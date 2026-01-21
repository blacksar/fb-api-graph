from fastapi import APIRouter, HTTPException, status
from models.request_models import PublishRequest
from services.facebook import FacebookService

router = APIRouter()


@router.post("/publish/")
async def publish(data: PublishRequest):
    try:
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
            raise HTTPException(
                status_code=status_code if 400 <= status_code < 600 else status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=mensaje
            )
        
        return {"status": "ok", "resultado": resultado}
    
    except HTTPException:
        # Re-lanzar excepciones HTTP que ya fueron creadas
        raise
    except Exception as e:
        # Capturar cualquier otro error inesperado
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

