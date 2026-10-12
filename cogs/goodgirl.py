import asyncio
import logging
import shutil
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands


logger = logging.getLogger(__name__)
AUDIO_FILE = Path(__file__).resolve().parent.parent / "GoodGirl.mp3"


class GoodGirlCommand(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._active_guilds: set[int] = set()

    @app_commands.command(name="goodgirl", description="Fai i complimenti a una good girl del server!")
    @app_commands.describe(utente="L'utente da premiare")
    async def goodgirl(
        self,
        interaction: discord.Interaction,
        utente: discord.Member,
    ) -> None:
        embed = discord.Embed(
            title="Chi è una **_Good girl_** ???",
            description=f"proprio tu {utente.mention} sei la _Good girl_ migliore del server!\nbrava continua così 😘🎀!",
            color=0xff69b4
        )
        await interaction.response.send_message(embed=embed)

        guild = interaction.guild
        voice_state = utente.voice
        if guild is None or voice_state is None or voice_state.channel is None:
            return

        if not AUDIO_FILE.is_file():
            await interaction.followup.send(
                f"Non trovo il file audio: `{AUDIO_FILE.name}`.",
                ephemeral=True,
            )
            return

        if shutil.which("ffmpeg") is None:
            await interaction.followup.send(
                "FFmpeg non è installato o non è presente nel PATH.",
                ephemeral=True,
            )
            return

        guild_id = guild.id
        if guild_id in self._active_guilds:
            await interaction.followup.send(
                "Sto già riproducendo un audio in questo server.",
                ephemeral=True,
            )
            return

        self._active_guilds.add(guild_id)
        voice_client: discord.VoiceClient | None = None
        error_message: str | None = None
        try:
            existing_client = guild.voice_client
            if existing_client is not None and existing_client.is_connected():
                raise RuntimeError("Il bot è già collegato a un canale vocale.")

            voice_client = await voice_state.channel.connect()
            await guild.change_voice_state(
                channel=voice_client.channel,
                self_mute=False,
            )
            loop = asyncio.get_running_loop()
            playback_done: asyncio.Future[None] = loop.create_future()

            def playback_finished(error: Exception | None) -> None:
                def finish() -> None:
                    if playback_done.done():
                        return
                    if error is not None:
                        playback_done.set_exception(error)
                    else:
                        playback_done.set_result(None)

                loop.call_soon_threadsafe(finish)

            source = discord.FFmpegPCMAudio(str(AUDIO_FILE))
            voice_client.play(source, after=playback_finished)
            await playback_done
        except Exception:
            logger.exception("Errore durante la riproduzione del comando /goodgirl")
            error_message = (
                "Non sono riuscito a riprodurre l'audio. Verifica i permessi vocali "
                "del bot e che FFmpeg e PyNaCl siano installati."
            )
        finally:
            if voice_client is not None and voice_client.is_connected():
                try:
                    await voice_client.disconnect(force=True)
                except Exception:
                    logger.exception("Errore durante la disconnessione dal canale vocale")
                    error_message = "L'audio è terminato, ma non sono riuscito a uscire dal canale."
            self._active_guilds.discard(guild_id)

        if error_message is not None:
            await interaction.followup.send(error_message, ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(GoodGirlCommand(bot))