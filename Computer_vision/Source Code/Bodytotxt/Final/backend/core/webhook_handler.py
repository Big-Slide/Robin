import requests
import json
from dbutils.schemas import WebhookStatus
from config.config_handler import config
from loguru import logger


def __generate_url(request_id: str) -> str:
    # Generate the link to the processed image
    link = f"{config['BASE_URL_FILE_LINK']}/aihive-bodytotxt/api/v1/image/{request_id}"
    return link


def set_inprogress(request_id: str) -> bool:
    url = f"{config['AIHIVE_ADDR']}/api/Request/{request_id}"
    headers = {"Content-type": "application/json", "Accept": "application/json"}

    # Create the updateRequestDto structure
    update_request_dto = {
        "status": WebhookStatus.in_progress.value,
        "output": json.dumps(None)  # Convert to JSON string
    }

    # Create the final data structure
    data = {
        "updateRequestDto": update_request_dto
    }

    try:
        logger.info(f"Sending in-progress webhook to: {url}")
        logger.debug(f"Webhook data: {data}")

        response = requests.put(url, json=data, headers=headers, timeout=10)

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
                response=response.text if hasattr(response, 'text') else None,
            )
            return False
    except Exception as e:
        logger.error(f"Error in set_inprogress webhook: {e}")
        return False


def set_completed(request_id: str) -> bool:
    url = f"{config['AIHIVE_ADDR']}/api/Request/{request_id}"

    # Create the result as a dictionary
    result_dict = {"download_link": __generate_url(request_id)}

    # Convert result to JSON string
    result_json_string = json.dumps(result_dict)

    headers = {"Content-type": "application/json", "Accept": "*/*"}

    # Create the updateRequestDto structure
    update_request_dto = {
        "status": WebhookStatus.completed.value,
        "output": result_json_string  # Already a JSON string
    }

    # Create the final data structure
    data = {
        "updateRequestDto": update_request_dto
    }

    try:
        logger.info(f"Sending completed webhook to: {url}")
        logger.debug(f"Webhook data: {data}")

        response = requests.put(url, json=data, headers=headers, timeout=10)

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
                response=response.text if hasattr(response, 'text') else None,
            )
            return False
    except Exception as e:
        logger.error(f"Error in set_completed webhook: {e}")
        return False


def set_failed(request_id: str) -> bool:
    url = f"{config['AIHIVE_ADDR']}/api/Request/{request_id}"
    headers = {"Content-type": "application/json", "Accept": "application/json"}

    # Create the updateRequestDto structure
    update_request_dto = {
        "status": WebhookStatus.failed.value,
        "output": json.dumps(None)  # Convert to JSON string
    }

    # Create the final data structure
    data = {
        "updateRequestDto": update_request_dto
    }

    try:
        logger.info(f"Sending failed webhook to: {url}")
        logger.debug(f"Webhook data: {data}")

        response = requests.put(url, json=data, headers=headers, timeout=10)

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
                response=response.text if hasattr(response, 'text') else None,
            )
            return False
    except Exception as e:
        logger.error(f"Error in set_failed webhook: {e}")
        return False