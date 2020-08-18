import django
import sys
import os
from django.conf import settings
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import json
import datetime
import time
import pickle
from django.utils import timezone
from django import template
from email.mime.text import MIMEText

# timezone.make_aware(yourdate, timezone.get_current_timezone())

# need this to access django models and templates
sys.path.append("/code/aklc")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aklc.settings")
django.setup()

from monitor.models import Node, Profile, NodeUser, Team, NodeGateway
from django.contrib.auth.models import User

# all config parameters are set as environment variables, best practice in docker environment
eMqtt_client_id = os.getenv("AKLC_MQTT_CLIENT_ID", "mqtt_monitor")
eMqtt_host = os.getenv("AKLC_MQTT_HOST", "mqtt")
eMqtt_port = os.getenv("AKLC_MQTT_PORT", "1883")
eMqtt_user = os.getenv("AKLC_MQTT_USER", "aklciot")
eMqtt_password = os.getenv("AKLC_MQTT_PASSWORD", "iotiscool")
eMail_From = os.getenv("AKLC_MAIL_FROM", "info@innovateauckland.nz")
eMail_To = os.getenv("AKLC_MAIL_TO", "westji@aklc.govt.nz")

eMail_topic = os.getenv("AKLC_MAIL_TOPIC", "AKLC/email/send")
sMs_topic = os.getenv("AKLC_SMS_TOPIC", "AKLC/sms/send")

eWeb_Base_URL = os.getenv("AKLC_WEB_BASE_URL", "http://aws2.innovateauckland.nz")

testRunDaily = os.getenv("AKLC_TEST_DAILY", "F")


# ********************************************************************
def mqtt_on_connect(client, userdata, flags, rc):
    """
      This procedure is called on connection to the mqtt broker
    """

    print(f"Connected to mqtt with result code {str(rc)}")
    sub_topic = "AKLC/#"
    client.subscribe(sub_topic)
    print(f"MQTT Subscribed to {sub_topic}")

    # Teams are 1st level TOPICs, used to separate data for various communities
    # We subscribe to all devined teams
    aTeams = Team.objects.all()
    for t in aTeams:
        sub_topic = t.teamID + "/#"
        print(sub_topic)
        client.subscribe(sub_topic)


# ********************************************************************
def mqtt_on_disconnect(client, userdata, rc):
    """
      This procedure is called on connection to the mqtt broker
    """
    print(f"MQTT has disconnected, the code was {rc}, attempting to reconnect")
    res = client.reconnect()
    print(f"Reconnect result was {res}")
    return


# ********************************************************************
def mqtt_on_message(client, userdata, msg):
    """This procedure is called each time a mqtt message is received"""

    # print("mqtt message received {} : {}".format(msg.topic, msg.payload))

    # separate the topic up so we can work with it
    cTopic = msg.topic.split("/")
    cDict = {}

    # get the payload as a string
    sPayload = msg.payload.decode()

    # Check for nodes using regular topic structure
    if cTopic[0] == "AKLC":
        # print("Aklc message received, topic {}, payload {}".format(msg.topic, msg.payload))
        # Check types of message from the topic
        # print("Subtopic = |{}|".format(cTopic[1]))
        if cTopic[1] == "Status":
            # These are status messages sent by gateways. Data in CSV format
            cPayload = sPayload.split(",")
            cNode = cPayload[0]
            print(f"Gateway status message received for {cNode}, payload is {cPayload}")
            # Check and update the gateway data
            if node_validate(cNode):
                #print(f"Make/get node {cNode}")
                gw, created = Node.objects.get_or_create(nodeID=cNode)
                #print(f"MG Success")
                if created:
                    print(f"Gateway {gw.nodeID} created")
                gw.msgReceived()
                gw.isGateway = True
                gw.lastStatus = sPayload
                gw.lastStatusTime = timezone.make_aware(
                    datetime.datetime.now(), timezone.get_current_timezone()
                )
                #print("Save")
                gw.incrementMsgCnt()
                gw.save()
                nJson = gw.make_json(sPayload)
                #print(f"Gateway JSON is {nJson}")
                if "Uptime" in nJson:
                    gw.bootTimeUpdate(nJson["Uptime"])
                if "Uptime(s)" in nJson:
                    gw.bootTimeUpdate(nJson["Uptime(s)"]/60)
                if "Uptime(m)" in nJson:
                    gw.bootTimeUpdate(nJson["Uptime(m)"])
                if "HWType" in jOut["jStr"]:
                    gw.hardware = jOut["jStr"]["HWType"]
                if "Version" in jOut["jStr"]:
                    gw.software = jOut["jStr"]["Version"]
                gw.save()
                #print(f"Gateway {gw.nodeID} saved")
            else:
                print(f"Gateway {cNode} not processed")

        elif cTopic[1] == "Gateway":
            # These are data messages from nodes sent on by a gateway, payload should be CSV
            # print("Gateway message received")
            cPayload = sPayload.split(",")  # the payload should be CSV

            print(
                "Gateway msg received, Node {}, Gateway {}".format(
                    cPayload[1], cPayload[0]
                )
            )
            if node_validate(cPayload[1]):  # check if the nodeID is valid
                # get the node, or create it if not found
                # print("Valid node {}".format(cPayload[1]))
                nd, created = Node.objects.get_or_create(nodeID=cPayload[1])
                nd.msgReceived()
                nd.lastData = sPayload
                nd.lastDataTime = timezone.make_aware(
                    datetime.datetime.now(), timezone.get_current_timezone()
                )
                nd.incrementMsgCnt()
                if "RP" in nd.nodeID:
                    nd.isRepeater = True
                else:
                    nd.isRepeater = False
                nJson = nd.make_json(sPayload)
                print(f"JSON is {nJson}")
                if "Uptime" in nJson:
                    nd.bootTimeUpdate(nJson["Uptime"])
                if "Uptime(s)" in nJson:
                    nd.bootTimeUpdate(nJson["Uptime(s)"]/60)
                if "Uptime(m)" in nJson:
                    nd.bootTimeUpdate(nJson["Uptime(m)"])
                nd.save()

            # Check and update the gateways info
            if node_validate(cPayload[0]):  # payload[0] is the gateway
                # print("Valid gateway {}".format(cPayload[0]))
                gw, created = Node.objects.get_or_create(nodeID=cPayload[0])
                gw.msgReceived()
                gw.isGateway = True
                gw.lastData = sPayload
                gw.lastDataTime = timezone.make_aware(
                    datetime.datetime.now(), timezone.get_current_timezone()
                )
                gw.incrementMsgCnt()
                gw.save()

            if node_validate(cPayload[1]) and node_validate(cPayload[0]):
                try:
                    lp = nd.passOnData()
                    ngAll = NodeGateway.objects.filter(nodeID_id=nd.id)
                    ngAll = ngAll.filter(gatewayID_id=gw.id)
                    if len(ngAll) == 1:
                        ng = ngAll[0]
                    else:
                        ng = NodeGateway(nodeID=nd, gatewayID=gw)
                    ng.lastdata = timezone.make_aware(
                        datetime.datetime.now(), timezone.get_current_timezone()
                    )
                    ng.save()

                except Exception as e:
                    print(e)
                    print(f"Houston, we have an error {e}")

        elif (
            cTopic[1] == "Network"
        ):  # These are status messages sent by gateways and nodes. Data in JSON format
            print(f"Network message received |{sPayload}|, topic |{msg.topic}|")
            # print("Topic length = {}".format(len(cTopic)))
            jPayload = json.loads(sPayload)  # the payload should be JSON

            # we need to ignore MQTT messages with a payload that has "Status": "Missing". Those are generated by us!
            try:
                if "Status" in jPayload and jPayload["Status"] == "Missing":
                    print("Picked up a status = missing message")
                else:
                    if len(cTopic) > 2:
                        # print("Topic[2] is {}".format(cTopic[2]))
                        if node_validate(cTopic[2]):
                            # print("Processing network message")
                            # print(jPayload)
                            nd, created = Node.objects.get_or_create(nodeID=cTopic[2])
                            nd.msgReceived()
                            nd.lastStatus = sPayload
                            nd.lastStatusTime = timezone.make_aware(
                                datetime.datetime.now(), timezone.get_current_timezone()
                            )
                            nd.jsonLoad(sPayload)
                            nd.incrementMsgCnt()
                            nd.save()
                    else:
                        # print("Gateway not in topic")
                        if "Gateway" in jPayload:
                            if node_validate(jPayload["Gateway"]):
                                print(f"Process gateway {jPayload['Gateway']}")
                                gw, created = Node.objects.get_or_create(
                                    nodeID=jPayload["Gateway"]
                                )
                                gw.msgReceived()
                                gw.lastStatus = sPayload
                                gw.lastStatusTime = timezone.make_aware(
                                    datetime.datetime.now(),
                                    timezone.get_current_timezone(),
                                )
                                gw.jsonLoad(sPayload)
                                gw.incrementMsgCnt()

                                gw.save()
            except Exception as e:
                print(e)
                print(f"Houston, we have an error {e}")

    else:  # not AKLC, a team subscription
        # the payload is expected to be json
        jPayload = json.loads(sPayload)
        # print(f"Team message arrived, topic is {msg.topic}, payload is {sPayload}")
        # print("The NodeID is {}".format(jPayload["NodeID"]))
        if "NodeID" in jPayload:
            try:
                nd, created = Node.objects.get_or_create(nodeID=jPayload["NodeID"])
                nd.msgReceived()
                nd.lastData = sPayload
                nd.lastDataTime = timezone.make_aware(
                    datetime.datetime.now(), timezone.get_current_timezone()
                )
                nd.jsonLoad(sPayload)
                nd.incrementMsgCnt()
                try:
                    tm = Team.objects.get(teamID=cTopic[0])
                    nd.team = tm
                except:
                    print("team {} not found".format(cTopic[0]))

                nd.save()
                # print(nd.team.teamID)
                # print("Processed data for {}".format(nd.nodeID))
            except Exception as e:
                print(f"Team error {e}")


# ********************************************************************
def node_validate(inNode):
    """Function to validate node names and eliminate Klingon """
    # Only the characters below are accepted in nodeID's
    for c in inNode:
        if c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890_-":
            print(f"Invalid char {c}, the name '{inNode}' is not valid")
            return False
    if inNode == "sys-monitor":  # we don't monitor ourself!
        return False
    return True


# ******************************************************************
def missing_node(node, mqtt_client):
    """
  Procedure run when a node has not been seen for a while
  """

    if node.status == "C":  # only do something if node is currently marked as "C"urrent
        print(f"Update node {node.nodeID} is down!")
        node.textStatus = "Missing"
        node.status = "X"
        node.notification_sent = True
        node.upTime = 0
        node.onlineTime = 0
        node.status_sent = timezone.make_aware(
            datetime.datetime.now(), timezone.get_current_timezone()
        )
        node.save()
        cDict = {"node": node}  # dict to pass to template
        uNotify = NodeUser.objects.filter(
            nodeID=node.id
        )  # get a list af those users to send notifications to
        for usr in uNotify:
            if usr.email:
                # print(usr.user.email)
                sendNotifyEmail(
                    "Node down notification for {}".format(node.nodeID),
                    cDict,
                    "monitor/email-down.html",
                    mqtt_client,
                    usr.user,
                )
                print(
                    f"Node {node.nodeID} marked as down and email notification sent to {usr.user.username}"
                )
                usr.lastemail = timezone.make_aware(
                    datetime.datetime.now(), timezone.get_current_timezone()
                )
            if usr.sms:
                sendNotifySMS(node, "monitor/sms-down.html", mqtt_client, usr.user)
                print(
                    f"Node {node.nodeID} marked as down and SMS notification sent to {usr.user.username}"
                )
                usr.smsSent = True
                usr.lastsms = timezone.make_aware(
                    datetime.datetime.now(), timezone.get_current_timezone()
                )
            usr.save()
    return


# ******************************************************************************
def sendNotifyEmail(inSubject, inDataDict, inTemplate, mqtt_client, mailUser):
    """A function to send email notification
    """
    payload = {}
    try:
        inDataDict["web_base_url"] = eWeb_Base_URL
        inDataDict["user"] = mailUser
        t = template.loader.get_template(inTemplate)
        body = t.render(inDataDict)

        payload["To"] = mailUser.email
        payload["From"] = eMail_From
        payload["Body"] = body
        payload["Subject"] = inSubject
        mqtt_client.publish(eMail_topic, json.dumps(payload))
        print(f"Email sent to {mailUser.email}")

    except Exception as e:
        print(e)
        print(f"Houston, we have an error {e}")

    return


# ******************************************************************************
def sendNotifySMS(inNode, inTemplate, mqtt_client, mailUser):
    """A function to send email notification
    """
    print(f"Send an SMS to {mailUser.username} about {inNode.nodeID}")
    payload = {}
    dataDict = {"node": inNode}
    # get to profile which has the phone number
    try:
        uProfile = Profile.objects.get(user=mailUser)
        print(f"Send sms to {uProfile}, the number is {uProfile.phoneNumber}")
        dataDict["web_base_url"] = eWeb_Base_URL
        dataDict["user"] = mailUser
        t = template.loader.get_template(inTemplate)
        body = t.render(dataDict)

        payload["Number"] = uProfile.phoneNumber
        payload["Text"] = body

        # print("The topic used is {}".format(sMs_topic))
        mqtt_client.publish(sMs_topic, json.dumps(payload))
    except Exception as e:
        print(e)
        print(f"Houston, we have an error {e}")

    return


# ******************************************************************
def sendReport(aNotifyUsers, mqttClient):
    """
  Function collates data and sends a full system report
  """
    print("Sending report")

    # get users to send reports to
    allUsers = Profile.objects.all()

    # get all node data for reports
    allNodes = Node.objects.all().order_by("nodeID")
    dMonthAgo = timezone.make_aware(
        datetime.datetime.now(), timezone.get_current_timezone()
    ) - datetime.timedelta(days=31)
    allNodes = allNodes.exclude(status="M").exclude(lastseen__lte=dMonthAgo)
    batWarnList = []
    batCritList = []
    nodeOKList = []
    nodeDownList = []
    gatewayOKList = []
    gatewayDownList = []
    for a in allNodes:
        if a.isGateway:
            if a.status == "C":
                gatewayOKList.append(a)
            else:
                gatewayDownList.append(a)
        else:
            if a.status == "C":
                if a.battName == None or a.battLevel == 0:
                    nodeOKList.append(a)
                else:
                    if a.battLevel > a.battWarn:
                        nodeOKList.append(a)
                    elif a.battLevel > a.battCritical:
                        batWarnList.append(a)
                    else:
                        batCritList.append(a)
            elif a.status == "X":
                nodeDownList.append(a)
    cDict = {
        "nodes": allNodes,
        "nodeOK": nodeOKList,
        "nodeWarn": batWarnList,
        "nodeCrit": batCritList,
        "nodeDown": nodeDownList,
        "gatewayOK": gatewayOKList,
        "gatewayDown": gatewayDownList,
        "web_base_url": eWeb_Base_URL,
    }

    # now iterate through users to see what report to send
    for u in allUsers:
        if u.reportType == "F":
            sendNotifyEmail(
                "Daily report", cDict, "monitor/email-full.html", mqttClient, u.user
            )
        elif u.reportType == "S":
            sendNotifyEmail(
                "Daily summary report",
                cDict,
                "monitor/email-summary.html",
                mqttClient,
                u.user,
            )
    return


# ******************************************************************
def sys_monitor():
    """ The main program that sends updates to the MQTT system
    """

    print("Start function")

    print(eMqtt_client_id)
    print(eMqtt_host)
    print(eMqtt_port)

    # The mqtt client is initialised
    client = mqtt.Client()

    # functions called by mqtt client
    client.on_connect = mqtt_on_connect
    client.on_message = mqtt_on_message
    client.on_disconnect = mqtt_on_disconnect

    try:
        # set up the MQTT environment
        client.username_pw_set(eMqtt_user, eMqtt_password)
        client.connect(eMqtt_host, int(eMqtt_port), 60)
    except Exception as e:
        print(f"MQTT connection error: {e}")

    # used to manage mqtt subscriptions
    client.loop_start()

    print("MQTT env set up done")

    # initialise the checkpoint timer
    checkTimer = timezone.now()

    # remember when we started
    startedTime = timezone.now()

    notification_data = {
        "LastSummary": datetime.datetime.now() + datetime.timedelta(days=-3)
    }

    # get any pickled notification data
    try:
        notificationPfile = open("notify.pkl", "rb")
        notification_data = pickle.load(notificationPfile)
        print("Pickled notification read")
        notificationPfile.close()
    except:
        print("Notification pickle file not found")
        notification_data = {
            "LastSummary": datetime.datetime.now() + datetime.timedelta(days=-3)
        }

    if testRunDaily == "T":  # if this environment flag is true, run the daily report
        print("Send test daily report")
        allUsers = Profile.objects.filter(user__username__startswith="jim")

        # uReport = []
        # for usr in allUsers:
        # print("User is {}, email is {}".format(usr.user.user, usr.user.email))
        #  if usr.reportType == 'F':
        #      uReport.append(usr.user)
        #      print("Full report to {}".format(usr.user.email))

        sendReport(allUsers, client)

    print("About to start loop")

    while True:
        time.sleep(1)

        try:
            # this section runs regularly (every 15 sec) and does a number of functions
            if (timezone.now() - checkTimer) > datetime.timedelta(
                0, 15
            ):  # second value is seconds to pause between....
                # update the checkpoint timer
                checkTimer = timezone.now()  # reset timer

                # print("Timer check {}".format(timezone.make_aware(datetime.datetime.now(), timezone.get_current_timezone())))

                allNodes = Node.objects.all()

                tdRunning = timezone.now() - startedTime
                if (
                    tdRunning.total_seconds() > 3600
                ):  # dont check if nodes are down until you have been running for at least an hour
                    for n in allNodes:
                        # if nothing then our 'patience' will run out
                        if (timezone.now() - n.lastseen) > datetime.timedelta(
                            minutes=n.allowedDowntime
                        ):
                            # print("Node {} not seen for over {} minutes".format(n, n.allowedDowntime))
                            missing_node(n, client)

                # if (timezone.now() - startTime) > datetime.timedelta(hours=1):    # this section is ony run if the script has been running for an hour
                if (
                    timezone.make_aware(
                        datetime.datetime.now(), timezone.get_current_timezone()
                    )
                    .now()
                    .hour
                    > 7
                ):  # run at certain time of the day
                    # print("Time now {}".format(timezone.now()))
                    if (
                        notification_data["LastSummary"].day
                        != datetime.datetime.now().day
                    ):
                        print("Send 8am messages")

                        allUsers = Profile.objects.all()
                        uReport = []
                        for usr in allUsers:
                            # print("User is {}, email is {}".format(usr.user.username, usr.user.email))
                            if usr.reportType == "F":
                                uReport.append(usr.user)
                                print(f"Full report to {usr.user.email}")

                        # sendReport(uReport, client)
                        sendReport(allUsers, client)

                        # update out notification data and save
                        notification_data["LastSummary"] = datetime.datetime.now()
                        # write a pickle containing current notification data
                        try:
                            notificationPfile = open("notify.pkl", "wb")
                            pickle.dump(notification_data, notificationPfile)
                            notificationPfile.close()
                        except Exception as e:
                            print(f"Notification Pickle failed {e}")

                        # function to remove old nodes in 'M'aintenance mode
                        print("Checking for maintenace nodes to purge")
                        dCutOff = timezone.now() - datetime.timedelta(days=360)
                        print(f"Cutoff date is {dCutOff}")
                        allMaint = Node.objects.filter(status="M").filter(
                            lastseen__lt=dCutOff
                        )
                        print(f"There are {len(allMaint)} nodes in maintenance mode")
                        # delete all these nodes
                        allMaint.delete()

        except Exception as e:
            print(f"Houston, we have an error {e}")


# ********************************************************************
if __name__ == "__main__":
    sys_monitor()
