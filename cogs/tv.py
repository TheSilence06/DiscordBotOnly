import asyncio
import io
import logging
import os
import re
import threading
import wave

import discord
from discord import app_commands
from discord.ext import commands, voice_recv
from openai import AsyncOpenAI


logger = logging.getLogger(__name__)
DESTINATION_CHANNEL_ID = 1558247025991229573
LISTEN_DURATION_SECONDS = 5 * 60
AUDIO_SAMPLE_RATE = 48_000
AUDIO_CHANNELS = 2
AUDIO_SAMPLE_WIDTH = 2
CHUNK_DURATION_SECONDS = 3
CHUNK_SIZE_BYTES = (
    AUDIO_SAMPLE_RATE
    * AUDIO_CHANNELS
    * AUDIO_SAMPLE_WIDTH
    * CHUNK_DURATION_SECONDS
)
MIN_PARTIAL_CHUNK_SIZE_BYTES = (
    AUDIO_SAMPLE_RATE * AUDIO_CHANNELS * AUDIO_SAMPLE_WIDTH // 2
)
PARTIAL_FLUSH_INTERVAL_SECONDS = 0.5
MAX_QUEUED_CHUNKS = 30
KEYWORD_PATTERN = re.compile(r"\btelevisione\b", re.IGNORECASE)


class _SpeechCapture(voice_recv.AudioSink):
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        chunks: asyncio.Queue[bytes],
    ) -> None:
        super().__init__()
        self._loop = loop
        self._chunks = chunks
        self._buffers: dict[int, bytearray] = {}
        self._lock = threading.Lock()

    def wants_opus(self) -> bool:
        return False

    def write(
        self,
        user: discord.Member | discord.User | None,
        data: voice_recv.VoiceData,
    ) -> None:
        if user is None or data.pcm is None:
            return

        completed_chunks: list[bytes] = []
        with self._lock:
            buffer = self._buffers.setdefault(user.id, bytearray())
            buffer.extend(data.pcm)
            while len(buffer) >= CHUNK_SIZE_BYTES:
                completed_chunks.append(bytes(buffer[:CHUNK_SIZE_BYTES]))
                del buffer[:CHUNK_SIZE_BYTES]

        for chunk in completed_chunks:
            self._loop.call_soon_threadsafe(self._queue_chunk, chunk)

    def flush_partial(self) -> None:
        partial_chunks: list[bytes] = []
        with self._lock:
            for user_id, buffer in tuple(self._buffers.items()):
                if len(buffer) >= MIN_PARTIAL_CHUNK_SIZE_BYTES:
                    partial_chunks.append(bytes(buffer))
                    self._buffers[user_id] = bytearray()

        for chunk in partial_chunks:
            self._queue_chunk(chunk)

    def _queue_chunk(self, chunk: bytes) -> None:
        if self._chunks.full():
            try:
                self._chunks.get_nowait()
            except asyncio.QueueEmpty:
                pass
            logger.warning("Coda audio piena; scarto il segmento meno recente.")
        self._chunks.put_nowait(chunk)

    def cleanup(self) -> None:
        with self._lock:
            self._buffers.clear()


def _to_wav(pcm: bytes) -> io.BytesIO:
    audio_file = io.BytesIO()
    with wave.open(audio_file, "wb") as wav_file:
        wav_file.setnchannels(AUDIO_CHANNELS)
        wav_file.setsampwidth(AUDIO_SAMPLE_WIDTH)
        wav_file.setframerate(AUDIO_SAMPLE_RATE)
        wav_file.writeframes(pcm)
    audio_file.seek(0)
    return audio_file


class TvCommand(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._active_guilds: set[int] = set()

    @app_commands.command(
        name="tv",
        description="Ascolta per 5 minuti e sposta l'utente quando sente 'televisione'",
    )
    @app_commands.describe(utente="L'utente da spostare nel canale TV")
    async def tv(
        self,
        interaction: discord.Interaction,
        utente: discord.Member,
    ) -> None:
        guild = interaction.guild
        caller = interaction.user
        if guild is None or not isinstance(caller, discord.Member):
            await interaction.response.send_message(
                "Questo comando può essere usato solo in un server.",
                ephemeral=True,
            )
            return

        if caller.voice is None or not isinstance(caller.voice.channel, discord.VoiceChannel):
            await interaction.response.send_message(
                "Devi essere in un canale vocale per usare questo comando.",
                ephemeral=True,
            )
            return

        if utente.voice is None or utente.voice.channel is None:
            await interaction.response.send_message(
                "L'utente selezionato deve essere collegato a un canale vocale.",
                ephemeral=True,
            )
            return

        destination = guild.get_channel(DESTINATION_CHANNEL_ID)
        if not isinstance(destination, discord.VoiceChannel):
            await interaction.response.send_message(
                "Non trovo il canale vocale TV configurato in questo server.",
                ephemeral=True,
            )
            return

        bot_member = guild.me
        if bot_member is None or not bot_member.guild_permissions.move_members:
            await interaction.response.send_message(
                "Mi serve il permesso «Sposta membri» per spostare l'utente.",
                ephemeral=True,
            )
            return

        guild_id = guild.id
        if guild_id in self._active_guilds:
            await interaction.response.send_message(
                "Il comando /tv è già attivo in questo server.",
                ephemeral=True,
            )
            return

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            await interaction.response.send_message(
                "Sul server manca la variabile d'ambiente OPENAI_API_KEY.",
                ephemeral=True,
            )
            return

        current_voice_client = guild.voice_client
        if current_voice_client is not None and current_voice_client.is_connected():
            await interaction.response.send_message(
                "Sono già collegato a un canale vocale in questo server.",
                ephemeral=True,
            )
            return

        self._active_guilds.add(guild_id)
        voice_client: voice_recv.VoiceRecvClient | None = None
        worker: asyncio.Task[bool] | None = None
        flush_worker: asyncio.Task[None] | None = None
        client: AsyncOpenAI | None = None
        status = "Tempo scaduto: non ho sentito «televisione»."
        try:
            await interaction.response.send_message(
                "Avvio l'ascolto per un massimo di 5 minuti. I segmenti audio del "
                "canale saranno inviati a OpenAI Whisper per la trascrizione in italiano.",
            )
            voice_client = await caller.voice.channel.connect(
                cls=voice_recv.VoiceRecvClient
            )
            chunks: asyncio.Queue[bytes] = asyncio.Queue(maxsize=MAX_QUEUED_CHUNKS)
            capture = _SpeechCapture(asyncio.get_running_loop(), chunks)
            client = AsyncOpenAI(api_key=api_key)
            openai_client = client

            async def transcribe_until_keyword() -> bool:
                while True:
                    pcm = await chunks.get()
                    transcript = await openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=("voice.wav", _to_wav(pcm), "audio/wav"),
                        language="it",
                    )
                    if KEYWORD_PATTERN.search(transcript.text):
                        return True

            async def flush_partial_audio() -> None:
                while True:
                    await asyncio.sleep(PARTIAL_FLUSH_INTERVAL_SECONDS)
                    capture.flush_partial()

            voice_client.listen(capture)
            worker = asyncio.create_task(transcribe_until_keyword())
            flush_worker = asyncio.create_task(flush_partial_audio())
            try:
                keyword_heard = await asyncio.wait_for(
                    worker,
                    timeout=LISTEN_DURATION_SECONDS,
                )
            except asyncio.TimeoutError:
                keyword_heard = False

            if keyword_heard:
                if utente.voice is None or utente.voice.channel is None:
                    status = f"Ho sentito «televisione», ma {utente.mention} non è più in vocale."
                else:
                    await utente.move_to(destination, reason="Comando /tv: parola rilevata")
                    status = f"Ho sentito «televisione» e ho spostato {utente.mention}."
        except Exception:
            logger.exception("Errore durante il comando /tv")
            status = (
                "Non sono riuscito a completare il comando. Controlla la connessione "
                "vocale, i permessi del bot e la configurazione OpenAI."
            )
        finally:
            if voice_client is not None and voice_client.is_listening():
                try:
                    voice_client.stop_listening()
                except Exception:
                    logger.exception("Errore durante l'arresto dell'ascolto vocale")
            if flush_worker is not None and not flush_worker.done():
                flush_worker.cancel()
                await asyncio.gather(flush_worker, return_exceptions=True)
            if worker is not None and not worker.done():
                worker.cancel()
                await asyncio.gather(worker, return_exceptions=True)
            if voice_client is not None:
                if voice_client.is_connected():
                    try:
                        await voice_client.disconnect(force=True)
                    except Exception:
                        logger.exception("Errore durante l'uscita dal canale vocale")
                        status = "Non sono riuscito a uscire dal canale vocale."
            if client is not None:
                try:
                    await client.close()
                except Exception:
                    logger.exception("Errore durante la chiusura del client OpenAI")
            self._active_guilds.discard(guild_id)

        await interaction.followup.send(status)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TvCommand(bot))
