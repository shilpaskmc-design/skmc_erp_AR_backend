from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from skmc_erp.core.uom.model import Uom, UomStatus


class UomInputError(Exception):
    pass


async def get_uom(*, session: AsyncSession, code: str) -> Uom | None:
    return await session.get(Uom, code.strip().upper())


async def list_active_uoms(*, session: AsyncSession) -> Sequence[Uom]:
    stmt = select(Uom).where(Uom.status == UomStatus.ACTIVE).order_by(Uom.code)
    result = await session.scalars(stmt)
    return result.all()


async def validate_uom_code(
    *, session: AsyncSession, uom_code: str | None
) -> str | None:
    if uom_code is None:
        return None
    normalized = uom_code.strip().upper()
    if not normalized:
        raise UomInputError("UOM code cannot be blank")
    uom = await session.get(Uom, normalized)
    if uom is None:
        raise UomInputError(f"UOM '{normalized}' does not exist")
    if uom.status != UomStatus.ACTIVE:
        raise UomInputError(f"UOM '{normalized}' is inactive")
    return normalized
