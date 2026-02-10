"""
Login a Facebook: GET home → POST login → si hay 2FA, Playwright o polling hasta c_user.
Misma lógica que manual.py; la API ejecuta login_with_cookies en un hilo.
"""
import asyncio
import re
import time
from time import sleep
from typing import Any
from urllib.parse import urljoin

import httpx

# Cookies y headers (igual que manual.py)
COOKIES = {"datr": "J3Zwacud3dLST2sXfsrenol4"}
HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "accept-language": "es-419,es;q=0.9,es-ES;q=0.8,en;q=0.7,en-GB;q=0.6,en-US;q=0.5",
    "cache-control": "max-age=0",
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
}


def _extract_form(html: str):
    """Primer form del HTML: action y dict de inputs hidden."""
    m = re.search(r'<form[^>]*action="([^"]+)"[^>]*>', html, re.IGNORECASE)
    if not m:
        return None, {}
    action = m.group(1)
    block = re.search(rf'<form[^>]*action="{re.escape(action)}"[^>]*>.*?</form>', html, re.IGNORECASE | re.DOTALL)
    form_html = block.group(1) if block else html
    inputs = {}
    for tag in re.finditer(r"<input[^>]*>", form_html, re.IGNORECASE):
        t = tag.group(0)
        typ = re.search(r'type="([^"]+)"', t, re.IGNORECASE)
        if typ and typ.group(1).lower() != "hidden":
            continue
        nm = re.search(r'name="([^"]+)"', t, re.IGNORECASE)
        if not nm:
            continue
        vm = re.search(r'value="([^"]*)"', t, re.IGNORECASE)
        inputs[nm.group(1)] = vm.group(1) if vm else ""
    return action, inputs


def _playwright_2fa(checkpoint_url: str, client: httpx.Client, wait_time: int = 120, poll_interval: int = 2):
    """Abre la página de checkpoint en Playwright y espera cookie c_user. Retorna lista de cookies o None."""
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return None
    with sync_playwright() as p:
        # Argumentos necesarios para Chromium dentro de Docker
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--single-process",
                "--no-zygote",
                "--disable-background-networking",
                "--disable-default-apps",
                "--disable-extensions",
                "--disable-sync",
                "--metrics-recording-only",
                "--mute-audio",
            ],
        )
        context = browser.new_context(user_agent=HEADERS.get("user-agent"), locale="es-LA")
        pw_cookies = [
            {
                "name": c.name,
                "value": c.value,
                "domain": c.domain or ".facebook.com",
                "path": c.path or "/",
                "secure": bool(c.secure),
                "httpOnly": bool(getattr(c, "rest", {}).get("HttpOnly", False)),
                **({"expires": c.expires} if c.expires else {}),
            }
            for c in client.cookies.jar
        ]
        if pw_cookies:
            context.add_cookies(pw_cookies)
        page = context.new_page()
        page.goto(str(checkpoint_url), wait_until="domcontentloaded")
        deadline = time.time() + wait_time
        while time.time() < deadline:
            now = context.cookies("https://www.facebook.com/")
            if any(c["name"] == "c_user" for c in now):
                browser.close()
                return now
            time.sleep(poll_interval)
        browser.close()
    return None


def _cookies_list(client: httpx.Client) -> list[dict]:
    """Lista de dicts con las cookies del client (para respuesta API)."""
    out = []
    for c in client.cookies.jar:
        d = {"name": c.name, "value": c.value, "domain": c.domain, "path": c.path, "secure": c.secure, "expires": c.expires}
        d["httpOnly"] = bool(getattr(c, "rest", {}).get("HttpOnly", False))
        out.append(d)
    return out


def _cookies_list_from_pw(pw_cookies: list) -> list[dict]:
    """Lista de dicts desde cookies devueltas por Playwright."""
    return [
        {
            "name": c["name"], "value": c["value"], "domain": c["domain"], "path": c["path"],
            "secure": c.get("secure", False), "expires": c.get("expires"),
            "httpOnly": c.get("httpOnly", False),
        }
        for c in pw_cookies
    ]


def _cookies_to_browser_format(cookies_list: list[dict]) -> list[dict]:
    """
    Convierte las cookies al formato exacto de las extensiones del navegador.
    Acepta entrada con "expires" (crudo) o "expirationDate" (ya formateado).
    Salida: domain, expirationDate (solo si no session), hostOnly, httpOnly, name,
    path, sameSite, secure, session, storeId, value. Tipos JSON puros (bool, no string).
    """
    COOKIES_NO_HTTPONLY = {"c_user", "locale", "wd", "presence"}
    out = []
    for c in cookies_list:
        # Aceptar tanto "expires" (crudo) como "expirationDate" (ya formateado)
        exp = c.get("expires") if "expires" in c else c.get("expirationDate")
        is_session = exp is None or exp == -1
        name = c.get("name", "")
        if "httpOnly" in c:
            http_only = bool(c["httpOnly"]) if isinstance(c["httpOnly"], bool) else (c["httpOnly"] not in ("false", "0", ""))
        else:
            http_only = name not in COOKIES_NO_HTTPONLY
        if is_session:
            same_site = None
        elif name == "wd":
            same_site = "lax"
        else:
            same_site = "no_restriction"
        # expirationDate: número (float/int), solo para no-session
        if not is_session and exp is not None and exp != -1:
            exp_num = float(exp) if not isinstance(exp, (int, float)) else exp
        else:
            exp_num = None
        secure_val = c.get("secure", True)
        if isinstance(secure_val, str):
            secure_bool = secure_val.lower() in ("true", "1", "yes")
        else:
            secure_bool = bool(secure_val)
        item = {"domain": c.get("domain") or ".facebook.com"}
        if exp_num is not None:
            item["expirationDate"] = exp_num
        item["hostOnly"] = False
        item["httpOnly"] = http_only
        item["name"] = name
        item["path"] = c.get("path") or "/"
        item["sameSite"] = same_site
        item["secure"] = secure_bool
        item["session"] = is_session
        item["storeId"] = None
        item["value"] = str(c.get("value", ""))
        out.append(item)
    return out


def _cookies_for_browser(cookies_list: list[dict]) -> list[dict]:
    """
    Normaliza las cookies para que sean compatibles con navegadores/JSON:
    booleanos como "true"/"false" (minúsculas), expires como número o null.
    (Mantenido por compatibilidad; para formato de extensión usar _cookies_to_browser_format.)
    """
    out = []
    for c in cookies_list:
        out.append({
            "name": c.get("name", ""),
            "value": c.get("value", ""),
            "domain": c.get("domain") or "",
            "path": c.get("path") or "/",
            "secure": "true" if c.get("secure") else "false",
            "expires": c.get("expires") if c.get("expires") is not None else None,
        })
    return out


def login_with_cookies(email: str, encpass: str, wait_2fa_seconds: int = 60) -> tuple[bool, list, int]:
    """
    Flujo de login: GET home → lsd/jazoest → POST login → c_user o 2FA (Playwright + polling).
    Retorna (ok, cookies_list, status_code).
    ok=True -> cookies_list con las cookies de sesión, status_code=200.
    ok=False -> cookies_list=[], status_code 401 (login fallido), 408 (2FA timeout) o 500 (error).
    """
    post_headers = {
        **HEADERS,
        "content-type": "application/x-www-form-urlencoded",
        "origin": "https://www.facebook.com",
        "referer": "https://www.facebook.com/",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin",
        "sec-fetch-user": "?1",
    }

    with httpx.Client(cookies=COOKIES, headers=HEADERS, follow_redirects=True, timeout=30, http2=True) as client:
        try:
            r_home = client.get("https://www.facebook.com/")
        except Exception:
            return False, [], 500
        if r_home.status_code != 200:
            return False, [], 500

        html = r_home.text
        lsd = re.search(r'name="lsd"\s+value="([^"]+)"', html)
        jazoest = re.search(r'name="jazoest"\s+value="([^"]+)"', html)
        action = re.search(r'action="(/login/[^"]+)"', html)
        if not lsd or not jazoest:
            return False, [], 500

        url_post = f"https://www.facebook.com{action.group(1).replace('&amp;', '&')}" if action else "https://www.facebook.com/login/device-based/regular/login/?login_attempt=1&lwv=100"
        data = {"jazoest": jazoest.group(1), "lsd": lsd.group(1), "email": email, "login_source": "comet_headerless_login", "next": "", "encpass": encpass}
        r = client.post(url_post, data=data, headers=post_headers)

        if "c_user" in client.cookies:
            return True, _cookies_list(client), 200

        # Si la URL no es 2FA/checkpoint, el email o la contraseña son incorrectos
        if "two_step_verification" not in str(r.url) and "checkpoint" not in str(r.url) and "lsrc=lb" not in str(r.url):
            return False, [], 401

        checkpoint_url = r.url
        if "APPROVE_FROM_ANOTHER_DEVICE" in r.text:
            pw_cookies = _playwright_2fa(checkpoint_url, client)
            if pw_cookies:
                for c in pw_cookies:
                    client.cookies.set(c["name"], c["value"], domain=c["domain"], path=c["path"])
                return True, _cookies_list_from_pw(pw_cookies), 200

        wait_time = max(wait_2fa_seconds, 60)
        for _ in range(wait_time, 0, -5):
            try:
                r_check = client.get(checkpoint_url, follow_redirects=False)
                if "location" in r_check.headers:
                    checkpoint_url = urljoin(str(r_check.url), r_check.headers["location"])
                    r_check = client.get(checkpoint_url)
                action_path, form_data = _extract_form(r_check.text)
                if action_path and form_data:
                    submit_url = urljoin(str(r_check.url), action_path)
                    r_submit = client.post(submit_url, data=form_data, headers={**HEADERS, "content-type": "application/x-www-form-urlencoded", "origin": "https://www.facebook.com", "referer": str(r_check.url)})
                    checkpoint_url = r_submit.url
                if "c_user" not in client.cookies:
                    client.get("https://www.facebook.com/")
                if "c_user" in client.cookies:
                    return True, _cookies_list(client), 200
            except Exception:
                pass
            sleep(5)
        return False, [], 408


def _mensaje_status(code: int) -> str:
    if code == 401:
        return "Email o contraseña incorrectos."
    if code == 408:
        return "Tiempo agotado esperando 2FA."
    return "Error en el servidor."


async def login_facebook(email: str, encpass: str, wait_2fa_seconds: int = 60) -> dict[str, Any]:
    """
    Ejecuta login_with_cookies en un hilo (para no bloquear FastAPI).
    Retorna {"ok": True, "cookies": [...]} o {"ok": False, "status_code": N, "mensaje": "..."}.
    """
    try:
        ok, cookies_list, status_code = await asyncio.to_thread(
            login_with_cookies, email, encpass, wait_2fa_seconds
        )
    except Exception as e:
        return {"ok": False, "status_code": 500, "mensaje": str(e)}
    if ok:
        return {"ok": True, "cookies": _cookies_to_browser_format(cookies_list)}
    return {
        "ok": False,
        "status_code": status_code,
        "mensaje": _mensaje_status(status_code),
    }
