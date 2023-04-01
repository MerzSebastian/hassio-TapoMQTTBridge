import requests
import hashlib
from datetime import datetime, timedelta
import time
import paho.mqtt.client as mqtt
import json
import os
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import sys
from ruamel.yaml import YAML, representer
from ruamel.yaml.compat import StringIO
representer.RoundTripRepresenter.ignore_aliases = lambda x, y: True

currentToken = ""
hass_options = json.load(open('/data/options.json'))
getCensoredToken = lambda token: (len(token) - 4) * "*" + token[len(token)-4:]
log = lambda value: os.system(f'echo \'{datetime.now().strftime("%m/%d/%Y, %H:%M:%S")} | {str(value).replace(currentToken, getCensoredToken(currentToken))}\'') if hass_options["logging"] else lambda:None 











def update_yaml_file(yaml_file_path, update_value):
    with open(yaml_file_path, "r") as yaml_file:
        yaml = YAML()
        data = yaml.load(yaml_file)
        
    # mqtt config
    if "mqtt" not in data.keys():
        data["mqtt"] = update_value["mqtt"]
    else:
        for key in update_value["mqtt"].keys():
            for i, button in enumerate(update_value["mqtt"][key]):
                if len([i for i in update_value["mqtt"][key] if i["unique_id"] == button["unique_id"]]) == 1:
                    if key not in data["mqtt"].keys():
                        data["mqtt"][key] = []
                    index_map = [i for i, s in enumerate(data["mqtt"][key]) if s["unique_id"] == button["unique_id"]]
                    if len(index_map) == 0:
                        data["mqtt"][key].append(button)
                    else:
                        data["mqtt"][key][index_map[0]] = button
    # camera config
    if "camera" not in data.keys():
        data["camera"] = update_value["camera"]
    else:
        for i, button in enumerate(update_value["camera"]):
            if len([i for i in update_value["camera"] if i["name"] == button["name"]]) == 1:
                index_map = [i for i, s in enumerate(data["camera"]) if s["name"] == button["name"]]
                if len(index_map) == 0:
                    data["camera"].append(button)
                else:
                    data["camera"][index_map[0]] = button

    # Write the updated data back to the YAML file
    with open(yaml_file_path, "w") as yaml_file:
        yaml.dump(data, yaml_file)


# Auto create tapo entities in configuration.yaml - if they are not existing, they will get created. If the are existing, they will get updated. mqtt entries get identified based on the unique_id and the camera based on the name
update_yaml_file('/config/configuration.yaml', {
    "mqtt": {
        "button": [
            { "unique_id": "tapo-cam_up", "name": "Tapo Cam - Move up", "command_topic": "tapo-cam/move/up", "payload_press": "10" },
            { "unique_id": "tapo-cam_down", "name": "Tapo Cam - Move down", "command_topic": "tapo-cam/move/down", "payload_press": "10" },
            { "unique_id": "tapo-cam_left", "name": "Tapo Cam - Move left", "command_topic": "tapo-cam/move/left", "payload_press": "10" },
            { "unique_id": "tapo-cam_right", "name": "Tapo Cam - Move right", "command_topic": "tapo-cam/move/right", "payload_press": "10" },
        ],
        "switch": [
            { "unique_id": "tapo-cam_privacy_switch", "name": "Tapo Cam - Privacy Switch", "state_topic": "tapo-cam/privacy", "command_topic": "tapo-cam/privacy/set", "payload_on": "ON", "payload_off": "OFF", "state_on": "ON", "state_off": "OFF" },
        ]
    },
    "camera": [{
        "platform": "ffmpeg",
        "name": "Tapo-C200",
        "input": f'-rtsp_transport tcp -i rtsp://{hass_options["username"]}:{hass_options["password"]}@{hass_options["ip"]}:554/stream1'
    }]
})
# Restart hass core (a bit shitty but works for now)
res = requests.POST("http://supervisor/core/restart", headers={
    "Authorization": "Bearer " + os.environ.get('SUPERVISOR_TOKEN')
})
log("RESTART CORE " + res.text)










#log(yaml.safe_load(open('/config/configuration.yaml')))

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
