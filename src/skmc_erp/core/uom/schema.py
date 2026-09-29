from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from skmc_erp.core.uom.model import UomStatus

UomCode = Annotated[
    str, StringConstraints(strip_whitespace=True, pattern=r"^[A-Za-z0-9_]{1,20}$")
]


class UomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    symbol: str | None
    uqc_code: str | None
    status: UomStatus
    created_at: datetime
    updated_at: datetime
