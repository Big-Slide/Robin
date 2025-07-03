import requests
from dbutils.schemas import WebhookStatus
from config.config_handler import config
from loguru import logger
from sqlalchemy.orm import Session
from dbutils import crud


base_url = f"{config['AIHIVE_ADDR']}/api/Request"


def __generate_url(request_id: str) -> str:
    # TODO: read link from db
    link = f"{config['BASE_URL_FILE_LINK']}/aihive-txttosp/api/v1/file/{request_id}"
    return link


def get_file(db: Session, request_id: str):
    task = crud.get_request(db=db, request_id=request_id)
    if not task:
        return None
    if task.status == WebhookStatus.completed and task.result is not None:
        return open(task.result, "rb")


def set_inprogress(db: Session, request_id: str) -> bool:
    url = base_url + f"/{request_id}"
    params = {"status": WebhookStatus.in_progress.value, "output": "{}"}
    headers = {"Accept": "*/*"}
    response = requests.put(url, params=params, headers=headers)
    crud.set_webhook_result(
        db=db,
        request_id=request_id,
        webhook_status_code=response.status_code,
        increase_retry=False,
    )
    # response.raise_for_status()
    if response.status_code == 200:
        logger.debug(
            "Webhook-set_inprogress",
            status_code=response.status_code,
            # content=response.content,
        )
        return True
    else:
        logger.warning(
            "Webhook-set_inprogress",
            status_code=response.status_code,
            content=response.content,
        )
        return False


def set_completed(db: Session, request_id: str) -> bool:
    url = base_url + f"/{request_id}"
    params = {"status": WebhookStatus.completed.value, "output": "{}"}
    headers = {"Accept": "*/*"}
    response = requests.put(
        url,
        params=params,
        headers=headers,
        files={"outputFile": get_file(db, request_id)},
    )
    crud.set_webhook_result(
        db=db, request_id=request_id, webhook_status_code=response.status_code
    )
    # response.raise_for_status()
    if response.status_code == 200:
        logger.debug(
            "Webhook-set_completed",
            status_code=response.status_code,
            # content=response.content,
        )
        return True
    else:
        logger.warning(
            "Webhook-set_completed",
            status_code=response.status_code,
            content=response.content,
        )
        return False


def set_failed(db: Session, request_id: str) -> bool:
    url = base_url + f"/{request_id}"
    params = {"status": WebhookStatus.failed.value, "output": "{}"}
    headers = {"Accept": "*/*"}
    response = requests.put(url, params=params, headers=headers)
    crud.set_webhook_result(
        db=db, request_id=request_id, webhook_status_code=response.status_code
    )
    # response.raise_for_status()
    if response.status_code == 200:
        logger.debug(
            "Webhook-set_failed",
            status_code=response.status_code,
            # content=response.content,
        )
        return True
    else:
        logger.warning(
            "Webhook-set_failed",
            status_code=response.status_code,
            content=response.content,
        )
        return False
