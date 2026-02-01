import httpx
import json
import re
import traceback
from typing import List, Optional, Dict, Any
from models.request_models import Cookie
from services.facebook_steps import (
    fb_home,
    photo_upload,
    get_params,
    posting_post,
    posting_comment,
    feedback_start_typing,
)
from utils.helpers import get_headers


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

        client = await fb_home(cookies_dict)

        try:
            # 1. Subir imagen (Si aplica)
            upload_result = await FacebookService._upload_image_if_needed(
                client, image_base64
            )

            # Si hubo error al subir imagen, retornamos error inmediatamente
            if isinstance(upload_result, dict) and upload_result["status_code"] != 200:
                return upload_result

            photo_id = upload_result

            # 2. Publicar Post (Texto o Texto+Imagen)
            feedback_id = await posting_post(client, photo_id, title)
            if feedback_id is None:
                return {
                    "status_code": 400,
                    "mensaje": "Error al publicar el post",
                }

            # 3. Publicar Comentario (Si aplica)
            comment_result = await FacebookService._publish_comment_if_needed(
                client, feedback_id, comment
            )

            # Si publicamos comentario, retornamos ese resultado final
            # Si no hubo comentario, retornamos éxito del post base
            if comment_result:
                return comment_result

            return {
                "status_code": 200,
                "mensaje": "Post publicado exitosamente (sin comentario)",
                "data": {"feedback_id": feedback_id},
            }

        finally:
            await client.aclose()

    @staticmethod
    async def _upload_image_if_needed(
        client: httpx.AsyncClient, image_base64: str
    ) -> Optional[str] | Dict[str, Any]:
        """
        Retorna:
        - None: Si no hay imagen para subir.
        - photo_id (str): Si sube exitosamente.
        - dict: Si ocurre un error.
        """
        if not image_base64:
            return None

        resultado_upload = await photo_upload(client, image_base64)
        if resultado_upload["status_code"] != 200:
            return resultado_upload

        return resultado_upload["photo_id"]

    @staticmethod
    async def _publish_comment_if_needed(
        client: httpx.AsyncClient, feedback_id: str, comment: str
    ):
        """
        Retorna:
        - None: Si no hay comentario.
        - dict: Resultado de la publicación del comentario.
        """
        if not comment:
            return None

        await client.get("https://www.facebook.com/")

        # Restaurado: Llamada explícita a feedback_start_typing
        await feedback_start_typing(client, feedback_id)

        final = await posting_comment(client, feedback_id, comment)

        # Lógica de reintento
        if final["status_code"] != 200:
            await feedback_start_typing(client, feedback_id)
            final = await posting_comment(client, feedback_id, comment)

        return final

    @staticmethod
    async def get_pages(cookies: List[Cookie]):
        cookies_dict = {c.name: c.value for c in cookies}

        session = await FacebookService.get_session(cookies)

        if session["status_code"] != 200:
            return session

        async with httpx.AsyncClient(
            cookies=cookies_dict, headers=get_headers(), follow_redirects=True
        ) as client:
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

    @staticmethod
    async def get_session(cookies: List[Cookie]):
        cookies_dict = {c.name: c.value for c in cookies}
        try:
            async with httpx.AsyncClient(
                cookies=cookies_dict, headers=get_headers(), follow_redirects=True
            ) as client:
                response = await client.get("https://www.facebook.com/")
                html = response.text
                match_actor = re.search(r'"actorId":"(.*?)"', html)
                match_name = re.search(r'"USER_ID":".*?","NAME":"(.*?)"', html)

                if match_actor and match_name:
                    active = match_actor.group(1)
                    userName = match_name.group(1)
                    return {
                        "status_code": 200,
                        "mensaje": "Sesión activa",
                        "c_user": active,
                        "name": userName,
                    }
                else:
                    return {
                        "status_code": 400,
                        "mensaje": "No se encontró actorId o name en el HTML",
                        "resultado": "Sesión caducada o no valida",
                        "c_user": None,
                        "name": None,
                    }
        except Exception as e:
            print(traceback.format_exc())
            return {
                "status_code": 500,
                "mensaje": f"Error en get_session: {str(e)}",
                "c_user": None,
                "name": None,
            }
