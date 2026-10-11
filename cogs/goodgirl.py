import discord
from discord import app_commands
from discord.ext import commands

class GoodGirlCommand(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

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

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(GoodGirlCommand(bot))