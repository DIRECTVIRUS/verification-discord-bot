import discord
import asyncio
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import datetime
import yaml
from modules.verification import init_db, get_config, set_config, get_user_verification, add_user_verification, async_session, Verification, Config
from modules.logging import log_verification
from sqlalchemy.future import select
from discord import app_commands
import json
import os

# Load bot config file
with open("config/config.yml", "r") as file:
    config = yaml.safe_load(file)

TOKEN = config.get("TOKEN")
if not TOKEN:
    raise ValueError("Token not found in config.yml")

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
intents.members = True  # Required to manage roles

def is_admin():
    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.user.guild_permissions.administrator:
            # Send an error response if the user is not an admin
            embed = discord.Embed(
                title="Permission Denied",
                description="You do not have permission to use this command.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

bot = commands.Bot(command_prefix="l!", intents=intents)

# Global dictionary to track dynamic views
dynamic_views = {}

class VerificationModal(Modal):
    def __init__(self):
        super().__init__(title="Age Verification Form")
        self.day = TextInput(
            label="Birthdate - Day (DD)", 
            placeholder="Enter the day of your birth (e.g., 01)", 
            max_length=2 , min_length=2
        )
        self.month = TextInput(
            label="Birthdate - Month (MM)", 
            placeholder="Enter the month of your birth (e.g., 01 for January)", 
            max_length=2, min_length=2
        )
        self.year = TextInput(
            label="Birthdate - Year (YYYY)", 
            placeholder="Enter the year of your birth (e.g., 2000)", 
            max_length=4, min_length=4
        )
        self.add_item(self.day)
        self.add_item(self.month)
        self.add_item(self.year)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Combine the day, month, and year into a single date
            day = int(self.day.value)
            month = int(self.month.value)
            year = int(self.year.value)
            birthdate = datetime.date(year, month, day)

            # Calculate the user's age
            today = datetime.date.today()
            age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))

            # Check if the user is under 18
            if age < 18:
                # Log the underage attempt
                embed = discord.Embed(
                    title="Verification Failed",
                    description=f"{interaction.user.mention} attempted to verify but is under 18.",
                    color=discord.Color.red(),
                )
                embed.add_field(name="User ID", value=interaction.user.id, inline=True)
                embed.add_field(name="Username", value=interaction.user.name, inline=True)
                embed.add_field(name="Birthdate", value=birthdate.strftime("%d-%m-%Y"), inline=True)
                embed.add_field(name="Age", value=age, inline=True)
                embed.set_thumbnail(url=interaction.user.avatar.url)

                await log_verification(interaction.client, interaction.guild.id, embed)

                # Notify the user
                await interaction.response.send_message(
                    "You must be at least 18 years old to verify.", ephemeral=True
                )
                return

            # Add the user to the verification database
            await add_user_verification(str(interaction.user.id), interaction.user.name, birthdate=birthdate)

            # Assign the verified role
            config = await get_config(interaction.guild.id)
            if config and config.verified_role_id:
                verified_role = interaction.guild.get_role(config.verified_role_id)
                if verified_role:
                    await interaction.user.add_roles(verified_role)
                else:
                    print(f"Verified role with ID {config.verified_role_id} not found in guild {interaction.guild.id}.")

            # Notify the user
            embed = discord.Embed(
                title="Verification Successful",
                description=f"{interaction.user.mention}, you have been verified successfully!",
                color=discord.Color.green(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

            # Log the verification event
            embed = discord.Embed(
                title="User Verified",
                description=f"{interaction.user.mention} has been verified.",
                color=discord.Color.green(),
            )
            embed.add_field(name="User ID", value=interaction.user.id, inline=True)
            embed.add_field(name="Username", value=interaction.user.name, inline=True)
            embed.add_field(name="Birthdate", value=birthdate.strftime("%d-%m-%Y"), inline=True)
            embed.add_field(name="Age", value=age, inline=True)
            embed.set_thumbnail(url=interaction.user.avatar.url)

            await log_verification(interaction.client, interaction.guild.id, embed)
        except ValueError:
            embed = discord.Embed(
                title="Invalid Date",
                description="Please ensure all fields are filled correctly.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            print(f"Error in modal submission: {e}")
            embed = discord.Embed(
                title="Error",
                description="An error occurred. Please try again later.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

class DynamicVerificationButton(Button):
    def __init__(self, label: str, style: discord.ButtonStyle, custom_id: str):
        super().__init__(label=label, style=style, custom_id=custom_id)

    async def callback(self, interaction: discord.Interaction):
        try:
            print(f"Button clicked by {interaction.user} (ID: {interaction.user.id})")
            # Fetch the current configuration
            config = await get_config(interaction.guild.id)
            if not config:
                print("Configuration not found for the guild.")
            elif not config.verified_role_id:
                print("Verified role ID not configured.")
            else:
                print("Configuration and verified role ID found.")

            # Check if user is already verified
            existing_user = await get_user_verification(str(interaction.user.id))
            if existing_user:
                print(f"User {interaction.user.id} is already verified.")
                embed = discord.Embed(
                    title="Already Verified",
                    description="You are already verified.",
                    color=discord.Color.blue(),
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                print(f"User {interaction.user.id} is not verified. Showing modal.")
                modal = VerificationModal()
                await interaction.response.send_modal(modal)
        except Exception as e:
            print(f"Error in button callback: {e}")
            embed = discord.Embed(
                title="Error",
                description="An error occurred during verification. Please try again later.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

class DynamicVerificationView(View):
    def __init__(self, label: str, style: discord.ButtonStyle, custom_id: str):
        super().__init__(timeout=None)  # Persistent views must have no timeout
        self.add_item(DynamicVerificationButton(label=label, style=style, custom_id=custom_id))

class ConfigCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("ConfigCommands cog loaded.")

    @commands.Cog.listener()
    @bot.event
    async def on_ready(self):
        print(f"Logged in as {bot.user}")
        # Check if there is a stored restart message
        try:
            with open("restart_message.json", "r") as file:
                data = json.load(file)
                channel_id = data["channel_id"]
                message_id = data["message_id"]

            # Fetch the channel and message
            channel = bot.get_channel(channel_id)
            if channel:
                message = await channel.fetch_message(message_id)
                embed = discord.Embed(
                    title="Bot Restarted",
                    description="The bot has successfully restarted!",
                    color=discord.Color.green(),
                )
                await message.edit(embed=embed)

                # Add a tick reaction to indicate success
                await message.add_reaction("✅")

            # Remove the file after editing the message
            os.remove("restart_message.json")
            print("Restart message file deleted successfully.")
        except FileNotFoundError:
            print("No restart_message.json file found.")
        except KeyError:
            print("Invalid data in restart_message.json.")
        except discord.NotFound:
            print("Message or channel not found.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

        await init_db()  # Initialize the database

        # Fetch the current configuration for all guilds
        async with async_session() as session:
            result = await session.execute(select(Config))
            configs = result.scalars().all()

        # Register a persistent view for each guild
        for config in configs:
            custom_id = f"verify_button_{config.guild_id}"
            if config.verification_channel_id:
                view = DynamicVerificationView(label="Verify", style=discord.ButtonStyle.green, custom_id=custom_id)
                self.bot.add_view(view)  # Register the persistent view
                dynamic_views[custom_id] = view  # Track the view globally
                print(f"Registered persistent view for guild {config.guild_id} with custom_id {custom_id}")
            else:
                print(f"Skipping guild {config.guild_id}: verification_channel_id is not set.")
        print("Dynamic persistent verification views registered.")

    @discord.app_commands.command(name="set_channels", description="Set the verification, log channels, and verified role for the server.")
    @discord.app_commands.describe(
        verification_channel="The channel for verification messages",
        log_channel="The channel for logging verification events",
        verified_role="The role to assign to verified users"
    )
    @is_admin()
    async def set_channels(self, interaction: discord.Interaction, verification_channel: discord.TextChannel, log_channel: discord.TextChannel, verified_role: discord.Role):
        """Slash command to set the verification and log channels, and the verified role."""
        await interaction.response.defer(ephemeral=True)  # Defer the response to avoid timeouts
        await set_config(interaction.guild.id, verification_channel.id, log_channel.id, verified_role.id)

        # Create or update the dynamic view
        custom_id = f"verify_button_{interaction.guild.id}"
        view = DynamicVerificationView(label="Verify", style=discord.ButtonStyle.green, custom_id=custom_id)
        dynamic_views[custom_id] = view  # Track the view globally
        self.bot.add_view(view)  # Re-register the view

        # Create an embed for the success response
        embed = discord.Embed(
            title="Configuration Updated",
            description="The server configuration has been updated successfully.",
            color=discord.Color.green(),
        )
        embed.add_field(name="Verification Channel", value=verification_channel.mention, inline=False)
        embed.add_field(name="Log Channel", value=log_channel.mention, inline=False)
        embed.add_field(name="Verified Role", value=verified_role.mention, inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.app_commands.command(name="send_verification", description="Send the verification button in the configured channel.")
    @is_admin()
    async def send_verification(self, interaction: discord.Interaction):
        """Slash command to send the verification button."""
        await interaction.response.defer(ephemeral=True)  # Defer the response to avoid timeouts
        config = await get_config(interaction.guild.id)
        channel = self.bot.get_channel(config.verification_channel_id)

        # Create an embed for the verification message
        embed = discord.Embed(
            title="Age Verification Required",
            description="Please verify with the button below.",
            color=discord.Color.blue(),
        )

        # Use the existing view or create a new one
        custom_id = f"verify_button_{interaction.guild.id}"
        view = dynamic_views.get(custom_id) or DynamicVerificationView(label="Verify", style=discord.ButtonStyle.green, custom_id=custom_id)
        dynamic_views[custom_id] = view  # Track the view globally

        await channel.send(embed=embed, view=view)
        embed = discord.Embed(
            title="Verification Button Sent",
            description="The verification button has been sent successfully.",
            color=discord.Color.green(),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.app_commands.command(name="clear_verification", description="Clear a user's verification record.")
    @discord.app_commands.describe(user="The user whose verification record should be cleared.")
    @is_admin()
    async def clear_verification(self, interaction: discord.Interaction, user: discord.User):
        """Slash command to clear a user's verification record."""
        await interaction.response.defer(ephemeral=True)  # Defer the response to avoid timeouts
        async with async_session() as session:
            result = await session.execute(
                select(Verification).where(Verification.user_id == str(user.id))
            )
            verification = result.scalars().first()
            if verification:
                await session.delete(verification)
                await session.commit()

                # Send success response
                embed = discord.Embed(
                    title="Verification Record Cleared",
                    description=f"The verification record for {user.mention} has been cleared.",
                    color=discord.Color.green(),
                )
                await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.app_commands.command(name="check_verification", description="Check the verification status of a user.")
    @discord.app_commands.describe(user="The user whose verification status you want to check.")
    @is_admin()
    async def check_verification(self, interaction: discord.Interaction, user: discord.User):
        """Slash command to check the verification status of a user."""
        await interaction.response.defer(ephemeral=True)  # Defer the response to avoid timeouts
        async with async_session() as session:
            result = await session.execute(
                select(Verification).where(Verification.user_id == str(user.id))
            )
            verification = result.scalars().first()
            if verification:
                # Create an embed for the verification status
                embed = discord.Embed(
                    title="Verification Status",
                    description=f"Verification details for {user.mention}",
                    color=discord.Color.green(),
                )
                embed.add_field(name="User ID", value=user.id, inline=True)
                embed.add_field(name="Username", value=verification.username, inline=True)
                embed.add_field(name="Birthdate", value=verification.birthdate.strftime('%d-%m-%Y'), inline=True)
                embed.set_thumbnail(url=user.display_avatar.url)

                await interaction.followup.send(embed=embed, ephemeral=True)

@bot.command(name="sync", description="Sync slash commands to Discord globally.")
@commands.is_owner()
async def sync_global_commands(ctx):
    """Manually sync slash commands globally."""
    synced = await bot.tree.sync()
    embed = discord.Embed(
        title="Commands Synced",
        description=f"Successfully synced {len(synced)} global commands.",
        color=discord.Color.green(),
    )
    await ctx.send(embed=embed)

@bot.command(name="ping", description="Check the bot's latency.")
async def ping(ctx):
    """Responds with the bot's latency."""
    latency = round(bot.latency * 1000)  # Convert latency to milliseconds
    embed = discord.Embed(
        title="Pong! 🏓",
        description=f"Latency: {latency}ms",
        color=discord.Color.blue(),
    )
    await ctx.send(embed=embed)

@bot.command(name="restart", description="Restart the bot.")
@commands.is_owner()
async def restart(ctx, mode: str = None):
    """Restart the bot with an optional 'force' mode."""
    if mode:
        if mode.lower() == "force":
            # Force shutdown without saving the restart message
            embed = discord.Embed(
                title="Restarting Bot",
                description="The bot is restarting without a confirm message.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            await bot.close()
            return
        else:
            # Handle invalid argument
            embed = discord.Embed(
                title="Invalid Argument",
                description="Invalid argument provided. Use `force` to force a shutdown or leave it blank for a normal restart.",
                color=discord.Color.orange(),
            )
            await ctx.send(embed=embed)
            return

    # Normal restart with restart message
    embed = discord.Embed(
        title="Restarting Bot",
        description="The bot is restarting...",
        color=discord.Color.blue(),
    )
    message = await ctx.send(embed=embed)

    # Save the message ID and channel ID to a file
    with open("restart_message.json", "w") as file:
        json.dump({"channel_id": ctx.channel.id, "message_id": message.id}, file)

    await bot.close()

@bot.event
async def on_command_error(ctx, error):
    """Global error handler for commands."""
    try:
        if isinstance(error, commands.NotOwner):
            # Handle the NotOwner error
            embed = discord.Embed(
                title="Permission Denied",
                description="Error: Only the bot owner can execute this command.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MissingPermissions):
            # Handle missing permissions for other commands
            embed = discord.Embed(
                title="Permission Denied",
                description="You do not have the required permissions to use this command.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.CommandNotFound):
            # Handle unknown commands
            embed = discord.Embed(
                title="Command Not Found",
                description="The command you entered does not exist.",
                color=discord.Color.orange(),
            )
            await ctx.send(embed=embed)
        else:
            # Handle other errors
            embed = discord.Embed(
                title="Error",
                description="An unexpected error occurred. Please try again later.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            # Optionally log the error for debugging
            print(f"Unhandled error: {error}")
    except discord.Forbidden:
        # Fallback to plain text if the bot cannot send embeds
        if isinstance(error, commands.NotOwner):
            await ctx.send("Error: Only the bot owner can execute this command.")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("You do not have the required permissions to use this command.")
        elif isinstance(error, commands.CommandNotFound):
            await ctx.send("The command you entered does not exist.")
        else:
            await ctx.send("An unexpected error occurred. Please try again later.")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Global error handler for app commands (slash commands)."""
    if isinstance(error, app_commands.CheckFailure):
        # Handle permission errors
        embed = discord.Embed(
            title="Permission Denied",
            description="You do not have permission to use this command.",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        # Handle other errors
        embed = discord.Embed(
            title="Error",
            description="An unexpected error occurred. Please try again later.",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        # Optionally log the error for debugging
        print(f"Unhandled app command error: {error}")

async def main():
    """Main entry point for the bot."""
    async with bot:
        # Register global persistent views (if needed)
        custom_id = "global_verify_button"
        view = DynamicVerificationView(label="Verify", style=discord.ButtonStyle.green, custom_id=custom_id)
        bot.add_view(view)  # Register the persistent view globally

        # Add the ConfigCommands cog
        await bot.add_cog(ConfigCommands(bot))  # Await the cog addition
        await bot.start(TOKEN)

# Run the bot
asyncio.run(main())