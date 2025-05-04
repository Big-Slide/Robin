import requests
from dbutils.schemas import WebhookStatus
from dbutils import crud
from config.config_handler import config
from loguru import logger
import json
from sqlalchemy.orm import Session


base_url = f"{config['AIHIVE_ADDR']}/api/Request"


def set_inprogress(request_id: str) -> bool:
    url = base_url + f"/{request_id}"
    headers = {"Accept": "*/*"}
    params = {"status": WebhookStatus.in_progress.value, "output": "{}"}
    response = requests.put(url, params=params, headers=headers)
    # response.raise_for_status()
    if response.status_code == 200:
        logger.info(
            "Webhook-set_inprogress",
            status_code=response.status_code,
        )
        return True
    else:
        logger.warning(
            "Webhook-set_inprogress",
            status_code=response.status_code,
            content=response.content,
        )
        return False


def set_completed(db: Session, request_id: str, data: dict) -> bool:
    url = base_url + f"/{request_id}"
    result = {"result": data}
    headers = {"Accept": "*/*"}
    params = {"status": WebhookStatus.completed.value, "output": json.dumps(result)}
    response = requests.put(url, params=params, headers=headers)
    crud.set_webhook_result(
        db=db, request_id=request_id, webhook_status_code=response.status_code
    )
    # response.raise_for_status()
    if response.status_code == 200:
        logger.debug(
            "Webhook-set_completed",
            status_code=response.status_code,
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
    headers = {"Accept": "*/*"}
    params = {"status": WebhookStatus.failed.value, "output": "{}"}
    response = requests.put(url, params=params, headers=headers)
    crud.set_webhook_result(
        db=db, request_id=request_id, webhook_status_code=response.status_code
    )
    # response.raise_for_status()
    if response.status_code == 200:
        logger.debug("Webhook-set_failed", status_code=response.status_code)
        return True
    else:
        logger.warning(
            "Webhook-set_failed",
            status_code=response.status_code,
            content=response.content,
        )
        return False
