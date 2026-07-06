from datetime import datetime
from typing import Optional

from fastapi_users import schemas


class UserRead(schemas.BaseUser[str]):
    name: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class UserUpdate(schemas.BaseUserUpdate):
    name: Optional[str] = None
