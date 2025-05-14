from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.future import select
from sqlalchemy import Column, Integer, String, BigInteger
import os
import json

# Ensure the database folder exists
DATABASE_FOLDER = "database"
os.makedirs(DATABASE_FOLDER, exist_ok=True)

SELFROLE_DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_FOLDER}/selfroles.db"

# Create the async engine and session for self-role configuration
selfrole_engine = create_async_engine(SELFROLE_DATABASE_URL, echo=True)
selfrole_session = sessionmaker(selfrole_engine, expire_on_commit=False, class_=AsyncSession)

# Define the base for self-role models
SelfRoleBase = declarative_base()

class SelfRoleConfig(SelfRoleBase):
    __tablename__ = "selfrole_configs"
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, nullable=False)
    message_name = Column(String, nullable=False)  # Unique name for each message
    roles_and_labels = Column(String, nullable=False)  # Store roles and labels as a JSON string
    button_color = Column(String, nullable=False, default="primary")  # Button color (primary, secondary, success, danger)
    embed_title = Column(String, nullable=False, default="Self-Assignable Roles")  # Embed title
    embed_description = Column(String, nullable=False, default="Click the buttons below to assign or remove roles.")  # Embed description

    __table_args__ = (
        # Ensure unique configurations per guild and message name
        {"sqlite_autoincrement": True},
    )

async def init_selfrole_db():
    """Initialize the self-role database."""
    async with selfrole_engine.begin() as conn:
        await conn.run_sync(SelfRoleBase.metadata.create_all)

async def get_selfrole_config(guild_id: int, message_name: str):
    """Retrieve the self-role configuration for a specific guild and message name."""
    async with selfrole_session() as session:
        result = await session.execute(
            select(SelfRoleConfig).where(
                SelfRoleConfig.guild_id == guild_id,
                SelfRoleConfig.message_name == message_name
            )
        )
        return result.scalars().first()

async def set_selfrole_config(guild_id: int, message_name: str, roles_and_labels: dict, button_color: str, embed_title: str, embed_description: str):
    """Set or update the self-role configuration for a guild and message name."""
    async with selfrole_session() as session:
        # Check if a configuration already exists for the guild and message name
        result = await session.execute(
            select(SelfRoleConfig).where(
                SelfRoleConfig.guild_id == guild_id,
                SelfRoleConfig.message_name == message_name
            )
        )
        config = result.scalars().first()

        if config:
            # Update the existing configuration
            config.roles_and_labels = json.dumps(roles_and_labels)
            config.button_color = button_color
            config.embed_title = embed_title
            config.embed_description = embed_description
        else:
            # Create a new configuration if none exists
            config = SelfRoleConfig(
                guild_id=guild_id,
                message_name=message_name,
                roles_and_labels=json.dumps(roles_and_labels),
                button_color=button_color,
                embed_title=embed_title,
                embed_description=embed_description,
            )
            session.add(config)

        # Commit the changes to the database
        await session.commit()

async def get_all_selfrole_configs(guild_id: int):
    """Retrieve all self-role configurations for a specific guild."""
    async with selfrole_session() as session:
        result = await session.execute(
            select(SelfRoleConfig).where(SelfRoleConfig.guild_id == guild_id)
        )
        return result.scalars().all()

async def delete_selfrole_config(guild_id: int, message_name: str):
    """Delete a specific self-role configuration for a guild and message name."""
    async with selfrole_session() as session:
        result = await session.execute(
            select(SelfRoleConfig).where(
                SelfRoleConfig.guild_id == guild_id,
                SelfRoleConfig.message_name == message_name
            )
        )
        config = result.scalars().first()

        if config:
            await session.delete(config)
            await session.commit()