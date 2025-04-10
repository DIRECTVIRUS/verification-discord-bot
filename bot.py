import discord
import asyncio
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import datetime
import yaml
from modules.verification import init_db, get_config, set_config, get_user_verification, add_user_verification, async_session, Verification
from modules.logging import log_verification
from sqlalchemy.future import select

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

bot = commands.Bot(command_prefix="l!", intents=intents)

class VerificationModal(Modal):
    def __init__(self):
        super().__init__(title="Verification Form")
        self.day = TextInput(label="Day (DD)", placeholder="DD", max_length=2)
        self.month = TextInput(label="Month (MM)", placeholder="MM", max_length=2)
        self.year = TextInput(label="Year (YYYY)", placeholder="YYYY", max_length=4)
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

                await log_verification(interaction.client, interaction.guild.id, embed)

                # Notify the user
                await interaction.response.send_message(
                    "You must be at least 18 years old to verify.", ephemeral=True
                )
                return

            # Add the user to the verification database
            await add_user_verification(str(interaction.user.id), interaction.user.name)

            # Assign the verified role
            config = await get_config(interaction.guild.id)
            if config and config.verified_role_id:
                verified_role = interaction.guild.get_role(config.verified_role_id)
                if verified_role:
                    await interaction.user.add_roles(verified_role)
                else:
                    print(f"Verified role with ID {config.verified_role_id} not found in guild {interaction.guild.id}.")

            # Notify the user
            await interaction.response.send_message("You have been verified successfully!", ephemeral=True)

            # Log the verification event
            embed = discord.Embed(
                title="User Verified",
                description=f"{interaction.user.mention} has been verified.",
                color=discord.Color.green(),
            )
            embed.add_field(name="User ID", value=interaction.user.id, inline=True)
            embed.add_field(name="Username", value=interaction.user.name, inline=True)
            embed.add_field(name="Birthdate", value=birthdate.strftime("%d-%m-%Y"), inline=True)

            await log_verification(interaction.client, interaction.guild.id, embed)
        except ValueError:
            await interaction.response.send_message(
                "Invalid date. Please ensure all fields are filled correctly.", ephemeral=True
            )
        except Exception as e:
            print(f"Error in modal submission: {e}")
            await interaction.response.send_message(
                "An error occurred. Please try again later.", ephemeral=True
            )

class PersistentVerificationButton(Button):
    def __init__(self):
        super().__init__(label="Verify", style=discord.ButtonStyle.green, custom_id="persistent_verify_button")

    async def callback(self, interaction: discord.Interaction):
        try:
            # Check if user is already verified
            existing_user = await get_user_verification(str(interaction.user.id))
            if existing_user:
                await interaction.response.send_message("You are already verified.", ephemeral=True)
            else:
                modal = VerificationModal()
                await interaction.response.send_modal(modal)
        except Exception as e:
            print(f"Error in button callback: {e}")
            await interaction.response.send_message("An error occurred during verification. Please try again later.", ephemeral=True)

class PersistentVerificationView(View):
    def __init__(self):
        super().__init__(timeout=None)  # Persistent views must have no timeout
        self.add_item(PersistentVerificationButton())

class ConfigCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("ConfigCommands cog loaded.")

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"Logged in as {self.bot.user}")
        await init_db()  # Initialize the database
        # Register the persistent view
        self.bot.add_view(PersistentVerificationView())
        print("Persistent verification view registered.")

    @discord.app_commands.command(name="set_channels", description="Set the verification, log channels, and verified role for the server.")
    @discord.app_commands.describe(
        verification_channel="The channel for verification messages",
        log_channel="The channel for logging verification events",
        verified_role="The role to assign to verified users"
    )
    async def set_channels(self, interaction: discord.Interaction, verification_channel: discord.TextChannel, log_channel: discord.TextChannel, verified_role: discord.Role):
        """Slash command to set the verification and log channels, and the verified role."""
        await interaction.response.defer(ephemeral=True)  # Defer the response to avoid timeouts
        try:
            await set_config(interaction.guild.id, verification_channel.id, log_channel.id, verified_role.id)
            await interaction.followup.send(
                f"Configuration updated:\n"
                f"Verification Channel: {verification_channel.mention}\n"
                f"Log Channel: {log_channel.mention}\n"
                f"Verified Role: {verified_role.mention}",
                ephemeral=True,
            )
        except Exception as e:
            print(f"Error in /set_channels: {e}")
            await interaction.followup.send("An error occurred while processing the command. Please try again later.", ephemeral=True)

    @discord.app_commands.command(name="send_verification", description="Send the verification button in the configured channel.")
    async def send_verification(self, interaction: discord.Interaction):
        """Slash command to send the verification button."""
        await interaction.response.defer(ephemeral=True)  # Defer the response to avoid timeouts
        try:
            config = await get_config(interaction.guild.id)
            if not config:
                await interaction.followup.send("Configuration not found. Please set it up using `/set_channels`.", ephemeral=True)
                return

            if not config.verification_channel_id:
                await interaction.followup.send("Verification channel is not configured. Please set it up using `/set_channels`.", ephemeral=True)
                return

            channel = self.bot.get_channel(config.verification_channel_id)
            if not channel:
                await interaction.followup.send("Verification channel is invalid or inaccessible.", ephemeral=True)
                return

            # Create an embed for the verification message
            embed = discord.Embed(
                title="Verification Required",
                description="Please verify with the button below.",
                color=discord.Color.blue(),
            )

            view = PersistentVerificationView()
            await channel.send(embed=embed, view=view)
            await interaction.followup.send("Verification button sent!", ephemeral=True)
        except Exception as e:
            print(f"Error in /send_verification: {e}")
            await interaction.followup.send("An error occurred while processing the command. Please try again later.", ephemeral=True)

    @discord.app_commands.command(name="clear_verification", description="Clear a user's verification record.")
    @discord.app_commands.describe(user="The user whose verification record should be cleared.")
    async def clear_verification(self, interaction: discord.Interaction, user: discord.User):
        """Slash command to clear a user's verification record."""
        await interaction.response.defer(ephemeral=True)  # Defer the response to avoid timeouts
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(Verification).where(Verification.user_id == str(user.id))
                )
                verification = result.scalars().first()
                if verification:
                    await session.delete(verification)
                    await session.commit()
                    await interaction.followup.send(f"Verification record for {user.mention} has been cleared.", ephemeral=True)
                else:
                    await interaction.followup.send(f"No verification record found for {user.mention}.", ephemeral=True)
        except Exception as e:
            print(f"Error in /clear_verification: {e}")
            await interaction.followup.send("An error occurred while processing the command. Please try again later.", ephemeral=True)

@bot.command(name="sync")
@commands.is_owner()
async def sync_global_commands(ctx):
    """Manually sync slash commands globally."""
    try:
        synced = await bot.tree.sync()
        await ctx.send(f"Synced {len(synced)} global commands.")
    except discord.Forbidden:
        await ctx.send("Failed to sync commands globally: Missing Access (403 Forbidden). Check the bot's permissions.")
    except Exception as e:
        await ctx.send(f"Failed to sync commands globally: {e}")

async def main():
    """Main entry point for the bot."""
    async with bot:
        await bot.add_cog(ConfigCommands(bot))  # Await the cog addition
        await bot.start(TOKEN)

# Run the bot
asyncio.run(main())