from fastapi import APIRouter
from models.request_models import GetPagesRequest
from services.facebook import FacebookService

router = APIRouter()


@router.post("/get_pages/")
async def getPages(data: GetPagesRequest):
    resultado = await FacebookService.get_pages(cookies=data.cookies)
    return {"status": "ok", "resultado": resultado}
