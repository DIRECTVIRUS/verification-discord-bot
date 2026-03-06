from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.future import select
from sqlalchemy import Column, Integer, String, BigInteger, DateTime, Boolean
import datetime
import os

# Ensure the database folder exists
DATABASE_FOLDER = "database"
os.makedirs(DATABASE_FOLDER, exist_ok=True)

MODERATION_DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_FOLDER}/moderation.db"

# Create the async engine and session for moderation configuration
moderation_engine = create_async_engine(MODERATION_DATABASE_URL, echo=True)
moderation_session = sessionmaker(moderation_engine, expire_on_commit=False, class_=AsyncSession)

# Define the base for moderation models
ModerationBase = declarative_base()

class ModerationConfig(ModerationBase):
    __tablename__ = "moderation_configs"
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, unique=True, nullable=False)
    log_channel_id = Column(BigInteger, nullable=True)
    audit_logging_enabled = Column(Boolean, default=False, nullable=False)
    
    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

class ModWarning(ModerationBase):
    __tablename__ = "warnings"
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    moderator_id = Column(BigInteger, nullable=False)
    reason = Column(String, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

class Appeal(ModerationBase):
    __tablename__ = "appeals"
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    ban_reason = Column(String, nullable=False)
    appeal_reason = Column(String, nullable=False)
    status = Column(String, nullable=False)  # pending, accepted, rejected
    moderator_id = Column(BigInteger, nullable=True)  # Who handled the appeal
    moderator_response = Column(String, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    message_id = Column(BigInteger, nullable=True)  # Appeal message ID in appeal channel

async def init_moderation_db():
    """Initialize the moderation database."""
    async with moderation_engine.begin() as conn:
        await conn.run_sync(ModerationBase.metadata.create_all)

async def get_moderation_config(guild_id: int):
    """Retrieve the moderation configuration for a guild."""
    async with moderation_session() as session:
        result = await session.execute(
            select(ModerationConfig).where(ModerationConfig.guild_id == guild_id)
        )
        return result.scalars().first()

async def set_moderation_log_channel(guild_id: int, log_channel_id: int):
    """Set or update the moderation log channel for a guild."""
    async with moderation_session() as session:
        result = await session.execute(
            select(ModerationConfig).where(ModerationConfig.guild_id == guild_id)
        )
        config = result.scalars().first()
        
        if config:
            config.log_channel_id = log_channel_id
        else:
            config = ModerationConfig(
                guild_id=guild_id,
                log_channel_id=log_channel_id
            )
            session.add(config)
            
        await session.commit()

async def set_audit_logging(guild_id: int, enabled: bool):
    """Enable or disable audit logging for a guild."""
    async with moderation_session() as session:
        result = await session.execute(
            select(ModerationConfig).where(ModerationConfig.guild_id == guild_id)
        )
        config = result.scalars().first()
        
        if config:
            config.audit_logging_enabled = enabled
        else:
            config = ModerationConfig(
                guild_id=guild_id,
                audit_logging_enabled=enabled
            )
            session.add(config)
            
        await session.commit()

async def is_audit_logging_enabled(guild_id: int) -> bool:
    """Check if audit logging is enabled for a guild."""
    async with moderation_session() as session:
        result = await session.execute(
            select(ModerationConfig).where(ModerationConfig.guild_id == guild_id)
        )
        config = result.scalars().first()
        
        if config:
            return config.audit_logging_enabled
        return False

async def add_warning(guild_id: int, user_id: int, moderator_id: int, reason: str):
    """Add a new warning record."""
    async with moderation_session() as session:
        warning = ModWarning(
            guild_id=guild_id,
            user_id=user_id,
            moderator_id=moderator_id,
            reason=reason
        )
        session.add(warning)
        await session.commit()
        await session.refresh(warning)
        return warning.id

async def get_user_warnings(guild_id: int, user_id: int):
    """Get all warnings for a user in a guild."""
    async with moderation_session() as session:
        result = await session.execute(
            select(ModWarning)
            .where(ModWarning.guild_id == guild_id)
            .where(ModWarning.user_id == user_id)
            .order_by(ModWarning.timestamp.desc())
        )
        return result.scalars().all()

async def get_warning_by_id(warning_id: int):
    """Get a specific warning by its ID."""
    async with moderation_session() as session:
        result = await session.execute(
            select(ModWarning)
            .where(ModWarning.id == warning_id)
        )
        return result.scalars().first()

async def remove_warning(warning_id: int):
    """Remove a warning by ID."""
    async with moderation_session() as session:
        warning = await session.execute(
            select(ModWarning)
            .where(ModWarning.id == warning_id)
        )
        warning = warning.scalars().first()
        if warning:
            await session.delete(warning)
            await session.commit()
            return True
        return False

async def clear_user_warnings(guild_id: int, user_id: int):
    """Clear all warnings for a user in a guild."""
    async with moderation_session() as session:
        result = await session.execute(
            select(ModWarning)
            .where(ModWarning.guild_id == guild_id)
            .where(ModWarning.user_id == user_id)
        )
        warnings = result.scalars().all()
        
        if not warnings:
            return 0
        
        count = len(warnings)
        for warning in warnings:
            await session.delete(warning)
        
        await session.commit()
        return count

async def set_appeal_channel(guild_id: int, appeal_channel_id: int):
    """Set or update the appeal channel for a guild."""
    async with moderation_session() as session:
        result = await session.execute(
            select(ModerationConfig).where(ModerationConfig.guild_id == guild_id)
        )
        config = result.scalars().first()
        
        if config:
            config.appeal_channel_id = appeal_channel_id
        else:
            config = ModerationConfig(
                guild_id=guild_id,
                appeal_channel_id=appeal_channel_id
            )
            session.add(config)
            
        await session.commit()

async def create_appeal(guild_id: int, user_id: int, ban_reason: str, appeal_reason: str, message_id: int = None):
    """Create a new appeal."""
    async with moderation_session() as session:
        appeal = Appeal(
            guild_id=guild_id,
            user_id=user_id,
            ban_reason=ban_reason,
            appeal_reason=appeal_reason,
            status="pending",
            message_id=message_id
        )
        session.add(appeal)
        await session.commit()
        await session.refresh(appeal)
        return appeal.id

async def get_appeal_by_id(appeal_id: int):
    """Get a specific appeal by ID."""
    async with moderation_session() as session:
        result = await session.execute(
            select(Appeal).where(Appeal.id == appeal_id)
        )
        return result.scalars().first()

async def get_pending_appeals(guild_id: int):
    """Get all pending appeals for a guild."""
    async with moderation_session() as session:
        result = await session.execute(
            select(Appeal)
            .where(Appeal.guild_id == guild_id)
            .where(Appeal.status == "pending")
            .order_by(Appeal.timestamp.asc())
        )
        return result.scalars().all()

async def get_user_appeals(guild_id: int, user_id: int):
    """Get all appeals for a specific user in a guild."""
    async with moderation_session() as session:
        result = await session.execute(
            select(Appeal)
            .where(Appeal.guild_id == guild_id)
            .where(Appeal.user_id == user_id)
            .order_by(Appeal.timestamp.desc())
        )
        return result.scalars().all()

async def update_appeal_status(appeal_id: int, status: str, moderator_id: int, moderator_response: str = None):
    """Update an appeal's status."""
    async with moderation_session() as session:
        result = await session.execute(
            select(Appeal).where(Appeal.id == appeal_id)
        )
        appeal = result.scalars().first()
        
        if appeal:
            appeal.status = status
            appeal.moderator_id = moderator_id
            if moderator_response:
                appeal.moderator_response = moderator_response
            await session.commit()
            return True
        return False
