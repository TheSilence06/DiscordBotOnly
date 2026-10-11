import asyncio
import json
import os
import discord
from discord.ext import commands

if os.path.exists("token.json"):
    with open("token.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        TOKEN = data.get("token")
else:
    raise FileNotFoundError("Il file 'token.json' non è stato trovato nella cartella del progetto!")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Bot online come {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizzati {len(synced)} comandi globali.")
    except Exception as e:
        print(e)

async def load_extensions():
    if os.path.exists("./cogs"):
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                extension_name = f"cogs.{filename[:-3]}"
                await bot.load_extension(extension_name)
                print(f"Caricato il modulo: {filename}")

async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

asyncio.run(main())