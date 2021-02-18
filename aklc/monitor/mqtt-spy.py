import django
import sys
import os
from django.conf import settings
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish

import json
import datetime
import time

import inspect

from django.utils import timezone

# need this to access django models and templates
sys.path.append("/code/aklc")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aklc.settings")
django.setup()

from monitor.models import (
    Node,
    Team,
    MqttQueue,
    MqttMessage,
    MqttStore,
)
from django.contrib.auth.models import User

eTesting = os.getenv("AKLC_TESTING", "N")
if eTesting == "Y":
    testFlag = True
    scriptID = "DJ_Mon_Spy-TEST"
else:
    scriptID = "DJ_Mon_Spy"
    testFlag = False

eLogging = os.getenv("AKLC_LOGGING", "N")
if eLogging == "Y":
    logFlag = True
else:
    logFlag = False

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
def testPr(tStr):
    if testFlag:
        print(tStr)
    return


# ********************************************************************
"""
This function is called when the MQTT client connects to the MQTT broker
"""


def mqtt_on_connect(client, userdata, flags, rc):
    """
      This procedure is called on connection to the mqtt broker
    """
    global scriptID
    userdata["nConnCnt"] = userdata["nConnCnt"] + 1
    print(
        f"Connected to {userdata['dbRec'].descr} with result code {rc}, connection count is {userdata['nConnCnt']}"
    )
    sub_topic = "AKLC/#"
    client.subscribe(sub_topic)
    print("mqtt Subscribed to " + sub_topic)
    client.publish(
        f"AKLC/monitor/{scriptID}/LWT", payload="Running", qos=0, retain=True
    )
    print("Sent connection message")

    # Teams are 1st level TOPICs, used to separate data for various communities
    # We subscribe to all defined teams
    aTeams = Team.objects.all()
    for t in aTeams:
        sub_topic = t.teamID + "/#"
        print("MQTT Subscribed to {}".format(sub_topic))
        client.subscribe(sub_topic)
    return


# ********************************************************************
def mqtt_on_disconnect(client, userdata, rc):
    """
      This procedure is called on when a disconnection is noted
      Attempt to reconnect
    """
    print(
        f"Disconnected to {userdata['dbRec'].descr} with result code {rc}, attempt to reconnect"
    )
    res = client.reconnect()
    print(f"Reconnect result was {res}")
    userdata["nConnCnt"] = userdata["nConnCnt"] + 1
    client.publish(
        f"AKLC/monitor/{scriptID}/LWT", payload="Running", qos=0, retain=True
    )
    return


# ********************************************************************
"""
This function is called when an mqtt message is received
"""


def mqtt_on_message(client, userdata, msg):
    """
      This procedure is called when a msg is recieved
    """
    print(
        f"Msg recived on {userdata['dbRec'].descr}, topic {msg.topic}, payload {msg.payload}"
    )

    cTopic = msg.topic.split("/")
    sPayload = msg.payload.decode()
    # print(f"Topic: {msg.topic}")
    # print(f"Payload: {msg.payload}")
    # print(f"QoS: {msg.qos}")
    # print(f"Retained: {msg.retain}")

    if logFlag:
        m = MqttStore(
            mqttQueue=userdata["dbRec"],
            topic=msg.topic,
            payload=sPayload,
            qos=msg.qos,
            retained=msg.retain,
        )
        m.save()
        # print("Mqtt message saved")

    # first have to find a node id
    cNode = ""

    if sPayload == "":  # empty payload
        print("Empty payload received")
        return

    if cTopic[0] == "AKLC":
        # print(f"AKLC msg received, next is {cTopic[1]}, payload is {sPayload}")
        if cTopic[1] == "Status":  # Status messages from Gateways, data in CSV format
            try:
                cPayload = sPayload.split(",")
                cNode = cPayload[0]
                # print(f"Status - Node is {cNode}")
            except Exception as e:
                print(e)
                print(f"Houston, we have an error {e}")

        elif (
            cTopic[1] == "Gateway"
        ):  # Data message passed on by gateway, data in CSV format
            cPayload = sPayload.split(",")
            if len(cPayload) < 1:  # empty payload
                return
            if "Test" in cPayload[1]:
                # print(f"Test message received, topic is {msg.topic}, payload is {sPayload}, msg not processed")
                return
            cNode = cPayload[1]

        elif cTopic[1] == "Node" or cTopic[1] == "Network":
            if is_json(sPayload):  # these messages should always be JSON
                jStr = json.loads(sPayload)
                # lets find the node name
                if len(cTopic) > 2:
                    cNode = cTopic[2]
                elif "Gateway" in jStr:
                    cNode = jStr["Gateway"]
                elif "nodeID" in jStr:
                    cNode = jStr["NodeID"]
                elif "NodeID" in jStr:
                    cNode = jStr["NodeID"]

    else:  # must be a team message
        jPayload = json.loads(sPayload)
        if "NodeID" in jPayload:
            cNode = jPayload["NodeID"]

    # Lets get the node record
    try:
        node = Node.objects.get(nodeID=cNode)
        # testPr(f"Node found {node.nodeID}")
    except:
        return

    try:
        # print(f"node is {node.nodeID}, mqttQueue is {userdata.descr}")
        mqttMsg, created = MqttMessage.objects.get_or_create(
            node=node, mqttQueue=userdata["dbRec"]
        )
        if created:
            print(f"New record created")
        mqttMsg.topic = msg.topic
        mqttMsg.payload = sPayload
        mqttMsg.received = timezone.make_aware(
            datetime.datetime.now(), timezone.get_current_timezone()
        )
        # print(f"Time received is {timezone.make_aware(datetime.datetime.now(), timezone.get_current_timezone())}")
        mqttMsg.save()

    except Exception as e:
        print(e)
        print(f"Houston, we have an mqtt storing error {e}")
    return


# ******************************************************************
def mqtt_spy():
    """ The main program that sends updates to the MQTT system
    """
    global scriptID
    print(" ")
    print(" ")
    print("Start MQTT spy")
    print(" ")
    print(" ")

    aMqtt = MqttQueue.objects.all()
    cMqtt = []
    # lConnCnt = {}  # Dict to hold connection count data

    if not logFlag:
        print("NOT caputing MQTT messages, delete all those that currently exist")
        MqttStore.objects.all().delete()
    else:
        print("Capture all MQTT messages")

    for m in aMqtt:
        print(f"Set up mqtt queue {m.descr}")
        uData = {"dbRec": m, "nConnCnt": 0}
        cMqtt.append(mqtt.Client(userdata=uData))
        cMqtt[-1].on_connect = mqtt_on_connect
        cMqtt[-1].on_message = mqtt_on_message
        cMqtt[-1].will_set(
            f"AKLC/monitor/{scriptID}/LWT", payload="Failed", qos=0, retain=True
        )
        print("Set WILL message")
        print(f"User is {m.user}, pw is {m.pw}")
        if m.user:
            print("User present")
            cMqtt[-1].username_pw_set(m.user, m.pw)

        try:
            print(f"Connect to {m.host} on port {m.port}")
            cMqtt[-1].connect(m.host, m.port, keepalive=60)

            print("Client connect requested")
            cMqtt[-1].loop_start()

        except Exception as e:
            print(e)
            print(f"Houston, we have an mqtt connection error {e}")
            # cMqtt.pop()     # remove this from the list

        # time.sleep(5)

    checkDt = datetime.date(2020, 1, 1)
    startTime = timezone.make_aware(
        datetime.datetime.now(), timezone.get_current_timezone()
    )

    # initialise the checkpoint timer
    checkTimer = timezone.now()

    while True:

        if datetime.date.today() != checkDt:
            print("Clean old mqtt messages from database")
            aMqttMsgAll = MqttMessage.objects.all()
            refDt = timezone.make_aware(
                datetime.datetime.now(), timezone.get_current_timezone()
            )
            cutOff = datetime.timedelta(days=30)
            for msg in aMqttMsgAll:
                tDiff = refDt - msg.received
                # print(f"Msg time dif is {tDiff}")
                if tDiff > cutOff:
                    print(f"Delete mqtt record reference {msg}")
                    msg.delete()
            checkDt = datetime.date.today()

        # regular MQTT connection status updates
        if (timezone.now() - checkTimer) > datetime.timedelta(minutes=5):
            checkTimer = timezone.now()  # reset timer
            upTime = (
                timezone.make_aware(
                    datetime.datetime.now(), timezone.get_current_timezone()
                )
                - startTime
            )
            for c in cMqtt:
                payLoad = {
                    "scriptName": scriptID,
                    "connectionCount": c._userdata["nConnCnt"],
                    "QueueName": c._userdata["dbRec"].descr,
                    "upTime(s)": upTime.total_seconds(),
                }
                print(
                    f"Regular reporting payload is {payLoad}, send to {c._userdata['dbRec'].descr}"
                )

                res = c.publish(
                    f"AKLC/monitor/{scriptID}/status",
                    payload=json.dumps(payLoad),
                    qos=0,
                    retain=False,
                )
                print(f"Queue name: {c._userdata['dbRec'].descr}, Result code {res.rc}")
                if res.rc == mqtt.MQTT_ERR_NO_CONN:  # no connection
                    try:
                        print(f"Dicconnect & reconnect to {c._userdata['dbRec'].descr}")
                        c.disconnect()
                        c.username_pw_set(
                            c._userdata["dbRec"].user, c._userdata["dbRec"].pw
                        )
                        c.will_set(
                            f"AKLC/monitor/{scriptID}/LWT",
                            payload="Failed",
                            qos=0,
                            retain=True,
                        )
                        c.connect(
                            host=c._userdata["dbRec"].host,
                            port=c._userdata["dbRec"].port,
                            keepalive=60,
                        )
                    except Exception as e:
                        print(e)
                        print(f"Houston, we have an mqtt re-connection error {e}")

        time.sleep(1)

    print("Finished")


# ********************************************************************
if __name__ == "__main__":
    mqtt_spy()

