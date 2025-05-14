import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View
from modules.selfroles_db import get_selfrole_config, set_selfrole_config, delete_selfrole_config, get_all_selfrole_configs, init_selfrole_db
import json

class SelfRoleButton(Button):
    def __init__(self, role: discord.Role, label: str, style: discord.ButtonStyle):
        super().__init__(label=label, style=style, custom_id=f"selfrole_{role.id}")
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
    def __init__(self, roles_and_labels: list[tuple[discord.Role, str]], button_style: discord.ButtonStyle):
        super().__init__(timeout=None)  # Persistent view
        for role, label in roles_and_labels:
            self.add_item(SelfRoleButton(role, label, button_style))

class SelfRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("SelfRoles cog loaded.")  # Print message when the cog is loaded

    @app_commands.command(name="set_selfroles", description="Configure self-assignable roles for the server.")
    @app_commands.describe(
        message_name="A unique name for this self-role message.",
        roles_and_labels="Provide role IDs and button labels in the format role_id:label, separated by spaces.",
        button_color="The color of the buttons (primary, secondary, success, danger).",
        embed_title="The title of the embed message.",
        embed_description="The description of the embed message."
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def set_selfroles(
        self,
        interaction: discord.Interaction,
        message_name: str,
        roles_and_labels: str,
        button_color: str = "primary",
        embed_title: str = "Self-Assignable Roles",
        embed_description: str = "Click the buttons below to assign or remove roles."
    ):
        """
        Slash command to configure self-assignable roles.
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
        await set_selfrole_config(
            interaction.guild.id,
            message_name,
            roles_and_labels_parsed,
            button_color,
            embed_title,
            embed_description
        )

        # Notify the user
        embed = discord.Embed(
            title="Configuration Updated",
            description=f"The self-roles configuration for `{message_name}` has been updated successfully.",
            color=discord.Color.green(),
        )
        for role_id, label in roles_and_labels_parsed.items():
            role = interaction.guild.get_role(int(role_id))
            embed.add_field(name=label, value=f"Role: {role.mention} (ID: {role.id})", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="remove_selfroles", description="Remove a self-role configuration.")
    @app_commands.describe(
        message_name="The name of the self-role message to remove."
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_selfroles(self, interaction: discord.Interaction, message_name: str):
        """
        Slash command to remove a self-role configuration.
        """
        config = await get_selfrole_config(interaction.guild.id, message_name)
        if not config:
            embed = discord.Embed(
                title="No Configuration Found",
                description=f"No self-roles configuration found for `{message_name}`.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Delete the configuration
        await delete_selfrole_config(interaction.guild.id, message_name)

        # Notify the user
        embed = discord.Embed(
            title="Configuration Removed",
            description=f"The self-roles configuration for `{message_name}` has been removed successfully.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="show_selfroles_config", description="Show the configuration for a self-role message.")
    @app_commands.describe(
        message_name="The name of the self-role message to show."
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def show_selfroles_config(self, interaction: discord.Interaction, message_name: str):
        """
        Slash command to show the configuration for a self-role message.
        """
        config = await get_selfrole_config(interaction.guild.id, message_name)
        if not config:
            embed = discord.Embed(
                title="No Configuration Found",
                description=f"No self-roles configuration found for `{message_name}`.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Parse the roles and labels from the configuration
        roles_and_labels = json.loads(config.roles_and_labels)

        # Create the embed to display the configuration
        embed = discord.Embed(
            title=f"Configuration for `{message_name}`",
            description="Here are the details of the self-role configuration:",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Embed Title", value=config.embed_title, inline=False)
        embed.add_field(name="Embed Description", value=config.embed_description, inline=False)
        embed.add_field(name="Button Color", value=config.button_color, inline=False)
        for role_id, label in roles_and_labels.items():
            role = interaction.guild.get_role(int(role_id))
            embed.add_field(name=label, value=f"Role: {role.mention} (ID: {role.id})", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="list_selfroles", description="List all self-role messages configured for this server.")
    @app_commands.checks.has_permissions(administrator=True)
    async def list_selfroles(self, interaction: discord.Interaction):
        """
        Slash command to list all self-role messages configured for the server.
        """
        configs = await get_all_selfrole_configs(interaction.guild.id)
        if not configs:
            embed = discord.Embed(
                title="No Configurations Found",
                description="There are no self-role configurations for this server.",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Create the embed to display the list of configurations
        embed = discord.Embed(
            title="Self-Role Configurations",
            description="Here are all the self-role messages configured for this server:",
            color=discord.Color.blue(),
        )
        for config in configs:
            embed.add_field(
                name=config.message_name,
                value=f"Embed Title: {config.embed_title}\nButton Color: {config.button_color}",
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await init_selfrole_db()  # Initialize the self-role database
    await bot.add_cog(SelfRoles(bot))