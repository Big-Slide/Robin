import requests
from dbutils.schemas import WebhookStatus
from config.config_handler import config
from loguru import logger


base_url = f"{config['AIHIVE_ADDR']}/api/Request"


def set_inprogress(request_id: str) -> bool:
    url = base_url + f"/{request_id}"
    headers = {"Content-type": "application/json", "Accept": "application/json"}
    data = {"status": WebhookStatus.in_progress.value, "output": None}
    response = requests.put(url, data=data, headers=headers)
    # response.raise_for_status()
    if response.status_code == 200:
        logger.info(
            "Webhook-set_inprogress",
            status_code=response.status_code,
            response=response.json(),
        )
        return True
    else:
        logger.warning(
            "Webhook-set_inprogress",
            status_code=response.status_code,
            response=response.json(),
        )
        return False


def set_completed(request_id: str, text: str) -> bool:
    url = base_url + f"/{request_id}"
    result = {"text": text}
    headers = {"Content-type": "application/json", "Accept": "*/*"}
    data = {"status": WebhookStatus.completed.value, "output": result}
    response = requests.put(url, json=data, headers=headers)
    # response.raise_for_status()
    if response.status_code == 200:
        logger.info(
            "Webhook-set_completed",
            status_code=response.status_code,
            response=response.json(),
        )
        return True
    else:
        logger.warning(
            "Webhook-set_completed",
            status_code=response.status_code,
            response=response.json(),
        )
        return False


def set_failed(request_id: str) -> bool:
    url = base_url + f"/{request_id}"
    headers = {"Content-type": "application/json", "Accept": "application/json"}
    data = {"status": WebhookStatus.failed.value, "output": None}
    response = requests.put(url, data=data, headers=headers)
    # response.raise_for_status()
    if response.status_code == 200:
        logger.info(
            "Webhook-set_failed",
            status_code=response.status_code,
            response=response.json(),
        )
        return True
    else:
        logger.warning(
            "Webhook-set_failed",
            status_code=response.status_code,
            response=response.json(),
        )
        return False
