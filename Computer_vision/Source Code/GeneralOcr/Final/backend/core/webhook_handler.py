import requests
from dbutils.schemas import WebhookStatus
from config.config_handler import config
from loguru import logger
from sqlalchemy.orm import Session
from dbutils import crud
import json

base_url = f"{config['AIHIVE_ADDR']}/api/Request"


def __generate_url(request_id: str) -> str:
    link = f"{config['BASE_URL_FILE_LINK']}/api/v1/file/{request_id}"
    return link


def get_file(db: Session, request_id: str):
    task = crud.get_request(db=db, request_id=request_id)
    if not task:
        return None
    if task.status == WebhookStatus.completed and task.result is not None:
        return open(task.result, "rb")


def set_inprogress(request_id: str) -> bool:
    url = base_url + f"/{request_id}"
    params = {"status": WebhookStatus.in_progress.value, "output": "{}"}
    headers = {"Accept": "*/*"}
    response = requests.put(url, params=params, headers=headers)

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


def set_completed(db: Session, request_id: str) -> bool:
    logger.info(f"Setting request {request_id} as completed")
    url = base_url + f"/{request_id}"
    params = {"status": WebhookStatus.completed.value, "output": "{}"}
    headers = {"Accept": "*/*"}

    try:
        # Get task and result
        task = crud.get_request(db=db, request_id=request_id)
        if not task:
            logger.warning(f"No task found for request_id: {request_id}")
            return False

        # Check if we have result data
        if task.result is not None:
            # Create JSON output with OCR data
            output_data = {"result": task.result}
            output_json = json.dumps(output_data)

            # Update params with the JSON output
            params["output"] = output_json

            # Make request without files
            response = requests.put(url, params=params, headers=headers)
        else:
            # No result, just update status
            response = requests.put(url, params=params, headers=headers)
            logger.warning(
                "Webhook-set_completed",
                status_code=response.status_code,
                content=response.content,
            )
            return False
    except Exception as e:
        logger.error(f"Error in set_completed for {request_id}: {str(e)}")
        return False

    # Check response
    if response.status_code == 200:
        logger.info(
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


def set_failed(request_id: str) -> bool:
    url = base_url + f"/{request_id}"
    params = {"status": WebhookStatus.failed.value, "output": "{}"}
    headers = {"Accept": "*/*"}
    response = requests.put(url, params=params, headers=headers)

    if response.status_code == 200:
        logger.info(
            "Webhook-set_failed",
            status_code=response.status_code,
        )
        return True
    else:
        logger.warning(
            "Webhook-set_failed",
            status_code=response.status_code,
            content=response.content,
        )
        return False