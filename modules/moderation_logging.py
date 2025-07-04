import discord
from discord.ext.commands import Bot
from modules.moderation_db import get_moderation_config

async def log_moderation_action(bot: Bot, guild_id: int, embed: discord.Embed):
    """
    Logs a moderation event to the configured moderation log channel for the guild.
    Args:
        bot (Bot): The bot instance.
        guild_id (int): The ID of the guild where the event occurred.
        embed (discord.Embed): The embed message to log.
    """
    config = await get_moderation_config(guild_id)
    if config and config.log_channel_id:
        log_channel = bot.get_channel(config.log_channel_id)
        if log_channel:
            await log_channel.send(embed=embed)
