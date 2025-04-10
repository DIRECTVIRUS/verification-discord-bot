from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.future import select  # Use the select construct
from sqlalchemy import Column, Integer, String, Boolean, DateTime, BigInteger
import datetime
import os

# Ensure the database folder exists
DATABASE_FOLDER = "database"
os.makedirs(DATABASE_FOLDER, exist_ok=True)

DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_FOLDER}/verification.db"

# Create the async engine and session
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

Base = declarative_base()

class Verification(Base):
    __tablename__ = "verifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, unique=True, nullable=False)
    username = Column(String, nullable=False)
    verified = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class Config(Base):
    __tablename__ = "configs"
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, unique=True, nullable=False)
    verification_channel_id = Column(BigInteger, nullable=True)
    log_channel_id = Column(BigInteger, nullable=True)
    verified_role_id = Column(BigInteger, nullable=True)  # New field for the verified role ID

async def init_db():
    """Initialize the database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_config(guild_id: int):
    """Retrieve the configuration for a guild."""
    async with async_session() as session:
        result = await session.execute(
            select(Config).where(Config.guild_id == guild_id)
        )
        return result.scalars().first()  # Use scalars().first() to return the full ORM object

async def set_config(guild_id: int, verification_channel_id: int, log_channel_id: int, verified_role_id: int):
    """Set or update the configuration for a guild."""
    async with async_session() as session:
        config = await get_config(guild_id)
        if config:
            config.verification_channel_id = verification_channel_id
            config.log_channel_id = log_channel_id
            config.verified_role_id = verified_role_id
        else:
            config = Config(
                guild_id=guild_id,
                verification_channel_id=verification_channel_id,
                log_channel_id=log_channel_id,
                verified_role_id=verified_role_id,
            )
            session.add(config)
        await session.commit()

async def add_user_verification(user_id: str, username: str):
    """Add a new user verification record."""
    async with async_session() as session:
        new_verification = Verification(
            user_id=user_id,
            username=username,
            verified=True,
            timestamp=datetime.datetime.utcnow(),
        )
        session.add(new_verification)
        await session.commit()

async def get_user_verification(user_id: str):
    """Retrieve a user's verification record."""
    async with async_session() as session:
        result = await session.execute(
            select(Verification).where(Verification.user_id == user_id)
        )
        return result.scalars().first()  # Use scalars().first() to return the full ORM object