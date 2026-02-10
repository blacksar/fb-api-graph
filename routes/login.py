from fastapi import APIRouter, HTTPException
from models.request_models import Cookie, LoginRequest
from services.auth import login_facebook, _cookies_to_browser_format
from services.facebook import FacebookService

router = APIRouter()


def _ensure_browser_format(cookies: list) -> list:
    """Siempre convierte a formato navegador (expirationDate, booleanos JSON)."""
    if not cookies or not isinstance(cookies[0], dict):
        return cookies
    return _cookies_to_browser_format(cookies)


# Prefijo fijo: encpass = PREFIX + pass (el cliente solo envía "pass")
ENCPASS_PREFIX = "#PWD_BROWSER:0:1628896342:"


@router.post("/login/")
async def login(data: LoginRequest):
    wait = data.wait_2fa_seconds if data.wait_2fa_seconds is not None else 60
    encpass = ENCPASS_PREFIX + data.password
    resultado = await login_facebook(
        email=data.email,
        encpass=encpass,
        wait_2fa_seconds=max(wait, 60),
    )
    if not resultado.get("ok"):
        raise HTTPException(
            status_code=resultado.get("status_code", 500),
            detail=resultado.get("mensaje", "Error en login"),
        )
    cookies = _ensure_browser_format(resultado.get("cookies", []))
    # Obtener nombre de la sesión (c_user y name) con las cookies recién obtenidas
    cookies_for_session = [Cookie(name=c["name"], value=c["value"]) for c in cookies]
    session_info = await FacebookService.get_session(cookies_for_session)
    session = {
        "name": session_info.get("name"),
        "c_user": session_info.get("c_user"),
    }
    return {"status": "ok", "cookies": cookies, "session": session}
