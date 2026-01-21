from fastapi import APIRouter
from models.request_models import GetSessionRequest
from services.facebook import FacebookService

router = APIRouter()


@router.post("/get_session/")
async def getPages(data: GetSessionRequest):
    resultado = await FacebookService.get_session(cookies=data.cookies)
    return resultado
