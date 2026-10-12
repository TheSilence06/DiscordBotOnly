import asyncio
import json
import os
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

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
                    if cog_name not in bot.extensions:
                        await bot.load_extension(cog_name)
                        print(f"✓ Caricato cog: {filename}")
                except Exception as e:
                    print(f"✗ Errore nel caricamento di {filename}: {e}")

# 4. Evento di avvio e Sincronizzazione dei Comandi corretta
@bot.event
async def on_ready():
    print(f"✅ Loggato come {bot.user} (ID: {bot.user.id})")
    try:
        # A. Pulisce eventuali comandi di gilda (server) rimasti bloccati
        for guild in bot.guilds:
            bot.tree.clear_commands(guild=guild)
            await bot.tree.sync(guild=guild)
            print(f"🧹 Puliti i comandi locali per il server: {guild.name} ({guild.id})")

        # B. Effettua il sync globale dei comandi caricati dai cogs
        synced = await bot.tree.sync()
        print(f"✅ Sincronizzati {len(synced)} comandi Slash globali con successo!")
        
        print(f"\n📋 Comandi attualmente attivi:")
        for cmd in bot.tree.get_commands():
            print(f"   ✓ /{cmd.name}: {cmd.description}")
            
    except Exception as e:
        print(f"❌ Errore durante la sincronizzazione dei comandi: {e}")

# 5. Avvio principale del bot con caricamento preventivo dei Cogs
async def main():
    async with bot:
        # Carichiamo i cogs PRIMA di avviare il bot, così on_ready li troverà già pronti
        await load_cogs()
        await bot.start(TOKEN)

asyncio.run(main())