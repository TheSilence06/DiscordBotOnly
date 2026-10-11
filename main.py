import json
import asyncio
import os
import discord
from discord.ext import commands

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
    print(f"Loggato come {bot.user} (ID: {bot.user.id})")
    try:
        # Pulisce la cache locale dei comandi globali ed effettua il sync con Discord
        synced = await bot.tree.sync()
        print(f"Sincronizzati {len(synced)} comandi Slash con successo!")
    except Exception as e:
        print(f"Errore durante la sincronizzazione dei comandi: {e}")

# ==========================================
# 4. DEFINIZIONE DEI COMANDI SLASH
# ==========================================

@bot.tree.command(name="goodgirl", description="Da del goodgirl all'utente")
async def goodgirl(interaction: discord.Interaction):
    await interaction.response.send_message(f"Brava ragazza, {interaction.user.mention}!")

@bot.tree.command(name="tv", description="Sposta lollo quando c'è la tv")
async def tv(interaction: discord.Interaction):
    await interaction.response.send_message("Comando TV eseguito!")

@bot.tree.command(name="harucenagay", description="Sposta haru nel canale cena (cucina di haru)")
async def harucenagay(interaction: discord.Interaction):
    await interaction.response.send_message("Haru spostato nel canale cena!")

# Avvio del bot
bot.run(TOKEN)