import discord
from discord.ext import commands
from discord import app_commands
from modules.moderation_db import (
    set_moderation_log_channel, add_warning, get_user_warnings, get_warning_by_id, 
    remove_warning, clear_user_warnings, get_moderation_config, set_audit_logging, 
    is_audit_logging_enabled
)
from modules import moderation_logging

# Helper function to create admin check
def is_admin():
    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.user.guild_permissions.administrator:
            embed = discord.Embed(
                title="Error",
                description="Admin permission required.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

# Helper function to create mod check
def is_mod():
    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.user.guild_permissions.kick_members:
            embed = discord.Embed(
                title="Error",
                description="Mod permission required.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ban", description="Ban a member. Requires a reason.")
    @app_commands.describe(member="The member to ban.", reason="The reason for the ban.")
    @is_mod()
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        # Check if the user is trying to ban themselves
        if member.id == interaction.user.id:
            embed = discord.Embed(
                title="Error",
                description="Cannot ban yourself",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if the bot has ban permission
        if not interaction.guild.me.guild_permissions.ban_members:
            embed = discord.Embed(
                title="Error",
                description="Bot missing ban permission",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if the bot can ban the member (role hierarchy)
        if not interaction.guild.me.top_role > member.top_role:
            embed = discord.Embed(
                title="Error",
                description="Target has higher role than bot",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if the member can ban the target (role hierarchy)
        if not interaction.user.top_role > member.top_role and interaction.guild.owner_id != interaction.user.id:
            embed = discord.Embed(
                title="Error",
                description="Target has higher role than you",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        # Track if we successfully DM'd the user
        dm_sent = False
        
        # Try to send a DM to the user before banning them
        try:
            user_embed = discord.Embed(
                title=f"Banned",
                description=f"You were banned from {interaction.guild.name}",
                color=discord.Color.red()
            )
            user_embed.add_field(name="Reason", value=reason, inline=False)
            await member.send(embed=user_embed)
            dm_sent = True
        except discord.Forbidden:
            # User has DMs disabled
            pass
        except Exception as e:
            # Other errors with sending DM
            print(f"Error sending DM for ban: {e}")
            pass
            
        # Ban the member
        await member.ban(reason=reason)
        
        # Create an embed for the ban log
        embed = discord.Embed(
            title="Ban",
            description=f"{member.mention} banned",
            color=discord.Color.red(),
        )
        embed.add_field(name="By", value=interaction.user.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=True)
        
        # Add a field indicating whether DM was sent
        if not dm_sent:
            embed.add_field(name="Notice", value="User could not be notified via DM", inline=False)
        
        # Log the ban
        await moderation_logging.log_moderation_action(self.bot, interaction.guild.id, embed)
        
        # Send confirmation to the moderator
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="kick", description="Kick a member. Requires a reason.")
    @app_commands.describe(member="The member to kick.", reason="The reason for the kick.")
    @is_mod()
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        # Check if the user is trying to kick themselves
        if member.id == interaction.user.id:
            embed = discord.Embed(
                title="Error",
                description="Cannot kick yourself",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if the bot has kick permission
        if not interaction.guild.me.guild_permissions.kick_members:
            embed = discord.Embed(
                title="Error",
                description="Bot missing kick permission",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if the bot can kick the member (role hierarchy)
        if not interaction.guild.me.top_role > member.top_role:
            embed = discord.Embed(
                title="Error",
                description="Target has higher role than bot",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if the member can kick the target (role hierarchy)
        if not interaction.user.top_role > member.top_role and interaction.guild.owner_id != interaction.user.id:
            embed = discord.Embed(
                title="Error",
                description="Target has higher role than you",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        # Track if we successfully DM'd the user
        dm_sent = False
        
        # Try to send a DM to the user before kicking them
        try:
            user_embed = discord.Embed(
                title="Kicked",
                description=f"You were kicked from {interaction.guild.name}",
                color=discord.Color.orange()
            )
            user_embed.add_field(name="Reason", value=reason, inline=True)
            await member.send(embed=user_embed)
            dm_sent = True
        except discord.Forbidden:
            # User has DMs disabled
            pass
        except Exception as e:
            # Other errors with sending DM
            print(f"Error sending DM for kick: {e}")
            pass
            
        # Kick the member
        await member.kick(reason=reason)
        
        # Create an embed for the kick log
        embed = discord.Embed(
            title="Kick",
            description=f"{member.mention} kicked",
            color=discord.Color.orange(),
        )
        embed.add_field(name="By", value=interaction.user.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=True)
        
        # Add a field indicating whether DM was sent
        if not dm_sent:
            embed.add_field(name="Notice", value="User could not be notified via DM", inline=False)
        
        # Log the kick
        await moderation_logging.log_moderation_action(self.bot, interaction.guild.id, embed)
        
        # Send confirmation to the moderator
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="unban", description="Unban a user by their user ID.")
    @app_commands.describe(user_id="The user ID of the banned user to unban.", reason="The reason for the unban.")
    @is_mod()
    async def unban(self, interaction: discord.Interaction, user_id: str, reason: str = "No reason provided"):
        # Check if the bot has ban permission
        if not interaction.guild.me.guild_permissions.ban_members:
            embed = discord.Embed(
                title="Error",
                description="Bot missing ban permission",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Try to convert user_id to int
        try:
            user_id_int = int(user_id)
        except ValueError:
            embed = discord.Embed(
                title="Error",
                description="Invalid user ID format",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if the user is actually banned
        try:
            ban_entry = await interaction.guild.fetch_ban(discord.Object(id=user_id_int))
            banned_user = ban_entry.user
        except discord.NotFound:
            embed = discord.Embed(
                title="Error",
                description="User is not banned",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        except discord.Forbidden:
            embed = discord.Embed(
                title="Error",
                description="Bot cannot access ban list",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        except Exception as e:
            embed = discord.Embed(
                title="Error",
                description=f"Failed to check ban status: {e}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Unban the user
        try:
            await interaction.guild.unban(banned_user, reason=reason)
        except discord.Forbidden:
            embed = discord.Embed(
                title="Error",
                description="Bot cannot unban users",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        except Exception as e:
            embed = discord.Embed(
                title="Error",
                description=f"Failed to unban user: {e}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Create an embed for the unban log
        embed = discord.Embed(
            title="Unban",
            description=f"{banned_user.mention} ({banned_user.name}) unbanned",
            color=discord.Color.green(),
        )
        embed.add_field(name="User ID", value=str(user_id_int), inline=True)
        embed.add_field(name="By", value=interaction.user.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=True)
        
        # Log the unban
        await moderation_logging.log_moderation_action(self.bot, interaction.guild.id, embed)
        
        # Send confirmation to the moderator
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Try to notify the user via DM
        try:
            user_embed = discord.Embed(
                title="Unbanned",
                description=f"You were unbanned from {interaction.guild.name}",
                color=discord.Color.green()
            )
            user_embed.add_field(name="Reason", value=reason, inline=True)
            await banned_user.send(embed=user_embed)
        except discord.Forbidden:
            # User has DMs disabled
            pass
        except Exception as e:
            # Other errors with sending DM
            print(f"Error sending DM for unban: {e}")
            pass

    @app_commands.command(name="warn", description="Warn a member. Requires a reason. 3 warnings will result in an automatic ban.")
    @app_commands.describe(member="The member to warn.", reason="The reason for the warning.")
    @is_mod()
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        # Check if the user is trying to warn themselves
        if member.id == interaction.user.id:
            embed = discord.Embed(
                title="Error",
                description="Cannot warn yourself.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if the bot can moderate the member (role hierarchy)
        if not interaction.guild.me.top_role > member.top_role:
            embed = discord.Embed(
                title="Error",
                description="Target has higher role than bot.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if the moderator can moderate the target (role hierarchy)
        if not interaction.user.top_role > member.top_role and interaction.guild.owner_id != interaction.user.id:
            embed = discord.Embed(
                title="Error",
                description="Target has higher role than you.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        # Add warning to the database
        warning_id = await add_warning(
            guild_id=interaction.guild.id,
            user_id=member.id,
            moderator_id=interaction.user.id,
            reason=reason
        )
        
        # Get all warnings for this user after adding the new one
        warnings = await get_user_warnings(interaction.guild.id, member.id)
        warning_count = len(warnings)
            
        # Create an embed for the warning log (includes moderator info for log channel)
        embed = discord.Embed(
            title="Warning",
            description=f"User warned: {member.mention}",
            color=discord.Color.yellow(),
        )
        embed.add_field(name="ID", value=f"#{warning_id}", inline=True)
        embed.add_field(name="Reason", value=reason, inline=True)
        embed.add_field(name="Count", value=f"{warning_count}/3", inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        
        # Create a copy of the embed for the moderator without moderator field
        mod_embed = discord.Embed(
            title="Warning",
            description=f"User warned: {member.mention}",
            color=discord.Color.yellow(),
        )
        mod_embed.add_field(name="ID", value=f"#{warning_id}", inline=True)
        mod_embed.add_field(name="Reason", value=reason, inline=True)
        mod_embed.add_field(name="Count", value=f"{warning_count}/3", inline=True)
        
        # Send confirmation to the moderator
        await interaction.response.send_message(embed=mod_embed, ephemeral=True)
        
        # Track if we successfully DM'd the user
        dm_sent = False
        
        # Try to send a DM to the warned user
        try:
            user_embed = discord.Embed(
                title=f"Warning",
                description=f"You were warned in {interaction.guild.name}",
                color=discord.Color.yellow()
            )
            user_embed.add_field(name="Reason", value=reason, inline=True)
            user_embed.add_field(name="Count", value=f"{warning_count}/3", inline=True)
            
            if warning_count >= 3:
                user_embed.add_field(
                    name="Auto-Ban", 
                    value="3 warnings = automatic ban", 
                    inline=False
                )
            
            await member.send(embed=user_embed)
            dm_sent = True
        except discord.Forbidden:
            # User has DMs disabled
            pass
        except Exception as e:
            # Other errors with sending DM
            print(f"Error sending DM for warning: {e}")
            pass
            
        # Add a field to the log indicating whether DM was sent
        if not dm_sent:
            embed.add_field(name="Notice", value="User could not be notified via DM", inline=False)
            
        # Update the log
        await moderation_logging.log_moderation_action(self.bot, interaction.guild.id, embed)
            
        # Auto-ban after 3 warnings
        if warning_count >= 3:
            # Check if bot has ban permission before attempting auto-ban
            if not interaction.guild.me.guild_permissions.ban_members:
                error_embed = discord.Embed(
                    title="Warning",
                    description="Auto-ban failed: bot missing ban permission",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            elif not interaction.guild.me.top_role > member.top_role:
                error_embed = discord.Embed(
                    title="Warning",
                    description="Auto-ban failed: target has higher role than bot",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            else:
                try:
                    # Track if autoban DM was sent (separate from warning DM)
                    autoban_dm_sent = False
                    
                    # Try to DM the user BEFORE banning
                    auto_ban_reason = f"Automatic ban after 3 warnings. Last warning: {reason}"
                    try:
                        ban_embed = discord.Embed(
                            title=f"Auto-Ban",
                            description=f"Banned from {interaction.guild.name}: 3 warnings reached",
                            color=discord.Color.red()
                        )
                        ban_embed.add_field(name="Reason", value=auto_ban_reason, inline=False)
                        await member.send(embed=ban_embed)
                        autoban_dm_sent = True
                    except discord.Forbidden:
                        # User has DMs disabled
                        pass
                    except Exception as e:
                        # Other errors with sending DM
                        print(f"Error sending autoban DM: {e}")
                        pass
                    
                    # Now ban the member
                    await member.ban(reason=auto_ban_reason)
                    
                    # Create an embed for the auto-ban log
                    autoban_embed = discord.Embed(
                        title="Auto-Ban",
                        description=f"{member.mention}: 3 warnings reached",
                        color=discord.Color.red(),
                    )
                    autoban_embed.add_field(name="Reason", value=auto_ban_reason, inline=True)
                    autoban_embed.add_field(name="Mod", value=interaction.user.mention, inline=True)
                    
                    # Add field indicating if user was notified about the auto-ban
                    if not dm_sent and not autoban_dm_sent:
                        autoban_embed.add_field(name="Notice", value="User could not be notified via DM", inline=False)
                    
                    # Log the ban
                    await moderation_logging.log_moderation_action(self.bot, interaction.guild.id, autoban_embed)
                    
                    # Notify the moderator
                    autoban_mod_embed = discord.Embed(
                        title="Auto-Ban",
                        description=f"{member.mention} banned: 3 warnings",
                        color=discord.Color.red(),
                    )
                    autoban_mod_embed.add_field(name="Warning ID", value=f"#{warning_id}", inline=True)
                    await interaction.followup.send(embed=autoban_mod_embed, ephemeral=True)
                except discord.Forbidden:
                    # Bot doesn't have permission to ban
                    error_embed = discord.Embed(
                        title="Error",
                        description="Cannot auto-ban: missing permissions",
                        color=discord.Color.red(),
                    )
                    await interaction.followup.send(embed=error_embed, ephemeral=True)
                except Exception as e:
                    # Log any other errors
                    print(f"Auto-ban error: {e}")
                    error_embed = discord.Embed(
                        title="Error",
                        description=f"Auto-ban failed: {e}",
                        color=discord.Color.red(),
                    )
                    await interaction.followup.send(embed=error_embed, ephemeral=True)

    @app_commands.command(name="warnings", description="List all warnings for a member. Staff only.")
    @app_commands.describe(member="The member to check warnings for.")
    @is_mod()
    async def warnings(self, interaction: discord.Interaction, member: discord.Member):
        warnings = await get_user_warnings(interaction.guild.id, member.id)
        
        if not warnings:
            embed = discord.Embed(
                title="Warnings",
                description=f"{member.mention}: No warnings",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        embed = discord.Embed(
            title=f"Warnings",
            description=f"{member.mention}: {len(warnings)}/3 warnings",
            color=discord.Color.yellow(),
        )
        
        for warning in warnings:
            timestamp = warning.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            moderator = interaction.guild.get_member(warning.moderator_id)
            moderator_name = moderator.mention if moderator else f"<@{warning.moderator_id}>"
            
            embed.add_field(
                name=f"Warning #{warning.id}",
                value=f"**Reason:** {warning.reason}\n**Moderator:** {moderator_name}\n**Date:** {timestamp}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="remove_warning", description="Remove a warning from a member.")
    @app_commands.describe(member="The member to remove the warning from.", warning_id="The ID of the warning to remove.")
    @is_mod()
    async def remove_warning_cmd(self, interaction: discord.Interaction, member: discord.Member, warning_id: int):
        # Check if the user is trying to remove their own warning
        if member.id == interaction.user.id:
            await interaction.response.send_message("You cannot remove your own warning.", ephemeral=True)
            return
        
        # Get the warning from the database
        warning = await get_warning_by_id(warning_id)
        
        if not warning:
            await interaction.response.send_message("Warning not found.", ephemeral=True)
            return
        
        # Check if the warning belongs to this guild
        if warning.guild_id != interaction.guild.id:
            await interaction.response.send_message("Warning not from this server.", ephemeral=True)
            return
        
        # Check if the warning belongs to the member
        if warning.user_id != member.id:
            await interaction.response.send_message("This warning does not belong to the specified member.", ephemeral=True)
            return
        
        # Remove the warning
        await remove_warning(warning_id)
        
        # Create an embed for the warning removal log
        embed = discord.Embed(
            title="Warning Removed",
            description=f"Warning #{warning_id} was removed from {member.mention} by {interaction.user.mention}",
            color=discord.Color.green(),
        )
        
        # Log the warning removal
        await moderation_logging.log_moderation_action(self.bot, interaction.guild.id, embed)
        
        # Send confirmation to the moderator
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="unwarn", description="Remove a warning from a user by warning ID.")
    @app_commands.describe(warning_id="The ID of the warning to remove.")
    @is_mod()
    async def unwarn(self, interaction: discord.Interaction, warning_id: int):
        # Get the warning to check if it exists and belongs to this guild
        warning = await get_warning_by_id(warning_id)
        
        if not warning:
            embed = discord.Embed(
                title="Error",
                description=f"Warning #{warning_id} not found",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        # Check if the warning belongs to this guild
        if warning.guild_id != interaction.guild.id:
            embed = discord.Embed(
                title="Error",
                description="Warning not from this server",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Get user info for the log
        user = await interaction.client.fetch_user(warning.user_id)
        user_mention = user.mention if user else f"<@{warning.user_id}>"
        user_name = user.name if user else f"User ID: {warning.user_id}"
        
        # Get total warnings for this user before removing one
        all_warnings = await get_user_warnings(interaction.guild.id, warning.user_id)
        warning_count = len(all_warnings)
        
        # Remove the warning
        success = await remove_warning(warning_id)
        
        if success:
            # Create the embed for the log (with moderator info)
            log_embed = discord.Embed(
                title="Warning Removed",
                description=f"#{warning_id} from {user_mention}",
                color=discord.Color.green(),
            )
            log_embed.add_field(name="Reason", value=warning.reason, inline=True)
            log_embed.add_field(name="Count", value=f"{warning_count-1}/3", inline=True)
            log_embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            
            if warning_count == 3:
                log_embed.add_field(
                    name="Note", 
                    value="Auto-ban prevented", 
                    inline=False
                )
            
            # Create a copy for the moderator without the moderator field
            mod_embed = discord.Embed(
                title="Warning Removed",
                description=f"#{warning_id} from {user_mention}",
                color=discord.Color.green(),
            )
            mod_embed.add_field(name="Reason", value=warning.reason, inline=True)
            mod_embed.add_field(name="Count", value=f"{warning_count-1}/3", inline=True)
            
            if warning_count == 3:
                mod_embed.add_field(
                    name="Note", 
                    value="Auto-ban prevented", 
                    inline=False
                )
            
            # Notify the moderator
            await interaction.response.send_message(
                embed=mod_embed,
                ephemeral=True
            )
            
            # Track if we successfully notified the user
            dm_sent = False
            
            # Try to notify the user
            try:
                user_embed = discord.Embed(
                    title=f"Warning Removed",
                    description=f"Warning removed in {interaction.guild.name}",
                    color=discord.Color.green()
                )
                user_embed.add_field(name="Reason", value=warning.reason, inline=True)
                
                if user:  # Make sure user object exists
                    await user.send(embed=user_embed)
                    dm_sent = True
            except (discord.Forbidden, AttributeError):
                # User has DMs disabled or user couldn't be found
                pass
            except Exception as e:
                print(f"Error sending warning removal DM: {e}")
                pass
                
            # Add a field to the log indicating whether DM was sent
            if not dm_sent and user:
                log_embed.add_field(name="Notice", value="User could not be notified via DM", inline=False)
                
            # Update the log
            await moderation_logging.log_moderation_action(self.bot, interaction.guild.id, log_embed)
        else:
            embed = discord.Embed(
                title="Error",
                description="Failed to remove the warning. Please try again.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="clearwarnings", description="Clear all warnings for a member.")
    @app_commands.describe(member="The member to clear warnings for.")
    @is_mod()
    async def clearwarnings(self, interaction: discord.Interaction, member: discord.Member):
        # Count of removed warnings
        count = await clear_user_warnings(interaction.guild.id, member.id)
        
        if count > 0:
            # Create embed for the log
            log_embed = discord.Embed(
                title="Warnings Cleared",
                description=f"{member.mention}: {count} warnings removed",
                color=discord.Color.green(),
            )
            log_embed.add_field(name="By", value=interaction.user.mention, inline=True)
            
            if count >= 3:
                log_embed.add_field(
                    name="Note", 
                    value="Auto-ban prevented", 
                    inline=True
                )
            
            # Notify the moderator
            await interaction.response.send_message(
                embed=log_embed,
                ephemeral=True
            )
            
            # Track if we successfully notified the user
            dm_sent = False
            
            # Try to notify the user
            try:
                user_embed = discord.Embed(
                    title=f"Warnings Cleared",
                    description=f"{count} warnings removed in {interaction.guild.name}",
                    color=discord.Color.green()
                )
                await member.send(embed=user_embed)
                dm_sent = True
            except discord.Forbidden:
                # User has DMs disabled
                pass
            except Exception as e:
                print(f"Error sending warning clear DM: {e}")
                pass
                
            # Add a field to the log indicating whether DM was sent
            if not dm_sent:
                log_embed.add_field(name="Notice", value="User could not be notified via DM", inline=False)
                
            # Update the log
            await moderation_logging.log_moderation_action(self.bot, interaction.guild.id, log_embed)
        else:
            embed = discord.Embed(
                title="Notice",
                description=f"{member.mention}: No warnings to clear",
                color=discord.Color.blue(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="clearwarnings_id", description="Clear all warnings for a user by their user ID.")
    @app_commands.describe(user_id="The user ID of the user to clear warnings for.")
    @is_mod()
    async def clearwarnings_id(self, interaction: discord.Interaction, user_id: str):
        # Try to convert user_id to int
        try:
            user_id_int = int(user_id)
        except ValueError:
            embed = discord.Embed(
                title="Error",
                description="Invalid user ID format",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Get warnings count before clearing
        count = await clear_user_warnings(interaction.guild.id, user_id_int)
        
        if count > 0:
            # Try to fetch user info
            try:
                user = await interaction.client.fetch_user(user_id_int)
                user_mention = user.mention if user else f"<@{user_id_int}>"
                user_name = user.name if user else f"User ID: {user_id_int}"
            except:
                user = None
                user_mention = f"<@{user_id_int}>"
                user_name = f"User ID: {user_id_int}"
            
            # Create embed for the log
            log_embed = discord.Embed(
                title="Warnings Cleared",
                description=f"{user_mention}: {count} warnings removed",
                color=discord.Color.green(),
            )
            log_embed.add_field(name="User ID", value=str(user_id_int), inline=True)
            log_embed.add_field(name="By", value=interaction.user.mention, inline=True)
            
            if count >= 3:
                log_embed.add_field(
                    name="Note", 
                    value="Auto-ban prevented", 
                    inline=False
                )
            
            # Notify the moderator
            await interaction.response.send_message(
                embed=log_embed,
                ephemeral=True
            )
            
            # Track if we successfully notified the user
            dm_sent = False
            
            # Try to notify the user if we have a user object
            if user:
                try:
                    user_embed = discord.Embed(
                        title=f"Warnings Cleared",
                        description=f"{count} warnings removed in {interaction.guild.name}",
                        color=discord.Color.green()
                    )
                    await user.send(embed=user_embed)
                    dm_sent = True
                except discord.Forbidden:
                    # User has DMs disabled
                    pass
                except Exception as e:
                    print(f"Error sending warning clear DM: {e}")
                    pass
            
            # Add a field to the log indicating whether DM was sent
            if not dm_sent and user:
                log_embed.add_field(name="Notice", value="User could not be notified via DM", inline=False)
                
            # Update the log
            await moderation_logging.log_moderation_action(self.bot, interaction.guild.id, log_embed)
        else:
            embed = discord.Embed(
                title="Notice",
                description=f"No warnings found for user ID {user_id_int}",
                color=discord.Color.blue(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="audit_logging", description="Enable or disable audit logging for native Discord moderation actions.")
    @app_commands.describe(enabled="Enable (True) or disable (False) audit logging.")
    @is_admin()
    async def audit_logging_cmd(self, interaction: discord.Interaction, enabled: bool):
        """Enable or disable audit logging for the server."""
        await interaction.response.defer(ephemeral=True)
        
        # Check if a moderation log channel is configured
        config = await get_moderation_config(interaction.guild.id)
        if not config or not config.log_channel_id:
            embed = discord.Embed(
                title="Error",
                description="Please configure a moderation log channel first using `/config`.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Update the audit logging setting
        await set_audit_logging(interaction.guild.id, enabled)
        
        # Create confirmation embed
        if enabled:
            embed = discord.Embed(
                title="✅ Audit Logging Enabled",
                description="Native Discord bans, kicks, and unbans will now be logged.",
                color=discord.Color.green(),
            )
            embed.add_field(
                name="Log Channel",
                value=f"<#{config.log_channel_id}>",
                inline=True
            )
            embed.add_field(
                name="Tracked Actions",
                value="• Bans\\n• Kicks\\n• Unbans",
                inline=True
            )
            embed.set_footer(text="Note: Only actions performed outside the bot are logged.")
        else:
            embed = discord.Embed(
                title="🔕 Audit Logging Disabled",
                description="Native Discord moderation actions will no longer be logged.",
                color=discord.Color.orange(),
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)

        
async def setup(bot):
    await bot.add_cog(Moderation(bot))
