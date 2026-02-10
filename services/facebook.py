import httpx
import json
import base64
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
    def _debug_text(label: str, text: Optional[str]) -> None:
        if text is None:
            print(f"[publish] {label}: None")
            return
        non_ascii = [f"U+{ord(c):04X}" for c in text if ord(c) > 127]
        non_ascii_preview = non_ascii[:20]
        more = "..." if len(non_ascii) > 20 else ""
        sample = text[:80]
        print(
            f"[publish] {label}: len={len(text)} non_ascii={non_ascii_preview}{more} sample={sample!r}"
        )

    @staticmethod
    async def post_publish(
        id: str, cookies: List[Cookie], title: str, comment: str, image_base64: str
    ):
        print(
            f"[publish] start: id={id!r} cookies={len(cookies)} has_image={bool(image_base64)}"
        )
        FacebookService._debug_text("title", title)
        #FacebookService._debug_text("comment", comment)

        cookies_dict = {c.name: c.value for c in cookies}
        cookies_dict["i_user"] = id  # ← Agregas manualmente esta cookie
        #
        print("[publish] get_session: start")
        session = await FacebookService.get_session(cookies)
        print(
            "[publish] get_session: status_code={status} mensaje={mensaje} c_user={c_user}".format(
                status=session.get("status_code"),
                mensaje=session.get("mensaje"),
                c_user=session.get("c_user"),
            )
        )

        if session["status_code"] != 200:
            print("[publish] get_session: not ok, returning")
            return session

        print("[publish] fb_home: start")
        client = await fb_home(cookies_dict)
        print("[publish] fb_home: ok")

        try:
            # 1. Subir imagen (Si aplica)
            print("[publish] upload_image: start")
            upload_result = await FacebookService._upload_image_if_needed(
                client, image_base64
            )
            if isinstance(upload_result, dict):
                print(
                    "[publish] upload_image: status_code={status} mensaje={mensaje}".format(
                        status=upload_result.get("status_code"),
                        mensaje=upload_result.get("mensaje"),
                    )
                )
            else:
                print(f"[publish] upload_image: result={upload_result!r}")

            # Si hubo error al subir imagen, retornamos error inmediatamente
            if isinstance(upload_result, dict) and upload_result["status_code"] != 200:
                print("[publish] upload_image: not ok, returning")
                return upload_result

            photo_id = upload_result

            # 2. Publicar Post (Texto o Texto+Imagen)
            print("[publish] posting_post: start")
            feedback_id = await posting_post(client, photo_id, title)
            print(f"[publish] posting_post: feedback_id={feedback_id!r}")
            if feedback_id is None:
                print("[publish] posting_post: failed (feedback_id None)")
                return {
                    "status_code": 400,
                    "mensaje": "Error al publicar el post",
                }

            # 3. Publicar Comentario (Si aplica)
            print("[publish] comment: start")
            comment_result = await FacebookService._publish_comment_if_needed(
                client, feedback_id, comment
            )

            # Si publicamos comentario, retornamos ese resultado final
            # Si no hubo comentario, retornamos éxito del post base
            if comment_result:
                print("[publish] comment: result returned")
                return comment_result

            post_id = base64.b64decode(feedback_id).decode("utf-8").replace("feedback:", "")
            print("[publish] comment: skipped or empty")
            return {
                "status_code": 200,
                "mensaje": "Post publicado exitosamente (sin comentario)",
                "data": {"post_id": post_id},
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
            print("[publish] upload_image: no image provided")
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
            print("[publish] comment: empty, skip")
            return None

        print(f"[publish] comment: feedback_id={feedback_id!r}")
        #FacebookService._debug_text("comment", comment)
        warmup = await client.get("https://www.facebook.com/")
        print(f"[publish] comment: warmup status={warmup.status_code}")

        # Restaurado: Llamada explícita a feedback_start_typing
        print("[publish] comment: feedback_start_typing (1)")
        await feedback_start_typing(client, feedback_id)

        print("[publish] comment: posting_comment (1)")
        final = await posting_comment(client, feedback_id, comment)
        print(
            "[publish] comment: result (1) status_code={status} mensaje={mensaje}".format(
                status=final.get("status_code"),
                mensaje=final.get("mensaje"),
            )
        )

        # Lógica de reintento
        if final["status_code"] != 200:
            print("[publish] comment: retry feedback_start_typing (2)")
            await feedback_start_typing(client, feedback_id)
            print("[publish] comment: posting_comment (2)")
            final = await posting_comment(client, feedback_id, comment)
            print(
                "[publish] comment: result (2) status_code={status} mensaje={mensaje}".format(
                    status=final.get("status_code"),
                    mensaje=final.get("mensaje"),
                )
            )

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
