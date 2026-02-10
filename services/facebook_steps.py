import httpx
import time
import base64
import re
from utils.helpers import get_params, base64_to_bytes, generar_session_id, get_headers
import json


async def fb_home(cookies: dict):
    client = httpx.AsyncClient(
        cookies=cookies,
        headers=get_headers(),
        follow_redirects=True,
    )  # Sin 'async with'
    await client.get("https://www.facebook.com/")
    return client

####
async def photo_upload(client: httpx.AsyncClient, base64_data: str):
    data = await get_params(client)
    binary = await base64_to_bytes(base64_data)
    # Equivalente a FormData en JS
    form_data = {
        "source": (None, "8"),
        "profile_id": (None, data["av"]),
        "waterfallxapp": (None, "comet"),
        "farr": ("imagen.jpeg", binary, "image/jpeg"),
        "upload_id": (None, "jsc_c_8"),
    }

    params = {
        "av": data["av"],
        "__user": data["av"],
        "__a": "1",
        "fb_dtsg": data["fb_dtsg"],
        "lsd": data["lsd"],
        "__spin_r": data["__spin_r"],
        "__spin_b": "trunk",
        "__spin_t": data["__spin_t"],
    }

    response = await client.post(
        "https://upload.facebook.com/ajax/react_composer/attachments/photo/upload",
        params=params,
        files=form_data,
    )

    text = response.text
    match = re.search(r'"photoID":"(.*?)"', text)
    if match:
        photo_id = match.group(1)
        return {"status_code": 200, "photo_id": photo_id, "client": client}
    else:
        return {
            "status_code": 400,
            "mensaje": "No se encontró photoID. Respuesta:",
            "respuesta": text,
        }

####
async def posting_post(client: httpx.AsyncClient, photo_id: str, title: str):
    data = await get_params(client)
    session_id = generar_session_id()
    timestamp = int(time.time() * 1000)
    attachments = []
    if photo_id:
        attachments = [{"photo": {"id": photo_id}}]

    # Preparar el payload para la publicacion
    variables = {
        "input": {
            "composer_entry_point": "inline_composer",
            "composer_source_surface": "timeline",
            "idempotence_token": f"{session_id}_FEED",
            "source": "WWW",
            "attachments": attachments,
            "audience": {
                "privacy": {
                    "allow": [],
                    "base_state": "EVERYONE",
                    "deny": [],
                    "tag_expansion_state": "UNSPECIFIED",
                }
            },
            "message": {"ranges": [], "text": {json.dumps(title)}},
            "with_tags_ids": None,
            "inline_activities": [],
            "text_format_preset_id": "0",
            "publishing_flow": {
                "supported_flows": ["ASYNC_SILENT", "ASYNC_NOTIF", "FALLBACK"]
            },
            "logging": {"composer_session_id": session_id},
            "navigation_data": {
                "attribution_id_v2": "ProfileCometTimelineListViewRoot.react,comet.profile.timeline.list,via_cold_start,{ts},532559,{ts},,".format(
                    ts=timestamp
                )
            },
            "tracking": [None],
            "event_share_metadata": {"surface": "timeline"},
            "actor_id": str(data["av"]),
            "client_mutation_id": "2",
        },
        "feedLocation": "TIMELINE",
        "feedbackSource": 0,
        "focusCommentID": None,
        "gridMediaWidth": 230,
        "groupID": None,
        "scale": 1,
        "privacySelectorRenderLocation": "COMET_STREAM",
        "checkPhotosToReelsUpsellEligibility": True,
        "renderLocation": "timeline",
        "useDefaultActor": False,
        "inviteShortLinkKey": None,
        "isFeed": False,
        "isFundraiser": False,
        "isFunFactPost": False,
        "isGroup": False,
        "isEvent": False,
        "isTimeline": True,
        "isSocialLearning": False,
        "isPageNewsFeed": False,
        "isProfileReviews": False,
        "isWorkSharedDraft": False,
        "hashtag": None,
        "canUserManageOffers": False,
        "__relay_internal__pv__CometUFIShareActionMigrationrelayprovider": True,
        "__relay_internal__pv__GHLShouldChangeSponsoredDataFieldNamerelayprovider": True,
        "__relay_internal__pv__GHLShouldChangeAdIdFieldNamerelayprovider": True,
        "__relay_internal__pv__CometUFI_dedicated_comment_routable_dialog_gkrelayprovider": False,
        "__relay_internal__pv__IsWorkUserrelayprovider": False,
        "__relay_internal__pv__CometUFIReactionsEnableShortNamerelayprovider": False,
        "__relay_internal__pv__FBReels_deprecate_short_form_video_context_gkrelayprovider": True,
        "__relay_internal__pv__CometFeedStoryDynamicResolutionPhotoAttachmentRenderer_experimentWidthrelayprovider": 500,
        "__relay_internal__pv__CometImmersivePhotoCanUserDisable3DMotionrelayprovider": False,
        "__relay_internal__pv__WorkCometIsEmployeeGKProviderrelayprovider": False,
        "__relay_internal__pv__IsMergQAPollsrelayprovider": False,
        "__relay_internal__pv__FBReelsMediaFooter_comet_enable_reels_ads_gkrelayprovider": False,
        "__relay_internal__pv__StoriesArmadilloReplyEnabledrelayprovider": False,
        "__relay_internal__pv__FBReelsIFUTileContent_reelsIFUPlayOnHoverrelayprovider": False,
        "__relay_internal__pv__GHLShouldChangeSponsoredAuctionDistanceFieldNamerelayprovider": False,
    }

    payload = {
        "av": data["av"],
        "fb_dtsg": data["fb_dtsg"],
        "lsd": data["lsd"],
        "__spin_r": data["__spin_r"],
        "__spin_b": "trunk",
        "__spin_t": data["__spin_t"],
        "__crn": "comet.fbweb.CometProfileTimelineListViewRoute",
        "fb_api_caller_class": "RelayModern",
        "fb_api_req_friendly_name": "CometUFILiveTypingBroadcastMutation_StartMutation",
        # Nota: aqui habia un error en el copy-paste original del usuario si esto fuera feedback_typing,
        # pero posting_post esta bien.
        # Aseguremonos de que posting_post esta limpio.
        "variables": json.dumps(variables, ensure_ascii=False),
        "server_timestamps": "true",
        "doc_id": "9908905722506681",
    }

    response = await client.post("https://www.facebook.com/api/graphql/", data=payload)
    if "story_create" in response.text and "post_id" in response.text:
        response = response.json()
        post_id = response["data"]["story_create"]["post_id"]
        feedback = "feedback:" + post_id
        feedback_id = base64.b64encode(feedback.encode("utf-8")).decode("utf-8")
        return feedback_id
    else:
        print(
            "[publish] posting_post: error status={status} body_snip={snip}".format(
                status=response.status_code, snip=response.text[:500]
            )
        )
        return None
####
async def feedback_start_typing(client: httpx.AsyncClient, feedback_id: str):
    data = await get_params(client)
    session_id = generar_session_id()
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
        "__comet_req": data["__comet_req"],
        "fb_dtsg": data["fb_dtsg"],
        "jazoest": data["jazoest"],
        "lsd": data["lsd"],
        "__spin_r": data["__spin_r"],
        "__spin_b": "trunk",
        "__spin_t": data["__spin_t"],
        "__crn": "comet.fbweb.CometProfileTimelineListViewRoute",
        "fb_api_caller_class": "RelayModern",
        "fb_api_req_friendly_name": "CometUFILiveTypingBroadcastMutation_StartMutation",
        "variables": f'{{"input":{{"feedback_id":"{feedback_id}","session_id":"{session_id}","actor_id":"{data["av"]}","client_mutation_id":"1"}}}}',
        "server_timestamps": "true",
        "doc_id": "9432643450167108",
    }

    await client.post("https://www.facebook.com/api/graphql/", data=payload)

####
async def posting_comment(client: httpx.AsyncClient, feedback_id: str, comment: str):
    post_id = base64.b64decode(feedback_id).decode("utf-8").replace("feedback:", "")
    data = await get_params(client)
    session_id = generar_session_id()
    timestamp = int(time.time() * 1000)
    # Procesamos el texto que viene de JSON.stringify()
    ##try:
    ##    # Primero intentamos decodificar el JSON
    ##    comment = json.loads(comment)
    ##    # Si el texto tiene escapes, los removemos
    ##    if isinstance(comment, str):
    ##        comment = comment.encode("utf-8").decode("unicode_escape")
    ##except:
    ##    # Si falla el JSON, asumimos que es texto plano
    ##    pass

    #comment = comment.replace("\n", "\\n")
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
        "__comet_req": data["__comet_req"],
        "fb_dtsg": data["fb_dtsg"],
        "jazoest": data["jazoest"],
        "lsd": data["lsd"],
        "__spin_r": data["__spin_r"],
        "__spin_b": "trunk",
        "__spin_t": data["__spin_t"],
        "__crn": "comet.fbweb.CometProfileTimelineListViewRoute",
        "fb_api_caller_class": "RelayModern",
        "fb_api_req_friendly_name": "useCometUFICreateCommentMutation",
        "variables": f"""{{"feedLocation":"TIMELINE","feedbackSource":0,"groupID":null,"input":{{"client_mutation_id":"1","actor_id":"{data['av']}","attachments":null,"feedback_id":"{feedback_id}","formatting_style":null,"message":{{"ranges":[],"text":{json.dumps(comment)}}},"attribution_id_v2":"ProfileCometTimelineListViewRoot.react,comet.profile.timeline.list,via_cold_start,{timestamp},850307,190055527696468,,","vod_video_timestamp":null,"is_tracking_encrypted":true,"tracking":["{data['tracking_hash']}","{{\\"assistant_caller\\":\\"comet_above_composer\\",\\"conversation_guide_session_id\\":null,\\"conversation_guide_shown\\":null}}"],"feedback_source":"PROFILE","idempotence_token":"client:{session_id}","session_id":"{session_id}"}},"inviteShortLinkKey":null,"renderLocation":null,"scale":1,"useDefaultActor":false,"focusCommentID":null,"__relay_internal__pv__IsWorkUserrelayprovider":false}}""",
        "server_timestamps": "true",
        "doc_id": "9978194542273556",
    }

    response = await client.post("https://www.facebook.com/api/graphql/", data=payload)

    if "feedback" in response.text and "associated_group" in response.text:
        return {
            "status_code": 200,
            "data": {"post_id": post_id},
            "mensaje": "Comentario publicado exitosamente.",
        }
    else:
        return {
            "status_code": 400,
            "mensaje": "Error al publicar el comentario. Respuesta:"+ response.text,
            "respuesta": response.text,
        }
