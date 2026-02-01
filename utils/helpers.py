import base64
import uuid
import random
import httpx
import re


async def base64_to_bytes(base64_str):
    _, content = base64_str.split(",", 1)
    return base64.b64decode(content)


#####
def generar_session_id():
    try:
        return str(uuid.uuid4())
    except Exception:

        def reemplazo(c):
            b = random.randint(0, 15)
            return hex((b & 0x3) | 0x8)[2:] if c == "y" else hex(b)[2:]

        plantilla = "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx"
        return "".join(reemplazo(c) if c in "xy" else c for c in plantilla)


#####
async def get_params(client: httpx.AsyncClient):
    response = await client.get("https://www.facebook.com/")
    html = response.text

    # Extrae los tokens de Facebook usando expresiones regulares
    def h(a, e):
        if e == "mix":
            r = "abcdefghijklmnopqrstuvwxyz"
        else:
            r = "0123456789"

        t = ""
        for _ in range(a):
            t += random.choice(r)

        return t

    try:
        return {
            "av": re.search(r'"actorId":"(.*?)"', html).group(1),
            "accountId": re.search(r'"accountId":"(.*?)"', html).group(1),
            "__user": re.search(r'"actorId":"(.*?)"', html).group(1),
            "__a": "1",
            "__req": "1",
            "__hs": re.search(r'"haste_session":"(.*?)"', html).group(1),
            "dpr": 1,
            "__ccg": "EXCELLENT",
            "__rev": re.search(r'"client_revision":(.*?),', html).group(1),
            "__s": f"{h(6, 'mix')}:{h(6, 'mix')}:{h(6, 'mix')}",
            "__hsi": re.search(r'"hsi":"(.*?)"', html).group(1),
            "__dyn": h(376, "mix"),
            "__csr": h(376, "mix"),
            "__hsdp": h(813, "mix"),
            "__hblp": h(578, "mix"),
            "tracking_hash": "AZW" + h(213, "mix"),
            "__comet_req": re.search(r'"comet_env":(\d+)', html).group(1),
            "fb_dtsg": re.search(
                r'\["DTSGInitialData",\[\],\{"token":"(.*?)"', html
            ).group(1),
            "async_get_token": re.search(r'"async_get_token":"(.*?)"', html).group(1),
            "jazoest": re.search(r'\["SprinkleConfig",\[\],\{.*?\},(\d+)]', html).group(
                1
            ),
            "lsd": re.search(r'\["LSD",\[\],\{"token":"(.*?)"', html).group(1),
            "__spin_r": re.search(r'"__spin_r":(.*?),', html).group(1),
            "__spin_b": "trunk",
            "__spin_t": re.search(r'"__spin_t":(.*?),', html).group(1),
            "__aaid": "9432643450167108",
        }
    except Exception:
        raise


def get_headers():
    return {
        "Accept-Language": "es-ES,es;q=0.9",
    }
