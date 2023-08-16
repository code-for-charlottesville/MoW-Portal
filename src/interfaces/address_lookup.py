import json
import logging
import urllib

import requests

import config.config as CONFIG
from meals.constants import MOW_LAT, MOW_LON

log = logging.getLogger(__name__)


def validate(addr):
    address = addr
    base = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json?"
    apikey = CONFIG.SERVER_GOOGLE_API_KEY
    packet = {
        "input": address,
        "inputtype": "textquery",
        "key": apikey,
        "fields": "geometry",
    }
    encoded = urllib.parse.urlencode(packet)
    to_send = base + encoded
    api_request = requests.get(to_send)
    response = json.loads(api_request.text)
    if response["status"] != "OK":
        if "error_message" in response:
            log.error(f"Error Message {response['error_message']}")
        log.error(f"Google address error on {address}")
        return {"lat": MOW_LAT, "lng": MOW_LON}
    log.info(f"Address lookup success on {address}")
    return response["candidates"][0]["geometry"]["location"]
