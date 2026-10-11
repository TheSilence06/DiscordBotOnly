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

# 3. Evento di avvio e Sincronizzazione dei Comandi Slash
@bot.event
async def on_ready():
    print(f"✅ Loggato come {bot.user} (ID: {bot.user.id})")
    try:
        # Pulisce la cache locale dei comandi globali ed effettua il sync con Discord
        synced = await bot.tree.sync()
        print(f"✅ Sincronizzati {len(synced)} comandi Slash con successo!")
        print(f"\n📋 Comandi caricati:")
        for cmd in bot.tree.get_commands():
            print(f"   ✓ /{cmd.name}: {cmd.description}")
    except Exception as e:
        print(f"❌ Errore durante la sincronizzazione dei comandi: {e}")

# ==========================================
# 4. CARICAMENTO DEI COGS
# ==========================================

async def load_cogs():
    """Carica tutti i cogs dalla cartella 'cogs'"""
    for filename in os.listdir("cogs"):
        if filename.endswith(".py") and filename != "__init__.py":
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"✓ Caricato cog: {filename}")
            except Exception as e:
                print(f"✗ Errore nel caricamento di {filename}: {e}")

# ==========================================
# 5. EVENTO DI AVVIO CON CARICAMENTO COGS
# ==========================================

@bot.event
async def on_ready_cogs():
    """Esegue una volta al primo avvio"""
    if not hasattr(bot, 'cogs_loaded'):
        await load_cogs()
        bot.cogs_loaded = True
        print(f"\n📋 Comandi disponibili:")
        for cmd in bot.tree.get_commands():
            print(f"   - /{cmd.name}: {cmd.description}")

# Avvio del bot
async def main():
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

asyncio.run(main())