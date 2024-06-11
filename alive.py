from http.client import responses
from logging import (
    basicConfig,
    getLogger,
    INFO,
)
from os import environ
from requests import get
from time import sleep

basicConfig(
    format="{asctime} - [{levelname[0]}] {name} [{module}:{lineno}] - {message}",
    datefmt="%Y-%m-%d %H:%M:%S",
    style="{",
    level=INFO,
)

LOGGER = getLogger("Alive")

def sendRequest(url: str, header: dict) -> None:
    request = get(
        url=url,
        headers=header,
        timeout=10,
        allow_redirects=True,
    )

    if not request.ok:
        raise Exception(f"[{request.status_code}] - {responses[request.status_code]}")

try:
    HEADER = dict()
    BASE_URL = None
    
    if BASE_URL := environ.get("BASE_URL"):
        if "hf.sp" in BASE_URL:
            if HF_TOKEN := environ.get("HF_TOKEN"):
                HEADER["Authorization"] = f"Bearer {HF_TOKEN}"

        HEADER["User-Agent"] = "Not a RoBot"

        while True:
            sendRequest(
                url=BASE_URL,
                header=HEADER,
            )
            sleep(300)

except Exception as error:
    LOGGER.error(error)
