from fastapi import APIRouter, HTTPException, status
import traceback
from models.request_models import PublishRequest
from services.facebook import FacebookService

router = APIRouter()


@router.post("/publish/")
async def publish(data: PublishRequest):
    try:
        print(
            "[publish] request: id={id} cookies={cookies} has_image={has_image} title_len={title_len} comment_len={comment_len}".format(
                id=repr(data.id),
                cookies=len(data.cookies) if data.cookies else 0,
                has_image=bool(data.image_base64),
                title_len=len(data.title) if data.title else 0,
                comment_len=len(data.comment) if data.comment else 0,
            )
        )
        resultado = await FacebookService.post_publish(
            id=data.id,
            cookies=data.cookies,
            title=data.title,
            comment=data.comment,
            image_base64=data.image_base64,
        )

        # Verificar si el resultado contiene un error (status_code diferente de 200)
        if isinstance(resultado, dict) and resultado.get("status_code") != 200:
            status_code = resultado.get("status_code", 500)
            mensaje = resultado.get("mensaje", "Error al publicar")
            print(
                "[publish] result error: status_code={status_code} mensaje={mensaje}".format(
                    status_code=status_code, mensaje=mensaje
                )
            )
            raise HTTPException(
                status_code=(
                    status_code
                    if 400 <= status_code < 600
                    else status.HTTP_500_INTERNAL_SERVER_ERROR
                ),
                detail=mensaje,
            )

        return {"status": "ok", "resultado": resultado}

    except HTTPException:
        # Re-lanzar excepciones HTTP que ya fueron creadas
        raise
    except Exception as e:
        # Capturar cualquier otro error inesperado
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}",
        )
