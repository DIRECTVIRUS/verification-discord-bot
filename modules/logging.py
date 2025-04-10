import discord
from discord.ext.commands import Bot
from modules.verification import get_config

async def log_verification(bot: Bot, guild_id: int, embed: discord.Embed):
    """
    Logs a verification event to the configured log channel for the guild.

    Args:
        bot (Bot): The bot instance.
        guild_id (int): The ID of the guild where the event occurred.
        embed (discord.Embed): The embed message to log.
    """
    config = await get_config(guild_id)
    if config and config.log_channel_id:
        log_channel = bot.get_channel(config.log_channel_id)
        if log_channel:
            await log_channel.send(embed=embed)