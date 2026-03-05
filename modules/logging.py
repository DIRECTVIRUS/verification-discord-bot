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
    try:
        config = await get_config(guild_id)
        if config and config.log_channel_id:
            log_channel = bot.get_channel(config.log_channel_id)
            if log_channel and isinstance(log_channel, discord.TextChannel):
                # Check if bot has permissions to send messages
                permissions = log_channel.permissions_for(log_channel.guild.me)
                if permissions.send_messages and permissions.embed_links:
                    await log_channel.send(embed=embed)
                else:
                    print(f"Missing permissions in verification log channel {config.log_channel_id} for guild {guild_id}")
            else:
                print(f"Verification log channel {config.log_channel_id} not found or not a text channel for guild {guild_id}")
    except Exception as e:
        print(f"Error logging verification action for guild {guild_id}: {e}")