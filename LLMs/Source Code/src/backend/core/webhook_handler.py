import requests
from dbutils.schemas import WebhookStatus
from dbutils import crud
from config.config_handler import config
from loguru import logger
import json
from sqlalchemy.orm import Session
import io


base_url = f"{config['AIHIVE_ADDR']}/api/Request"


def get_file(db: Session, request_id: str):
    task = crud.get_request(db=db, request_id=request_id)
    if not task:
        return None
    if task.status == WebhookStatus.completed and task.result_path is not None:
        return open(task.result_path, "rb")


def get_file_by_path(filepath: str):
    return open(filepath, "rb")


def set_inprogress(db: Session, request_id: str) -> bool:
    url = base_url + f"/{request_id}"
    headers = {"Accept": "*/*"}
    params = {"status": WebhookStatus.in_progress.value, "output": "{}"}
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
        )
        return True
    else:
        logger.warning(
            "Webhook-set_inprogress",
            status_code=response.status_code,
            content=response.content,
        )
        return False


def set_completed(
    db: Session, request_id: str, result_data: str = None, max_param_size: int = 1000
) -> bool:
    url = base_url + f"/{request_id}"
    headers = {"Accept": "*/*"}
    if result_data:
        # TODO: use max_param_size (check with Dr. Fathi)
        # Always send as file when result_data is provided
        result_json = json.dumps({"result": result_data})
        file_obj = io.BytesIO(result_json.encode("utf-8"))
        params = {"status": WebhookStatus.completed.value, "output": "{}"}
        files = {"outputFile": ("result.txt", file_obj, "text/plain")}
        response = requests.put(url, params=params, headers=headers, files=files)
    else:
        params = {"status": WebhookStatus.completed.value, "output": "{}"}
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
