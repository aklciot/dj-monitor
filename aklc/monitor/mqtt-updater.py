import django
import sys
import os
from django.conf import settings
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish

from influxdb import InfluxDBClient

import json
import datetime
import time
import pickle
from django.utils import timezone
from django import template
from email.mime.text import MIMEText

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
    MessageType,
    MessageItem,
    NodeMsgStats,
    Config,
)
from django.contrib.auth.models import User

# all config parameters are set as environment variables, best practice in docker environment
eMqtt_client_id = os.getenv("AKLC_MQTT_CLIENT_ID", "mqtt_monitor_updater-1")
eMqtt_host = os.getenv("AKLC_MQTT_HOST", "mqtt")
eMqtt_port = os.getenv("AKLC_MQTT_PORT", "1883")
eMqtt_user = os.getenv("AKLC_MQTT_USER", "aklciot")
eMqtt_password = os.getenv("AKLC_MQTT_PASSWORD", "iotiscool")

eTB_host = os.getenv("AKLC_TB_HOST", "thingsboard.innovateauckland.nz")
eTB_port = os.getenv("AKLC_TB_PORT", 8080)
eTB_topic = "v1/devices/me/telemetry"

eInflux_host = os.getenv("AKLC_INFLUX_HOST", "172.20.0.2")
eInflux_port = os.getenv("AKLC_INFLUX_PORT", 8086)
eInflux_user = os.getenv("AKLC_INFLUX_USER", "aklciot")
eInflux_pw = os.getenv("AKLC_INFLUX_PW", "password")
eInflux_db = os.getenv("AKLC_INFLUX_DB", "aklc")

eMqtt_prefix = os.getenv("AKLC_MQTT_PREFIX", "")
eTesting = os.getenv("AKLC_TESTING", "N")
if eTesting == "Y":
    testFlag = True
    scriptID = "DJ_Mon_Updater-TEST"
else:
    testFlag = False
    scriptID = "DJ_Mon_Updater"
connectionCount = 1
msgCount = 0
msgUpdates = 0

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
    global scriptID, connectionCount
    print("Connected to mqtt with result code " + str(rc))
    sub_topic = "AKLC/#"
    client.subscribe(sub_topic)
    print("mqtt Subscribed to " + sub_topic)

    client.publish(
        f"AKLC/monitor/{scriptID}/LWT", payload="Running", qos=0, retain=True
    )

    print(f"Sent connection message for {scriptID}")

    # Teams are 1st level TOPICs, used to separate data for various communities
    # We subscribe to all devined teams
    aTeams = Team.objects.all()
    for t in aTeams:
        sub_topic = t.teamID + "/#"
        print("MQTT Subscribed to {}".format(sub_topic))
        client.subscribe(sub_topic)


# ********************************************************************
def mqtt_on_disconnect(client, userdata, rc):
    """
      This procedure is called on connection to the mqtt broker
    """
    global connectionCount
    print(f"MQTT has disconnected, the code was {rc}, attempting to reconnect")
    res = client.reconnect()
    connectionCount = connectionCount + 1
    print(f"Reconnect result was {res}, connection count is now {connectionCount}")
    client.publish(
        f"AKLC/monitor/{scriptID}/LWT", payload="Running", qos=0, retain=True
    )
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
def thingsboardUpload(node, msg):
    testPr(f"Thingsboard upload for {node.nodeID}")
    if node.thingsboardUpload:
        sPayload = msg.payload.decode()

        if is_json(sPayload):  # payload is JSON
            jStr = json.loads(sPayload)
        else:
            if node.messagetype:
                jOut = csv_to_json(sPayload, node)
                jStr = jOut["jStr"]
            else:
                return

        if node.locationOverride:
            jStr["latitude"] = node.latitude
            jStr["longitude"] = node.longitude

        try:
            sPayload = json.dumps(jStr)
            tbRes = publish.single(
                topic=eTB_topic,
                payload=sPayload,
                hostname=eTB_host,
                port=eTB_port,
                auth={"username": node.thingsboardCred},
            )
            # print(f"Publish to TB from function, payload is {sPayload}, response is {tbRes}")
        except ValueError as e:
            testPr(f"Thingsboard load error: {e}, node is {node.nodeID}")
        return


# ********************************************************************
def dictDel(inDict, inKey):
    # testPr(f"in dict is {inDict}, in key is {inKey}")
    if inKey in inDict:
        inDict.pop(inKey)
    return inDict


# ********************************************************************
def influxUpload(node, influxClient, msg, measurement, aTags, aData):
    """
    A function to load data to Influx
    """

    # if node.influxUpload:  # check if we should do this
    sPayload = msg.payload.decode()

    # The following attempts to only store valid data in influx
    aData = dictDel(aData, "EOM")
    aData = dictDel(aData, "End")

    if "RSSI" in aData:
        if not (type(aData["RSSI"]) is int or type(aData["RSSI"]) is float):
            aData = dictDel(aData, "RSSI")

    if "RP-RSSI" in aData:
        if not (type(aData["RP-RSSI"]) is int or type(aData["RP-RSSI"]) is float):
            aData = dictDel(aData, "RP-RSSI")

    if "Latitude" in aData:
        aData["latitude"] = aData["Latitude"]
        aData = dictDel(aData, "Latitude")

    if "lat" in aData:
        aData["latitude"] = aData["lat"]
        aData = dictDel(aData, "lat")

    if "Lat" in aData:
        aData["latitude"] = aData["Lat"]
        aData = dictDel(aData, "Lat")

    if "latitude" in aData:
        if type(aData["latitude"]) is not float:
            aData = dictDel(aData, "latitude")

    if "Longitude" in aData:
        aData["longitude"] = aData["Longitude"]
        aData = dictDel(aData, "Longitude")

    if "lon" in aData:
        aData["longitude"] = aData["lon"]
        aData = dictDel(aData, "lon")

    if "Lon" in aData:
        aData["longitude"] = aData["Lon"]
        aData = dictDel(aData, "Lon")

    if "longitude" in aData:
        if type(aData["longitude"]) is not float:
            aData = dictDel(aData, "longitude")

    if "Version" in aData:
        if type(aData["Version"]) is not str:
            aData["Version"] = str(aData["Version"])

    aTags["upload_src"] = "PyUpdater"

    json_body = [{"measurement": measurement, "tags": aTags, "fields": aData,}]
    # print(f"Influx json from function {json_body}")
    try:
        influxClient.write_points(json_body)
        testPr(f"Store {json_body} in Influx")
    except Exception as e:
        print(f"Influx load error: {e}, json_body is {json_body}")

    return


# ********************************************************************
def mqtt_on_message(client, userdata, msg):
    """This procedure is called each time a mqtt message is received

    | AKLC | Gateway | Data message passed on by gateway, data in CSV format
    | AKLC | Status  | Status messages from Gateways, data in CSV format
    | AKLC | Network | Data & status messages from Gateways, data in JSON format
    | AKLC | Node    | Data & Status direct from a Node, data in JSON format

    """
    global msgCount, msgUpdates

    # print("mqtt message received {} : {}".format(msg.topic, msg.payload))
    # separate the topic up so we can work with it
    cTopic = msg.topic.split("/")
    if eMqtt_prefix:
        if cTopic[0] in eMqtt_prefix:
            del cTopic[0]
            #print(f"Removed prefix, cTopic is now {cTopic}")

    cDict = {}

    msgCount = msgCount + 1
    dbUpdate = False

    # get the payload as a string
    try:
        sPayload = msg.payload.decode()
    except Exception as e:
        print(
            f"Houston, we had an error {e} decoding the payload. Topic was {msg.topic}, payload was {msg.payload}"
        )
        return

    cPayload = sPayload.split(",")  # should the payload should be CSV

    # Check for nodes using regular topic structure
    if cTopic[0] == "AKLC":
        if len(cTopic) < 2:
            print(
                f"Bad topic in AKLC message, topic is {msg.topic}, payload is {sPayload}"
            )
            return

        # testPr(f"Aklc message received, topic {msg.topic}, payload { msg.payload.decode()}")
        # Check types of message from the topic

        if cTopic[1] == "Status":  # Status messages from Gateways, data in CSV format
            testPr(f"AKLC/Status message received, payload is {sPayload}")

            try:
                node = Node.objects.get(nodeID=cPayload[0])  # Lets
                # testPr(f"Gateway {node.nodeID} found")

                if node.messagetype:
                    jOut = csv_to_json(sPayload, node)
                    testPr(
                        f"Messagetype {node.messagetype.msgName} found, jOut is {jOut}"
                    )

                    if node.thingsboardUpload:
                        thingsboardUpload(node, msg)
                        dbUpdate = True

                    if node.influxUpload:
                        influxUpload(
                            node, InClient, msg, "Gateway", jOut["jTags"], jOut["jData"]
                        )
                        dbUpdate = True

                    lUpdate = False

                    if "Version" in jOut["jTags"]:
                        if node.software != jOut["jTags"]["Version"] and isinstance(
                            jOut["jTags"]["Version"], str
                        ):
                            node.software = jOut["jTags"]["Version"]
                            lUpdate = True

                    if "HWType" in jOut["jTags"]:
                        if node.hardware != jOut["jTags"]["HWType"] and isinstance(
                            jOut["jTags"]["HWType"], str
                        ):
                            node.hardware = jOut["jTags"]["HWType"]
                            lUpdate = True

                    if lUpdate:
                        testPr(
                            f"{node.nodeID} updated with HW/SW details HW {jOut['jTags']['HWType']}, SW {jOut['jTags']['Version']}"
                        )
                        node.save()

            except Exception as e:
                testPr(e)
                print("Cant find {} in database, error is {}".format(cPayload[1], e))

        elif (
            cTopic[1] == "Gateway"
        ):  # Data message passed on by gateway, data in CSV format
            testPr(f"AKLC/Gateway message received, payload is {sPayload}")

            if len(cPayload) < 2:
                print(
                    f"Bad payload in Gateway message, topic is {msg.topic}, payload is {sPayload}"
                )
                return

            if "Test" in cPayload[1]:
                # print(f"Test message received, topic is {msg.topic}, payload is {sPayload}, msg not processed")
                return

            try:
                node = Node.objects.get(nodeID=cPayload[1])  # Lets
                # print("Node {} found".format(node.nodeID))
            except Exception as e:
                testPr(e)
                print(
                    f"Cant find {cPayload[1]} in database, error is {e}, payload is {sPayload}, topic is {msg.topic}"
                )
                return

            if node.messagetype:
                jOut = csv_to_json(sPayload, node)
                testPr(
                    f"Message type found in Gateway message, node is {node.nodeID}, jOut is {jOut}"
                )

                if node.influxUpload:
                    if node.team:
                        cTeam = node.team.teamID
                    else:
                        cTeam = "unknown"
                    # json_body = [
                    #    {
                    #        "measurement": cTeam,
                    #        "tags": jOut["jTags"],
                    #        "fields": jOut["jData"],
                    #    }
                    # ]
                    # testPr(f"Influx JSON {json_body}")
                    # InClient.write_points(json_body)
                    influxUpload(
                        node, InClient, msg, cTeam, jOut["jTags"], jOut["jData"]
                    )
                    dbUpdate = True

                if node.thingsboardUpload:
                    thingsboardUpload(node, msg)
                    dbUpdate = True

        # elif cTopic[1] == "Network":      # These are status messages sent by gateways and nodes. Data in JSON format
        #  x =1
        elif (
            cTopic[1] == "Node" or cTopic[1] == "Network"
        ):  # These are JSON messages, both data & status
            testPr(
                f"NODE/NETWORK type message received, topic: { msg.topic}, payload: {sPayload}"
            )

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
                else:
                    testPr("No node info could be found, ignore message")
                    return

                try:
                    node = Node.objects.get(nodeID=cNode)

                    cMeasurement = cTopic[0]
                    if node.team:
                        cMeasurement = node.team.teamID

                    # print("Found node {}".format(cNode))
                    if node.thingsboardUpload:
                        thingsboardUpload(node, msg)
                        dbUpdate = True

                    if node.influxUpload:
                        # testPr("Publish to Influx")
                        jOut = json_for_influx(sPayload, node)
                        if node.team:
                            sMeasure = node.team.teamID
                        elif "project" in sPayload:
                            sMeasure = sPayload["project"]
                        else:
                            sMeasure = "AKLC"

                        influxUpload(
                            node,
                            InClient,
                            msg,
                            cMeasurement,
                            jOut["jTags"],
                            jOut["jData"],
                        )
                        dbUpdate = True

                except Exception as e:
                    testPr(e)
            else:
                testPr("Payload not JSON")

    else:  # not AKLC, a team subscription
        # the payload is expected to be json
        if not is_json(sPayload):
            print(f"Team message error, payload is not JSON")
        jPayload = json.loads(sPayload)
        testPr(f"Team message arrived, topic is {msg.topic}, payload is {sPayload}")

        if "NodeID" in jPayload:

            # if "PPC" in jPayload["NodeID"]:
            #    print("Yay - People counter")

            # print("The NodeID is {}".format(jPayload["NodeID"]))
            try:
                node = Node.objects.get(nodeID=jPayload["NodeID"])
                # print("Node retrieved")
                jOut = json_for_influx(sPayload, node)

                influxUpload(
                    node, InClient, msg, cTopic[0], jOut["jTags"], jOut["jData"]
                )
                dbUpdate = True

                if node.thingsboardUpload:
                    thingsboardUpload(node, msg)
                    dbUpdate = True

            except Exception as e:
                print(f"Team error {e}")

        else:
            print("No NodeID in this payload {}".format(sPayload))
    
    if dbUpdate:
        msgUpdates = msgUpdates + 1


# ******************************************************************
def json_for_influx(sPayload, nNode):
    """
  Function evaluates a jason input and splits it into tags & fields for influx upload
  """
    cTags = ["gateway", "nodeid", "location", "repeater", "project", "software", "type"]
    jTags = {}
    jData = {}

    jPayload = json.loads(sPayload)

    # print("json_for_influx entered, payload is {}".format(sPayload))

    for jD in list(jPayload):
        val = jPayload[jD]
        # convert all integers to float, better for Influx
        if type(val) is int:
            val = val * 1.0
        if jD.lower() in cTags:  # Then this must be a tag
            if type(val) is str:
                jTags[jD] = val
            else:
                testPr(
                    f"Tag value should be a string, {jD} has a value of {val} which is a {type(val)}"
                )
                # jTags[jD] = val
        else:
            jData[jD] = val

    # Location correction
    if nNode.locationOverride:
        if "latitude" in jData:
            jData["latitude"] = nNode.latitude
        elif "Latitude" in jData:
            jData["Latitude"] = nNode.latitude
        elif "longitude" in jData:
            jData["longitude"] = nNode.longitude
        elif "Longitude" in jData:
            jData["Longitude"] = nNode.longitude

    if nNode.projectOverride:
        if "project" in jData:
            jTags["project"] = nNode.topic
        if "Project" in jData:
            jTags["Project"] = nNode.topic

    jOutput = {"jTags": jTags, "jData": jData}
    # print("jTags is {}\njData is {}".format(jOutput['jTags'], jOutput['jData'] ))
    return jOutput


# ******************************************************************
def csv_to_json(payload, nNode):
    """
  Function converts a CSV payload to JSON for thingsboard & Influx based on data in the MesssageType record if it exists
  """

    jStr = {}
    jTags = {}
    jData = {}

    cPayload = payload.split(",")

    # here we try and remove any references to any repeaters
    lRepeater = True
    while lRepeater:
        lRepeater = False
        for itm in cPayload:
            if itm.startswith("RP"):
                # print(f"Remove {itm} from input")
                cPayload.remove(itm)
                lRepeater = True

    # print("csv_to_json entered, payload is {}".format(cPayload))
    for mItem in nNode.messagetype.items.all():
        # print("  msgItem is {}, value is {}".format(mItem.name, cPayload[mItem.order-1]))
        # some validation here

        if mItem.order > len(cPayload):
            # print(f"Message type mismatch, payload is {cPayload}, message type is {nNode.messagetype.msgName}, index is {mItem.order}")
            break

        try:
            if mItem.fieldType == "I":
                val = float(cPayload[mItem.order - 1])
            elif mItem.fieldType == "F":
                val = float(cPayload[mItem.order - 1])
            else:
                val = cPayload[mItem.order - 1]
            if nNode.locationOverride:
                if mItem.name == "latitude" or mItem.name == "Latitude":
                    val = nNode.latitude
                if mItem.name == "longitude" or mItem.name == "Longitude":
                    val = nNode.longitude
        except Exception as e:
            print(
                f"CSV to JSON error, cPayload is {cPayload}, message type is {nNode.messagetype.msgName}, error was {e}"
            )
            print(e)

        jStr[mItem.name] = val
        if mItem.isTag:
            jTags[mItem.name] = val
        else:
            jData[mItem.name] = val

    jOutput = {"jStr": jStr, "jTags": jTags, "jData": jData}
    # print("jStr is {}\njTags is {}\njData is {}".format(jOutput['jStr'], jOutput['jTags'], jOutput['jData'] ))
    return jOutput


# ******************************************************************
def mqtt_updater():
    """ The main program that sends updates from MQTT to Thingsboard & Influx
    """
    global InClient, scriptID, connectionCount, msgCount, msgUpdates

    print(" ")
    print(" ")
    print("------------------")
    print("Start Updater v1.5")
    print("------------------")

    gConfig, created = Config.objects.get_or_create(id=1)

    # InClient = InfluxDBClient(host='influxdb', port=8086, username='aklciot', password='iotiscool', database='aklc')
    InClient = InfluxDBClient(
        host=eInflux_host,
        port=eInflux_port,
        username=eInflux_user,
        password=eInflux_pw,
        database=eInflux_db,
    )
    print(
        f"Influx connection details - host: {eInflux_host}, port: {eInflux_port}, user: {eInflux_user}, password: {eInflux_pw}, database: {eInflux_db}"
    )
    aDb = InClient.get_list_database()
    # print(aDb)
    InClient.switch_database("aklc")

    # The mqtt client is initialised
    client = mqtt.Client()

    # functions called by mqtt client
    client.on_connect = mqtt_on_connect
    client.on_disconnect = mqtt_on_disconnect
    client.on_message = mqtt_on_message
    client.will_set(
        f"AKLC/monitor/{scriptID}/LWT", payload="Failed", qos=0, retain=True
    )
    print("Set WILL message")

    try:
        # set up the MQTT environment
        client.username_pw_set(eMqtt_user, eMqtt_password)
        client.connect(eMqtt_host, int(eMqtt_port), 60)
    except Exception as e:
        print(e)

    # used to manage mqtt subscriptions
    client.loop_start()

    print(f"MQTT env set up done - using host {eMqtt_host}")


    startTime = timezone.make_aware(
        datetime.datetime.now(), timezone.get_current_timezone()
    )
    checkTimer = timezone.now()

    while True:
        time.sleep(1)

        if (timezone.now() - checkTimer) > datetime.timedelta(minutes=gConfig.MqttStatusPeriod):
            checkTimer = timezone.now()  # reset timer
            upTime = (
                timezone.make_aware(
                    datetime.datetime.now(), timezone.get_current_timezone()
                )
                - startTime
            )
            payLoad = {
                "scriptName": scriptID,
                "connectionCount": connectionCount,
                "upTime(s)": upTime.total_seconds(),
                "msgCount": msgCount,
                "msgUpdates": msgUpdates,
            }
            print(f"Regular reporting payload is {payLoad}")
            client.publish(
                f"AKLC/monitor/{scriptID}/status",
                payload=json.dumps(payLoad),
                qos=0,
                retain=False,
            )
            gConfig.refresh_from_db()

        # check if we need to send stats
        tDate = timezone.now()

        # Check and send messages on the hour
        # if (stats_data["LastStats"].day == tDate.day) and (
        #    stats_data["LastStats"].hour == tDate.hour
        # ):
        if (gConfig.LastStats.day == tDate.day) and (
            gConfig.LastStats.hour == tDate.hour
        ):
            # print("No need to send updates")
            x = 1
        else:
            # client.reconnect()      # put this in as I am getting LWT messages while script is still running
            upTime = (
                timezone.make_aware(
                    datetime.datetime.now(), timezone.get_current_timezone()
                )
                - startTime
            )
            #status_json = {
            #    "scriptID": scriptID,
            #    "ConnectionCount": connectionCount,
            #    "upTime(s)": upTime.total_seconds(),
            #}
            #client.publish(
            #    f"AKLC/monitor/{scriptID}/status", payload=json.dumps(status_json)
            #)

            print(f"Time to send radio stats, pickle date is {gConfig.LastStats}, current date is {tDate}")
            tDate2 = timezone.make_aware(
                datetime.datetime.now() - datetime.timedelta(minutes=5),
                timezone.get_current_timezone(),
            )
            aStat = NodeMsgStats.objects.all().filter(dt=tDate2, hr=tDate2.hour)
            print("Date used to get data is {}".format(tDate2))
            # aStats = NodeMsgStats.objects.all().filter()
            radioTot = 0
            radioNodes = 0
            gatewayTot = 0
            radioGw = 0
            gConfig.refresh_from_db()
            # print("Number of stat nodes is {}".format(len(aStat)))
            for s in aStat:
                json_body = [
                    {
                        "measurement": "radio_stats",
                        "tags": {"nodeID": s.node.nodeID,},
                        "fields": {"radioCount": s.msgCount,},
                    }
                ]
                # print(json_body)
                InClient.write_points(json_body)
                if s.node.isGateway:
                    gatewayTot = gatewayTot + s.msgCount
                    radioGw = radioGw + 1
                else:
                    radioTot = radioTot + s.msgCount
                    radioNodes = radioNodes + 1

                try:
                    if s.node.thingsboardUpload:
                        print(
                            "Send radio stat message to Thingsboard for {}".format(
                                s.node.nodeID
                            )
                        )
                        jStr = {}  # create empty dict
                        jStr["radioCount"] = s.msgCount

                        print("Heres the JSON string {}".format(json.dumps(jStr)))

                        # mRes = publish.single(topic = eTB_topic, payload = json.dumps(jStr),
                        #      hostname = eTB_host, port = eTB_port,
                        #      auth = {'username':s.node.thingsboardCred})
                except Exception as e:
                    print(e)

            # Now send totals
            print("Send totals now")
            json_body = [
                {
                    "measurement": "radio_stats",
                    "tags": {"nodeID": "AllNodes",},
                    "fields": {
                        "radioCount": radioTot,
                        "radioNodes": radioNodes,
                        "gatewayCount": gatewayTot,
                        "radioGateways": radioGw,
                    },
                }
            ]
            # Write the totals

            InClient.write_points(json_body)
            print(json_body)

            gConfig.LastStats = tDate
            gConfig.save()

            # Save the time we sent to stats
            #stats_data["LastStats"] = tDate
            #try:
            #    statsPfile = open("stats.pkl", "wb")
            #    pickle.dump(stats_data, statsPfile)
            #    statsPfile.close()
            #    print("Write date {} to pickle file".format(tDate))
            #except Exception as e:
            #    print(e)
            #    print("Stats Pickle failed")


# ********************************************************************
if __name__ == "__main__":
    mqtt_updater()
