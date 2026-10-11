import discord  # type: ignore[import-not-found]
from discord.ext import commands # type: ignore[import-not-found]

class GoodGirlCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="goodgirl", description="Fai i complimenti a una good girl del server!")
    @discord.app_commands.describe(utente="L'utente da premiare")
    async def goodgirl(self, interaction: discord.Interaction, utente: discord.Member):
        embed = discord.Embed(
            title="Chi è una **_Good girl_** ???",
            description=f"proprio tu {utente.mention} sei la _Good girl_ migliore del server!\nbrava continua così 😘🎀!",
            color=0xff69b4
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(GoodGirlCommand(bot))