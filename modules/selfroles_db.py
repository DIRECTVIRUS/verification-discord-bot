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
    guild_id = Column(BigInteger, unique=True, nullable=False)
    roles_and_labels = Column(String, nullable=False)  # Store roles and labels as a JSON string

async def init_selfrole_db():
    """Initialize the self-role database."""
    async with selfrole_engine.begin() as conn:
        await conn.run_sync(SelfRoleBase.metadata.create_all)

async def get_selfrole_config(guild_id: int):
    """Retrieve the self-role configuration for a guild."""
    async with selfrole_session() as session:
        result = await session.execute(
            select(SelfRoleConfig).where(SelfRoleConfig.guild_id == guild_id)
        )
        return result.scalars().first()

async def set_selfrole_config(guild_id: int, roles_and_labels: dict):
    """Set or update the self-role configuration for a guild."""
    async with selfrole_session() as session:
        # Check if a configuration already exists for the guild
        result = await session.execute(
            select(SelfRoleConfig).where(SelfRoleConfig.guild_id == guild_id)
        )
        config = result.scalars().first()

        if config:
            # Update the existing configuration
            config.roles_and_labels = json.dumps(roles_and_labels)
        else:
            # Create a new configuration if none exists
            config = SelfRoleConfig(
                guild_id=guild_id,
                roles_and_labels=json.dumps(roles_and_labels),
            )
            session.add(config)

        # Commit the changes to the database
        await session.commit()