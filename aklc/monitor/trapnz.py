# Lets import the things we need
import django
import sys
import json
import datetime
import time
import os
from django.utils import timezone
from django import template
from django.conf import settings

import paho.mqtt.client as mqtt

import requests
from requests_oauthlib import OAuth2Session

# need this to access django models and templates
sys.path.append("/code/aklc")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aklc.settings")
django.setup()

from monitor.models import (
    Node,
    Profile,
    NodeUser,
    Team,
    NodeGateway,
    Config,
    notificationLog,
    webNotification,
)
from django.contrib.auth.models import User

# all config parameters are set as environment variables, best practice in docker environment
eMqtt_client_id = os.getenv("AKLC_MQTT_CLIENT_ID", "mqtt_trapnz")
eMqtt_host      = os.getenv("AKLC_MQTT_HOST", "mqtt")
eMqtt_port      = os.getenv("AKLC_MQTT_PORT", "1883")
eMqtt_user      = os.getenv("AKLC_MQTT_USER", "aklciot")
eMqtt_password  = os.getenv("AKLC_MQTT_PASSWORD", "iotiscool")
eMqtt_prefix    = os.getenv("AKLC_MQTT_PREFIX", "")

eTrapNZ_access_URL      = os.getenv("AKLC_TRAPNZ_ACCESS_URL", "https://io.trap.nz/api-sensor/oauth/token")
eTrapNZ_sensor_URL      = os.getenv("AKLC_TRAPNZ_SENSOR_URL", "https://io.trap.nz/api-sensor/iot/sensor-record")
eTrapNZ_user            = os.getenv("AKLC_TRAPNZ_USER", "")
eTrapNZ_password        = os.getenv("AKLC_TRAPNZ_PASSWORD", "")
eTrapNZ_client_id       = os.getenv("AKLC_TRAPNZ_CLIENT_ID", "")
eTrapNZ_client_secret   = os.getenv("AKLC_TRAPNZ_CLIENT_SECRET", "")

testFlag = os.getenv("AKLC_TESTING", False)

if testFlag:
    scriptID = "DJ_Mon_TrapNZ-TEST"
else:
    scriptID = "DJ_Mon_TrapNZ"

access_token = ""
refresh_token = ""

#client_id = "cb7c2987-f6e6-4d1f-bc22-ee971e244405"
#client_secret = "frogman-rollback-replica"
#username = "jimboeri"
#password = "changeme"

#trapnz_access_url = "https://io.trap.nz/api-sensor/oauth/token"
#if web:
#    trapnz_record_url = "https://io.trap.nz/api-sensor/iot/sensor-record?_format=json"
#else:
#    trapnz_record_url = "https://noderedtest.west.net.nz/trapnz/python?_format=json"

print(f"Starting Trap NZ script")

"""
print("Set up API call")
print("-------------------")

hdr = {
    "Authorization": f"Bearer {access_token}",
    "Cache-Control": "no-cache",
    "Content-Type": "application/hal+json",
    "accept": "application/hal+json",
}

nodeID = "JW-Trap01"

sData = {"dev_id": nodeID}
sData["metadata"] = {"time": datetime.datetime.now().isoformat()}

sPayload = {"type": "sensor_report"}
sPayload["field_event"] = [{"value": "Sprung"}]
sPayload["field_status"] = [{"value": "Set"}]
sPayload["field_network"] = [{"value": "Iwinet"}]
sPayload["field_gateway"] = [{"value": "JW02"}]
sPayload["field_sequence"] = [{"value": 1}]
sPayload["field_counter"] = [{"value": 2}]
sPayload["field_battery_voltage"] = [{"value": 3.141}]

sData["payload_fields"] = sPayload

#print(f"sData to Json string: {json.dumps(sData)}")

#dResp = requests.post(trapnz_record_url, headers=hdr, data=json.dumps(sData))

print(f"Request URL: {trapnz_record_url}")
print(" ")
#print(f"Return reason: {dResp.reason}")
print(" ")
#print(f"Return status code: {dResp.status_code}")
print(" ")
print(f"Data: {json.dumps(sData)}")
print(" ")

while True:
    time.sleep(1)
    x = input("Typr something and press enter")
    print(f"Input received: {x}")
    if x =="x":
        exit()
    
    refresh_payload = {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    }
    refresh_headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }

    print("Refreshing access code")
    print("-------------------")

    rRefreshToken = requests.post(trapnz_access_url, data=refresh_payload, headers=refresh_headers)

    print(f"Status code of access code refresh request: {rRefreshToken.status_code}")

    jResp = rRefreshToken.json()
    newAccess_token = jResp["access_token"]
    print(jResp)
    

    print(f"Try old code")
    dResp = requests.post(trapnz_record_url, headers=hdr, data=json.dumps(sData))
    print(f"Status code of old access code request: {dResp.status_code}")


    hdr = {
        "Authorization": f"Bearer {newAccess_token}",
        "Cache-Control": "no-cache",
        "Content-Type": "application/hal+json",
        "accept": "application/hal+json",
    }
    
    print("Try new code")
    dResp = requests.post(trapnz_record_url, headers=hdr, data=json.dumps(sData))
    print(f"Status code of new access code request: {dResp.status_code}")
"""

# ********************************************************************
def testPr(tStr):
    if testFlag:
        print(tStr)
    return

# ********************************************************************
def is_json(myjson):
    """
    Function to check if an input is a valid JSON message
    """
    try:
        json_object = json.loads(myjson)
    except ValueError as e:
        return False
    return True


# ********************************************************************
def mqtt_on_connect(client, userdata, flags, rc):
    """
      This procedure is called on connection to the mqtt broker
    """
    global scriptID, dProj
    print(f"Connected to mqtt with result code {str(rc)}")
    sub_topic = f"{eMqtt_prefix}EnvironmentalServices/#"
    client.subscribe(sub_topic)
    print(f"MQTT Subscribed to {sub_topic}")
    client.publish(
        f"{eMqtt_prefix}AKLC/monitor/{scriptID}/LWT", payload="Running", qos=0, retain=True
    )
    print("Sent connection message")


# ********************************************************************
def mqtt_on_message(client, userdata, msg):
    """This procedure is called each time a mqtt message is received"""
    global access_token

    #testPr(f"MQTT message received {msg.topic} : {msg.payload}")
    
    if not is_json(msg.payload):
        print("Input message is not valid JSON, topic: {msg.topic}, payload: {msg.payload}")
        return
    
    try:
        sPayload = msg.payload.decode()
    except Exception as e:
        print(
            f"Houston, we had an error {e} decoding the payload. Topic was {msg.topic}, payload was {msg.payload}"
        )
        return
    jPayload = json.loads(sPayload)

    if "NodeID" in jPayload:
        # Lets try and fine the node
        try:
            node = Node.objects.get(nodeID = jPayload["NodeID"])
        except:
            return
        
        if not node.trapNZ:
            return

        print(f"Processing node {node.nodeID}")

        # Some data validation
        if "State" not in jPayload:
            print('Payload has no "State" value')
            return

        if len(jPayload["State"]) > 1:
            print('Value of "State" is {jPayload["State"]}, only expecting single character in State')
            return

        if not ("O" in jPayload["State"] or "C" in jPayload["State"]):
            print(f'Value of "State" is {jPayload["State"]}, must be "C" or "O"')
            return

        if "Event" not in jPayload:
            print('Payload has no "Event" value')
            return

        if len(jPayload["Event"]) > 1:
            print('Value of "Event" is {jPayload["Event"]}, only expecting single character in Event')
            return
            
        if not ("H" in jPayload["Event"] or "T" in jPayload["Event"]):
            print(f'Value of "Event" is {jPayload["Event"]}, must be "T" or "H"')
            return

        print("Set up API call")
        print("-------------------")

        hdr = {
            "Authorization": f"Bearer {access_token}",
            "Cache-Control": "no-cache",
            "Content-Type": "application/hal+json",
            "accept": "application/hal+json",
        }

        sData = {"dev_id": node.nodeID}
        sData["metadata"] = {"time": datetime.datetime.now().isoformat()}

        sPayload = {"type": "sensor_report"}
        if jPayload["Event"] == "H":
            sPayload["field_event"] = [{"value": "Heartbeat"}]
        else:
            if jPayload["State"] == "O":
                sPayload["field_event"] = [{"value": "Set"}]
            else:
                sPayload["field_event"] = [{"value": "Sprung"}]

        if jPayload["State"] == "O":
            sPayload["field_status"] = [{"value": "Set"}]
        else:
            sPayload["field_status"] = [{"value": "Sprung"}]
        sPayload["field_network"] = [{"value": "Iwinet"}]
        if "Gateway" in jPayload:
            sPayload["field_gateway"] = [{"value": jPayload["Gateway"]}]
        if "VBat" in jPayload:
            sPayload["field_battery_voltage"] = [{"value": jPayload["VBat"]}]

        sPayload["field_timeout"] = [{"value": 7200}]

        sData["payload_fields"] = sPayload

        #print(f"sData to Json string: {json.dumps(sData)}")

        dResp = requests.post(eTrapNZ_sensor_URL, headers=hdr, data=json.dumps(sData))

        print(f"Request URL: {eTrapNZ_sensor_URL}")
        print(" ")
        print(f"Return reason: {dResp.reason}")
        print(" ")
        print(f"Return status code: {dResp.status_code}")
        print(" ")
        print(f"Data: {json.dumps(sData)}")
        print(" ")




# ******************************************************************
def trap_nz():
    """ 
    The program that updates the TRAP.NZ API with updates from MQTT
    """

    global scriptID, access_token, refresh_token

    print(" ")
    print(" ")
    print("---------------------------------")
    print("Start function - TRAP.NZ")
    print("---------------------------------")

    gConfig, created = Config.objects.get_or_create(id=1)

    payload = {
        "grant_type": "password",
        "client_id": eTrapNZ_client_id,
        "client_secret": eTrapNZ_client_secret,
        "username": eTrapNZ_user,
        "password": eTrapNZ_password,
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Cache-Control": "no-cache",
    }

    print("Getting initial access code")
    print("-------------------")

    rToken = requests.post(eTrapNZ_access_URL, data=payload, headers=headers)

    print(f"Status code of access code request: {rToken.status_code}")

    jResp = rToken.json()

    access_token = jResp["access_token"]
    refresh_token = jResp["refresh_token"]
    expires_in = jResp["expires_in"]
    print(f"Access token expires in {expires_in} seconds")

    refreshTime = timezone.now() + datetime.timedelta(seconds = (expires_in - 60))
    #refreshTime = timezone.now() + datetime.timedelta(seconds = 60)

    print(f"Initial refresh time: {refreshTime}")

    #print(jResp)
    #with open("access_token", "w") as f:
    #    f.write(access_token)
    #f.close()

    # The mqtt client is initialised
    print(f"Connect to MQTT queue {eMqtt_host}")

    client = mqtt.Client()

    # functions called by mqtt client
    client.on_connect = mqtt_on_connect
    client.on_message = mqtt_on_message

    client.will_set(
        f"AKLC/monitor/{scriptID}/LWT", payload="Failed", qos=0, retain=True
    )
    print("Set WILL message")

    try:
        # set up the MQTT environment
        client.username_pw_set(eMqtt_user, eMqtt_password)
        client.connect(eMqtt_host, int(eMqtt_port), 30)
    except Exception as e:
        print(f"MQTT connection error: {e}")

    client.loop_start()

    print("MQTT env set up done")

    # initialise the checkpoint timer
    checkTimer = timezone.now()

    while True:
        time.sleep(1)

        if timezone.now() > refreshTime:
                refresh_payload = {
                    "grant_type": "refresh_token",
                    "client_id": eTrapNZ_client_id,
                    "client_secret": eTrapNZ_client_secret,
                    "refresh_token": refresh_token,
                }
                refresh_headers = {
                    "Content-Type": "application/x-www-form-urlencoded",
                }

                print("Refreshing access code")
                print("-------------------")

                rRefreshToken = requests.post(eTrapNZ_access_URL, data=refresh_payload, headers=refresh_headers)

                print(f"Status code of access code refresh request: {rRefreshToken.status_code}")

                if rRefreshToken.status_code < 399:
                    jResp = rRefreshToken.json()
                    access_token = jResp["access_token"]
                    refresh_token = jResp["refresh_token"]
                    expires_in = jResp["expires_in"]
                    
                    refreshTime = timezone.now() + datetime.timedelta(seconds = (expires_in - 60))
                    #refreshTime = timezone.now() + datetime.timedelta(seconds = 60)
                else:
                    print(f"Refresh FAILIURE")
                    print(f"Headers: {refresh_headers}")
                    print(f"Data: {refresh_payload}")
                    refreshTime = timezone.now() + datetime.timedelta(seconds = 60)
                    break







# ********************************************************************
if __name__ == "__main__":
    trap_nz()
