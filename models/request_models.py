from pydantic import BaseModel
from typing import List


class Cookie(BaseModel):
    name: str
    value: str


class PublishRequest(BaseModel):
    id: str
    cookies: List[Cookie]
    title: str| None = None
    comment: str | None = None
    image_base64: str | None = None


class GetPagesRequest(BaseModel):
    cookies: List[Cookie]


class GetSessionRequest(BaseModel):
    cookies: List[Cookie]


class LoginRequest(BaseModel):
    email: str
    encpass: str  # manual.py: valor completo "#PWD_BROWSER:0:...:..."
    wait_2fa_seconds: int | None = 60
