import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Select, View
from modules.selfroles_db import (
    get_selfrole_config,
    set_selfrole_config,
    delete_selfrole_config,
    get_all_selfrole_configs,
    init_selfrole_db,
)
import json


class SelfRoleDropdown(Select):
    def __init__(self, roles_and_labels: list[tuple[discord.Role, str]]):
        options = [
            discord.SelectOption(label=label, value=str(role.id))
            for role, label in roles_and_labels
        ]
        super().__init__(placeholder="Select a role...", options=options, custom_id="selfrole_dropdown")

    async def callback(self, interaction: discord.Interaction):
        selected_role_id = int(self.values[0])  # Get the selected role ID
        role = interaction.guild.get_role(selected_role_id)
        member = interaction.user

        try:
            if role in member.roles:
                # Remove the role if the user already has it
                await member.remove_roles(role)
                embed = discord.Embed(
                    title="Role Removed",
                    description=f"Removed {role.name}",
                    color=discord.Color.red(),
                )
            else:
                # Add the role if the user doesn't have it
                await member.add_roles(role)
                embed = discord.Embed(
                    title="Role Added",
                    description=f"Added {role.name}",
                    color=discord.Color.green(),
                )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.Forbidden:
            embed = discord.Embed(
                title="Error",
                description="Missing permission: Manage Roles",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(
                title="Error",
                description=f"Unexpected error: {e}",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class SelfRolesView(View):
    def __init__(self, roles_and_labels: list[tuple[discord.Role, str]]):
        super().__init__(timeout=None)  # Persistent view
        self.add_item(SelfRoleDropdown(roles_and_labels))


class SelfRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("SelfRoles cog loaded.")  # Print message when the cog is loaded

    @commands.Cog.listener()
    async def on_ready(self):
        """Register persistent views for self-roles on bot startup."""
        print("Registering persistent self-role views...")
        configs = await get_all_selfrole_configs(self.bot.user.id)  # Fetch all self-role configurations
        for config in configs:
            roles_and_labels = json.loads(config.roles_and_labels)
            roles_and_labels_parsed = [
                (self.bot.get_guild(config.guild_id).get_role(int(role_id)), label)
                for role_id, label in roles_and_labels.items()
            ]

            # Create the view and register it globally
            view = SelfRolesView(roles_and_labels_parsed)
            self.bot.add_view(view)  # Register the persistent view globally
            print(f"Registered persistent view for message: {config.message_name}")

    @app_commands.command(name="set_selfroles", description="Configure self-assignable roles for the server.")
    @app_commands.describe(
        message_name="A unique name for this self-role message.",
        roles_and_labels="Provide role IDs and labels in the format role_id:label, separated by spaces.",
        embed_title="The title of the embed message.",
        embed_description="The description of the embed message.",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def set_selfroles(
        self,
        interaction: discord.Interaction,
        message_name: str,
        roles_and_labels: str,
        embed_title: str = "Self-Assignable Roles",
        embed_description: str = "Select a role from the dropdown menu below.",
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
                    description="Invalid format: use `role_id:label`",
                    color=discord.Color.red(),
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

        if not roles_and_labels_parsed:
            embed = discord.Embed(
                title="Error",
                description="No valid roles provided",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Save the configuration to the database
        await set_selfrole_config(
            interaction.guild.id,
            message_name,
            roles_and_labels_parsed,
            "primary",  # Button color is no longer used
            embed_title,
            embed_description,
        )

        # Notify the user
        embed = discord.Embed(
            title="Success",
            description=f"Self-roles updated: {message_name}",
            color=discord.Color.green(),
        )
        for role_id, label in roles_and_labels_parsed.items():
            role = interaction.guild.get_role(int(role_id))
            embed.add_field(name=label, value=f"Role: {role.mention} (ID: {role.id})", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="send_selfroles", description="Send the self-roles message in the configured channel.")
    @app_commands.describe(
        message_name="The name of the self-role message to send.",
        channel="The channel where the self-roles message should be sent.",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def send_selfroles(self, interaction: discord.Interaction, message_name: str, channel: discord.TextChannel):
        """
        Slash command to send the self-roles message to a specified channel.
        """
        config = await get_selfrole_config(interaction.guild.id, message_name)
        if not config:
            embed = discord.Embed(
                title="Error",
                description=f"Configuration not found: {message_name}",
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
            title=config.embed_title,
            description=config.embed_description,
            color=discord.Color.blue(),
        )
        for role, label in roles_and_labels_parsed:
            embed.add_field(name=label, value=f"Role: {role.mention} (ID: {role.id})", inline=False)

        # Create the view with the dropdown menu
        view = SelfRolesView(roles_and_labels_parsed)

        # Send the message to the specified channel
        await channel.send(embed=embed, view=view)

        # Notify the user that the message was sent
        embed = discord.Embed(
            title="Success",
            description=f"Self-roles message sent to {channel.mention}",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Register the view globally to make it persistent
        self.bot.add_view(view)

    @app_commands.command(name="delete_selfroles", description="Delete a self-roles configuration.")
    @app_commands.describe(message_name="The name of the self-role message to delete.")
    @app_commands.checks.has_permissions(administrator=True)
    async def delete_selfroles(self, interaction: discord.Interaction, message_name: str):
        """
        Slash command to delete a self-roles configuration.
        """
        config = await get_selfrole_config(interaction.guild.id, message_name)
        if not config:
            embed = discord.Embed(
                title="Error",
                description=f"Configuration not found: {message_name}",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Delete the configuration from the database
        await delete_selfrole_config(interaction.guild.id, message_name)

        # Notify the user
        embed = discord.Embed(
            title="Success",
            description=f"Configuration deleted: {message_name}",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="list_selfroles", description="List all self-role configurations for this server.")
    @app_commands.checks.has_permissions(administrator=True)
    async def list_selfroles(self, interaction: discord.Interaction):
        """
        Slash command to list all self-role configurations for the server.
        """
        configs = await get_all_selfrole_configs(interaction.guild.id)
        if not configs:
            embed = discord.Embed(
                title="Notice",
                description="No self-role configurations exist",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Create a list of message names
        message_names = "\n".join([f"- **{config.message_name}**" for config in configs])

        embed = discord.Embed(
            title="Self-Role Configurations",
            description=message_names,
            color=discord.Color.blue(),
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="show_selfrole_config", description="Show the self-role configuration for a specific message.")
    @app_commands.describe(message_name="The name of the self-role message to show.")
    @app_commands.checks.has_permissions(administrator=True)
    async def show_selfrole_config(self, interaction: discord.Interaction, message_name: str):
        """
        Slash command to show the self-role configuration for a specific message.
        """
        config = await get_selfrole_config(interaction.guild.id, message_name)
        if not config:
            embed = discord.Embed(
                title="Error",
                description=f"Configuration not found: {message_name}",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Parse the roles and labels from the configuration
        roles_and_labels = json.loads(config.roles_and_labels)
        roles_formatted = "\n".join(
            [f"- **{label}**: <@&{role_id}>" for role_id, label in roles_and_labels.items()]
        )

        embed = discord.Embed(
            title=f"Configuration: {message_name}",
            description="Configuration details:",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Embed Title", value=config.embed_title, inline=False)
        embed.add_field(name="Embed Description", value=config.embed_description, inline=False)
        embed.add_field(name="Roles", value=roles_formatted, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await init_selfrole_db()  # Initialize the self-role database
    await bot.add_cog(SelfRoles(bot))