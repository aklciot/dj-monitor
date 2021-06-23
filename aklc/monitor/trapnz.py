import requests
from requests_oauthlib import OAuth2Session

# from oauthlib.oauth2 import LegacyApplicationClient
import datetime
import json
import sys, getopt, time

getAccess = False
web = True
headerJSON = True
dataJSON = False

if len(sys.argv) > 1:
    opts, args = getopt.getopt(sys.argv[1:], "ath")
    for opt, arg in opts:
        if opt == "-h":
            print("Usage: python trapnz.py [ options ]")
            print("Options are:")
            print("-h - help")
            print("-a - generate new access token")
            print("-t - test, direct to nodered")
            sys.exit()
        if opt == "-a":
            getAccess = True
        elif opt == "-t":
            web = False

client_id = "cb7c2987-f6e6-4d1f-bc22-ee971e244405"
client_secret = "frogman-rollback-replica"
username = "jimboeri"
password = "changeme"

trapnz_access_url = "https://io.trap.nz/api-sensor/oauth/token"
if web:
    trapnz_record_url = "https://io.trap.nz/api-sensor/iot/sensor-record?_format=json"
else:
    trapnz_record_url = "https://noderedtest.west.net.nz/trapnz/python?_format=json"

print(f"Starting Trap NZ script")

if getAccess:

    payload = {
        "grant_type": "password",
        "client_id": client_id,
        "client_secret": client_secret,
        "username": username,
        "password": password,
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Cache-Control": "no-cache",
    }

    print("Getting access code")
    print("-------------------")

    rToken = requests.post(trapnz_access_url, data=payload, headers=headers)

    print(f"Status code of access code request: {rToken.status_code}")

    jResp = rToken.json()

    access_token = jResp["access_token"]
    refresh_token = jResp["refresh_token"]
    print(jResp)

    with open("access_token", "w") as f:
        f.write(access_token)
    f.close()
else:
    with open("access_token") as f:
        access_token = f.read()
    f.close

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
    