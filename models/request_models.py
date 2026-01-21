from pydantic import BaseModel
from typing import List


class Cookie(BaseModel):
    name: str
    value: str


class PublishRequest(BaseModel):
    id: str
    cookies: List[Cookie]
    title: str
    comment: str
    image_base64: str


class GetPagesRequest(BaseModel):
    cookies: List[Cookie]


class GetSessionRequest(BaseModel):
    cookies: List[Cookie]
