import httpx
import json
import re
from typing import List
from models.request_models import Cookie
from services.facebook_steps import (
    get_params,
    posting_post,
    base64_to_bytes,
    feedback_start_typing,
    posting_comment,
)


class FacebookService:
    @staticmethod
    async def post_publish(
        id: str, cookies: List[Cookie], title: str, comment: str, image_base64: str
    ):
        cookies_dict = {c.name: c.value for c in cookies}
        cookies_dict["i_user"] = id  # ← Agregas manualmente esta cookie
        #
        session = await FacebookService.get_session(cookies)

        if session["status_code"] != 200:
            return session

        async with httpx.AsyncClient(cookies=cookies_dict) as client:
            data = await get_params(client)
            binary = await base64_to_bytes(image_base64)
            # Subir imagen
            response = await client.post(
                "https://upload.facebook.com/ajax/react_composer/attachments/photo/upload",
                params={
                    "av": data["av"],
                    "__user": data["av"],
                    "__a": "1",
                    "fb_dtsg": data["fb_dtsg"],
                    "lsd": data["lsd"],
                    "__spin_r": data["__spin_r"],
                    "__spin_b": "trunk",
                    "__spin_t": data["__spin_t"],
                },
                files={
                    "source": (None, "8"),
                    "profile_id": (None, data["av"]),
                    "waterfallxapp": (None, "comet"),
                    "farr": ("imagen.jpeg", binary, "image/jpeg"),
                    "upload_id": (None, "jsc_c_8"),
                },
            )

            text = response.text
            match = re.search(r'"photoID":"(.*?)"', text)
            #
            if match:
                photo_id = match.group(1)
            else:
                return {
                    "status_code": 400,
                    "mensaje": "❌ No se encontró photoID.\nRespuesta:",
                    "respuesta": text,
                }

            feedback_id = await posting_post(client, photo_id, title)
            await client.get("https://www.facebook.com/")
            await feedback_start_typing(client, feedback_id)
            final = await posting_comment(client, feedback_id, comment)

        return final

    async def get_pages(cookies: List[Cookie]):
        cookies_dict = {c.name: c.value for c in cookies}

        session = await FacebookService.get_session(cookies)

        if session["status_code"] != 200:
            return session

        async with httpx.AsyncClient(cookies=cookies_dict) as client:
            data = await get_params(client)
            payload = {
                "av": data["av"],
                "__aaid": "0",
                "__user": data["av"],
                "__a": "1",
                "__req": "1",
                "__hs": data["__hs"],
                "dpr": "1",
                "__ccg": "EXCELLENT",
                "__rev": data["__rev"],
                "__s": data["__s"],
                "__hsi": data["__hsi"],
                "__dyn": data["__dyn"],
                "__csr": data["__csr"],
                "__hsdp": data["__hsdp"],
                "__hblp": data["__hblp"],
                "__comet_req": "15",
                "fb_dtsg": data["fb_dtsg"],
                "jazoest": data["jazoest"],
                "lsd": data["lsd"],
                "__spin_r": data["__spin_r"],
                "__spin_b": "trunk",
                "__spin_t": data["__spin_t"],
                "__crn": "comet.fbweb.CometHomeRoute",
                "fb_api_caller_class": "RelayModern",
                "fb_api_req_friendly_name": "PageCometLaunchpointLeftNavMenuRootQuery",
                "variables": '{"useAdminedPagesForActingAccount":true,"useNewPagesYouManage":true}',
                "server_timestamps": "true",
                "doc_id": "9750115298417028",
            }

            response = await client.post(
                "https://www.facebook.com/api/graphql/", data=payload
            )

            # Verifica si la respuesta es exitosa
            if response.status_code == 200:
                regex = r'"profile"\s*:\s*\{.*?"id"\s*:\s*"(\d+)"[\s\S]*?"name"\s*:\s*"([^"]+)"[\s\S]*?"can_manage_classic_page_in_pages_tab"\s*:\s*false'
                resultados = []

                for match in re.finditer(regex, response.text, re.DOTALL):
                    resultados.append({"id": match.group(1), "name": match.group(2)})

                return {
                    "status_code": 200,
                    "resultado": json.dumps(resultados),
                }

    async def get_session(cookies: List[Cookie]):
        cookies_dict = {c.name: c.value for c in cookies}
        try:
            async with httpx.AsyncClient(cookies=cookies_dict) as client:
                response = await client.get("https://www.facebook.com/")
                html = response.text
                match_actor = re.search(r'"actorId":"(.*?)"', html)
                match_name = re.search(r'"USER_ID":".*?","NAME":"(.*?)"', html)

                if match_actor and match_name:
                    active = match_actor.group(1)
                    userName = match_name.group(1)
                    return {
                        "status_code": 200,
                        "mensaje": "✅ Sesión activa",
                        "c_user": active,
                        "name": userName,
                    }
                else:
                    return {
                        "status_code": 400,
                        "mensaje": "❌ No se encontró actorId o name en el HTML",
                        "c_user": None,
                        "name": None,
                    }
        except Exception as e:
            return {
                "status_code": 500,
                "mensaje": f"❌ Error en get_session: {str(e)}",
                "c_user": None,
                "name": None,
            }
