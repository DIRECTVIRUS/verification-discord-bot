import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View
from modules.selfroles_db import get_selfrole_config, set_selfrole_config, init_selfrole_db
import json

class SelfRoleButton(Button):
    def __init__(self, role: discord.Role, label: str):
        super().__init__(label=label, style=discord.ButtonStyle.primary, custom_id=f"selfrole_{role.id}")
        self.role = role

    async def callback(self, interaction: discord.Interaction):
        try:
            member = interaction.user
            if self.role in member.roles:
                # Remove the role if the user already has it
                await member.remove_roles(self.role)
                embed = discord.Embed(
                    title="Role Removed",
                    description=f"Removed **{self.role.name}** from you.",
                    color=discord.Color.red(),
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                # Add the role if the user doesn't have it
                await member.add_roles(self.role)
                embed = discord.Embed(
                    title="Role Assigned",
                    description=f"Assigned **{self.role.name}** to you.",
                    color=discord.Color.green(),
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.Forbidden:
            embed = discord.Embed(
                title="Error",
                description="Missing permission: Manage Roles.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(
                title="Error",
                description=f"An unexpected error occurred: {e}",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

class SelfRolesView(View):
    def __init__(self, roles_and_labels: list[tuple[discord.Role, str]]):
        super().__init__(timeout=None)  # Persistent view
        for role, label in roles_and_labels:
            self.add_item(SelfRoleButton(role, label))

class SelfRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("SelfRoles cog loaded.")  # Print message when the cog is loaded

    @app_commands.command(name="set_selfroles", description="Configure self-assignable roles for the server.")
    @app_commands.describe(
        roles_and_labels="Provide role IDs and button labels in the format role_id:label, separated by spaces."
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def set_selfroles(self, interaction: discord.Interaction, roles_and_labels: str):
        """
        Slash command to configure self-assignable roles.
        Example: /set_selfroles roles_and_labels="123456789012345678:Admin 987654321098765432:Member"
        """
        roles_and_labels = roles_and_labels.split()
        roles_and_labels_parsed = {}

        for pair in roles_and_labels:
            try:
                role_id, label = pair.split(":")
                role = interaction.guild.get_role(int(role_id))
                if role:
                    roles_and_labels_parsed[role_id] = label
                else:
                    raise ValueError(f"Role with ID {role_id} not found in this server.")
            except ValueError:
                embed = discord.Embed(
                    title="Error",
                    description=f"Invalid format for pair: `{pair}`. Use `role_id:label`.",
                    color=discord.Color.red(),
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

        if not roles_and_labels_parsed:
            embed = discord.Embed(
                title="Error",
                description="No valid roles and labels provided.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Save the configuration to the database
        await set_selfrole_config(interaction.guild.id, roles_and_labels_parsed)

        # Notify the user
        embed = discord.Embed(
            title="Configuration Updated",
            description="The self-roles configuration has been updated successfully.",
            color=discord.Color.green(),
        )
        for role_id, label in roles_and_labels_parsed.items():
            role = interaction.guild.get_role(int(role_id))
            embed.add_field(name=label, value=f"Role: {role.mention} (ID: {role.id})", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="send_selfroles", description="Send the self-roles message in the configured channel.")
    @app_commands.describe(
        channel="The channel where the self-roles message should be sent."
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def send_selfroles(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """
        Slash command to send the self-roles message to a specified channel.
        """
        config = await get_selfrole_config(interaction.guild.id)
        if not config:
            embed = discord.Embed(
                title="No Configuration Found",
                description="No self-roles configuration found. Use `/set_selfroles` to configure roles first.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Parse the roles and labels from the configuration
        roles_and_labels = json.loads(config.roles_and_labels)
        roles_and_labels_parsed = [
            (interaction.guild.get_role(int(role_id)), label)
            for role_id, label in roles_and_labels.items()
        ]

        # Create the embed for the self-roles message
        embed = discord.Embed(
            title="Self-Assignable Roles",
            description="Click the buttons below to assign or remove roles.",
            color=discord.Color.blue(),
        )
        for role, label in roles_and_labels_parsed:
            embed.add_field(name=label, value=f"Role: {role.mention} (ID: {role.id})", inline=False)

        # Create the view with buttons for each role
        view = SelfRolesView(roles_and_labels_parsed)

        # Send the message to the specified channel
        await channel.send(embed=embed, view=view)

        # Notify the user that the message was sent
        embed = discord.Embed(
            title="Message Sent",
            description=f"The self-roles message has been sent to {channel.mention}.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Register the view globally to make it persistent
        self.bot.add_view(view)

async def setup(bot):
    await init_selfrole_db()  # Initialize the self-role database
    await bot.add_cog(SelfRoles(bot))