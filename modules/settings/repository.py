from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import SystemSetting


async def list_system_setting_records(db: AsyncSession) -> list[SystemSetting]:
    query = select(SystemSetting).order_by(SystemSetting.key.asc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_system_setting_record(db: AsyncSession, key: str) -> SystemSetting | None:
    query = select(SystemSetting).where(SystemSetting.key == key)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def delete_all_system_setting_records(db: AsyncSession) -> None:
    await db.execute(delete(SystemSetting))
