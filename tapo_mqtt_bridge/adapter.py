import requests
import hashlib
from datetime import datetime, timedelta
import time
import paho.mqtt.client as mqtt
import json
import os
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import yaml

currentToken = ""
hass_options = json.load(open('/data/options.json'))
getCensoredToken = lambda token: (len(token) - 4) * "*" + token[len(token)-4:]
log = lambda value: os.system(f'echo \'{datetime.now().strftime("%m/%d/%Y, %H:%M:%S")} | {str(value).replace(currentToken, getCensoredToken(currentToken))}\'') if hass_options["logging"] else lambda:None 

log(yaml.safe_load(open('/config/configuration.yaml')))

mqtt_response = requests.get("http://supervisor/services/mqtt", headers={
    "Authorization": "Bearer " + os.environ.get('SUPERVISOR_TOKEN')
}).json()["data"]

mqtt_username = mqtt_response["username"]
mqtt_password = mqtt_response["password"]
url = "https://" + hass_options["ip"] + ":443"
headers = {
    "Host": hass_options["ip"],
    "Referer": url,
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate",
    "User-Agent": "Tapo CameraClient Android",
    "Connection": "close",
    "requestByApp": "true",
    "Content-Type": "application/json; charset=UTF-8",
}


def refresh_token():
    global headers
    global url
    global currentToken
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    data = {
        "method": "login",
        "params": {
            "hashed": "true",
            "password": hashlib.md5(hass_options["password"].encode('ascii')).hexdigest().upper(),
            "username": hass_options["username"]
        }
    }
    res = requests.post(url, json=data, headers=headers, verify=False)
    if res.status_code == 200:
        currentToken = res.json()["result"]["stok"]

    
    log(f'Refresh Token => Status code: { str(res.status_code) }, response text: { res.text }' )
    

# def privacy_get():
#    global headers
#    global currentToken
#    global url
#    return requests.post(
#        url + "/stok=" + currentToken + "/ds",
#        json='{"method": "get", "lens_mask": {"name": ["lens_mask_info"]}}',
#        headers=headers,
#        verify=False
#    )#["lens_mask"]["lens_mask_info"]


def privacy_set(status):
    global headers
    global url
    global currentToken
    return requests.post(
        url + "/stok=" + currentToken + "/ds",
        json={"method": "set", "lens_mask": {
            "lens_mask_info": {"enabled": status}}},
        headers=headers,
        verify=False
    )


def move(direction, steps):
    global headers
    global url
    global currentToken
    requests.post(
        url + "/stok=" + currentToken + "/ds",
        json={
            "method": "do", "motor": {
                "move": {
                    "x_coord": "-" + steps if direction == "left" else steps if direction == "right" else "0",
                    "y_coord": "-" + steps if direction == "down" else steps if direction == "up" else "0"
                }
            }
        },
        headers=headers,
        verify=False
    )

def publish(client, topic, payload):
    log(f'MQTT Publish => Topic: { topic }, Payload: { payload }')
    client.publish(topic, payload)

def on_message(client, userdata, message):
    payload = str(message.payload.decode("utf-8")).lower()
    log(f'MQTT Message => Incoming => topic: { message.topic }, payload: { payload }')

    # Privacy
    if message.topic == hass_options["mqtt_client_id"] + "/privacy/set" and (payload == "on" or payload == "off"):
        if privacy_set(payload).json()["error_code"] == 0:
            publish(client, f'{ hass_options["mqtt_client_id"] }/privacy', payload.upper())
    
    # Move
    valid_topics = [f"{hass_options['mqtt_client_id']}/move/{direction}" for direction in ["right", "left", "up", "down"]]
    if message.topic in valid_topics:
        move(message.topic.split("/")[-1], payload)

def subscribe(client, topic):
    log(f'MQTT Subscribing => Topic: { topic }')
    client.subscribe(topic)

def on_connect(client, userdata, flags, rc):
    subscribe(client, f'{ hass_options["mqtt_client_id"] }/move/right')
    subscribe(client, f'{ hass_options["mqtt_client_id"] }/move/left')
    subscribe(client, f'{ hass_options["mqtt_client_id"] }/move/up')
    subscribe(client, f'{ hass_options["mqtt_client_id"] }/move/down')
    subscribe(client, f'{ hass_options["mqtt_client_id"] }/privacy/set')


client = mqtt.Client(client_id=hass_options["mqtt_client_id"])
client.username_pw_set(username=mqtt_username, password=mqtt_password)
client.on_message = on_message
client.on_connect = on_connect
client.connect(mqtt_response["host"], mqtt_response["port"], 60)

token_every_minutes = hass_options["refresh_token_polling_interval_minutes"]
timer = datetime.now() + timedelta(minutes=token_every_minutes)

client.loop_start()
while True:
    if (datetime.now() - timer).seconds >= token_every_minutes*60:
        try:
            refresh_token()
            timer = datetime.now()
        except:
            log("ERROR => Seems like the tapo-cam ist not reachable!")
    time.sleep(1)
