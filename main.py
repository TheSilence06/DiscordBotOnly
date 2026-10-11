import json
import asyncio
import os

try:
    import discord  # type: ignore[import-not-found]
    from discord.ext import commands  # type: ignore[import-not-found]
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Discord.py non è installato. Esegui: pip install discord.py"
    ) from exc

# 1. Caricamento del token dal file token.json
with open("token.json", "r") as f:
    config = json.load(f)
TOKEN = config["token"]

# 2. Configurazione dei permessi (Intents)
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# 3. Funzione per il caricamento dei Cogs
async def load_cogs():
    """Carica tutti i cogs dalla cartella 'cogs'"""
    if os.path.exists("cogs"):
        for filename in os.listdir("cogs"):
            if filename.endswith(".py") and filename != "__init__.py":
                cog_name = f"cogs.{filename[:-3]}"
                try:
                    # Evita di ricaricare lo stesso cog se già presente
                    if cog_name not in bot.extensions:
                        await bot.load_extension(cog_name)
                        print(f"✓ Caricato cog: {filename}")
                except Exception as e:
                    print(f"✗ Errore nel caricamento di {filename}: {e}")

# 4. Evento di avvio, Pulizia forzata e Sincronizzazione dei Comandi Slash
@bot.event
async def on_ready():
    print(f"✅ Loggato come {bot.user} (ID: {bot.user.id})")
    try:
        # A. Pulisce i comandi globali vecchi/duplicati
        bot.tree.clear_commands(guild=None)
        
        # B. Pulisce eventuali comandi di gilda (server) rimasti bloccati
        for guild in bot.guilds:
            bot.tree.clear_commands(guild=guild)
            await bot.tree.sync(guild=guild)
            print(f"🧹 Puliti i comandi locali per il server: {guild.name} ({guild.id})")

        # C. Effettua il sync globale pulito dei comandi attuali
        synced = await bot.tree.sync()
        print(f"✅ Sincronizzati {len(synced)} comandi Slash globali con successo!")
        
        print(f"\n📋 Comandi attualmente attivi:")
        for cmd in bot.tree.get_commands():
            print(f"   ✓ /{cmd.name}: {cmd.description}")
    except Exception as e:
        print(f"❌ Errore durante la sincronizzazione dei comandi: {e}")

# 5. Avvio principale del bot con gestione asincrona pulita
async def main():
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

asyncio.run(main())