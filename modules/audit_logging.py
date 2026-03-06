import discord
from discord.ext import commands
import asyncio
from modules.moderation_logging import log_moderation_action
from modules.moderation_db import is_audit_logging_enabled


class AuditLogging(commands.Cog):
    """Cog for tracking and logging native Discord moderation actions."""
    
    def __init__(self, bot):
        self.bot = bot
        print("AuditLogging cog loaded.")

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        """Log bans performed outside the bot (native Discord bans)."""
        try:
            # Check if audit logging is enabled for this guild
            if not await is_audit_logging_enabled(guild.id):
                return
            
            # Wait for the audit log to be available
            await asyncio.sleep(1)
            
            # Check if bot has permission to view audit log
            if not guild.me.guild_permissions.view_audit_log:
                print(f"AuditLogging: Missing view_audit_log permission in guild {guild.name}")
                return
            
            # Fetch the most recent ban from audit log
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.ban):
                if entry.target.id == user.id:
                    # Check if this ban was done by the bot itself (skip logging if so)
                    if entry.user.id == self.bot.user.id:
                        print(f"AuditLogging: Skipping bot's own ban action for {user.name}")
                        return
                    
                    # Create embed for the ban log
                    embed = discord.Embed(
                        title="Ban (Native)",
                        description=f"{user.mention} banned via Discord",
                        color=discord.Color.red(),
                    )
                    embed.add_field(name="User", value=f"{user.name} ({user.id})", inline=True)
                    embed.add_field(name="By", value=entry.user.mention, inline=True)
                    embed.add_field(name="Reason", value=entry.reason or "No reason provided", inline=True)
                    embed.set_thumbnail(url=user.display_avatar.url)
                    
                    # Log the ban
                    await log_moderation_action(self.bot, guild.id, embed)
                    print(f"AuditLogging: Logged native ban for {user.name} in {guild.name}")
                    break
        except discord.Forbidden:
            print(f"AuditLogging: Forbidden error in guild {guild.name}")
        except Exception as e:
            print(f"AuditLogging: Error logging native ban: {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Log kicks performed outside the bot (native Discord kicks)."""
        try:
            # Check if audit logging is enabled for this guild
            if not await is_audit_logging_enabled(member.guild.id):
                return
            
            # Wait for the audit log to be available
            await asyncio.sleep(1)
            
            # Check if bot has permission to view audit log
            if not member.guild.me.guild_permissions.view_audit_log:
                print(f"AuditLogging: Missing view_audit_log permission in guild {member.guild.name}")
                return
            
            # Fetch the most recent kick from audit log
            async for entry in member.guild.audit_logs(limit=5, action=discord.AuditLogAction.kick):
                if entry.target.id == member.id:
                    # Check if this kick was done by the bot itself (skip logging if so)
                    if entry.user.id == self.bot.user.id:
                        print(f"AuditLogging: Skipping bot's own kick action for {member.name}")
                        return
                    
                    # Create embed for the kick log
                    embed = discord.Embed(
                        title="Kick (Native)",
                        description=f"{member.mention} kicked via Discord",
                        color=discord.Color.orange(),
                    )
                    embed.add_field(name="User", value=f"{member.name} ({member.id})", inline=True)
                    embed.add_field(name="By", value=entry.user.mention, inline=True)
                    embed.add_field(name="Reason", value=entry.reason or "No reason provided", inline=True)
                    embed.set_thumbnail(url=member.display_avatar.url)
                    
                    # Log the kick
                    await log_moderation_action(self.bot, member.guild.id, embed)
                    print(f"AuditLogging: Logged native kick for {member.name} in {member.guild.name}")
                    break
        except discord.Forbidden:
            print(f"AuditLogging: Forbidden error in guild {member.guild.name}")
        except Exception as e:
            print(f"AuditLogging: Error logging native kick: {e}")

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        """Log unbans performed outside the bot (native Discord unbans)."""
        try:
            # Check if audit logging is enabled for this guild
            if not await is_audit_logging_enabled(guild.id):
                return
            
            # Wait for the audit log to be available
            await asyncio.sleep(1)
            
            # Check if bot has permission to view audit log
            if not guild.me.guild_permissions.view_audit_log:
                print(f"AuditLogging: Missing view_audit_log permission in guild {guild.name}")
                return
            
            # Fetch the most recent unban from audit log
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.unban):
                if entry.target.id == user.id:
                    # Check if this unban was done by the bot itself (skip logging if so)
                    if entry.user.id == self.bot.user.id:
                        print(f"AuditLogging: Skipping bot's own unban action for {user.name}")
                        return
                    
                    # Create embed for the unban log
                    embed = discord.Embed(
                        title="Unban (Native)",
                        description=f"{user.mention} unbanned via Discord",
                        color=discord.Color.green(),
                    )
                    embed.add_field(name="User", value=f"{user.name} ({user.id})", inline=True)
                    embed.add_field(name="By", value=entry.user.mention, inline=True)
                    embed.add_field(name="Reason", value=entry.reason or "No reason provided", inline=True)
                    embed.set_thumbnail(url=user.display_avatar.url)
                    
                    # Log the unban
                    await log_moderation_action(self.bot, guild.id, embed)
                    print(f"AuditLogging: Logged native unban for {user.name} in {guild.name}")
                    break
        except discord.Forbidden:
            print(f"AuditLogging: Forbidden error in guild {guild.name}")
        except Exception as e:
            print(f"AuditLogging: Error logging native unban: {e}")


async def setup(bot):
    await bot.add_cog(AuditLogging(bot))
