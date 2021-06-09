import django
import sys
import os
from django.conf import settings
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import json
import datetime
import time
import html2text
from django.utils import timezone
from django import template
#from email.mime.text import MIMEText

# timezone.make_aware(yourdate, timezone.get_current_timezone())

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
testFlag = os.getenv("AKLC_TESTING", False)
connectionCount = 1
msgCount = 0
AKLC_Status = 0
AKLC_Network = 0
AKLC_Node = 0
AKLC_Gateway = 0
dProj = {}  # empty dict for project totals

if testFlag:
    scriptID = "DJ_Mon_Script-TEST"
else:
    scriptID = "DJ_Mon_Script"

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
    sub_topic = "AKLC/#"
    client.subscribe(sub_topic)
    print(f"MQTT Subscribed to {sub_topic}")
    client.publish(
        f"AKLC/monitor/{scriptID}/LWT", payload="Running", qos=0, retain=True
    )
    print("Sent connection message")

    # Teams are 1st level TOPICs, used to separate data for various communities
    # We subscribe to all devined teams
    aTeams = Team.objects.all()
    for t in aTeams:
        sub_topic = t.teamID + "/#"
        print(sub_topic)
        client.subscribe(sub_topic)
        if t.teamID not in dProj:
            dProj[t.teamID] = 0


# ********************************************************************
def mqtt_on_disconnect(client, userdata, rc):
    """
      This procedure is called on connection to the mqtt broker
    """
    global connectionCount
    print(f"MQTT has disconnected, the code was {rc}, attempting to reconnect")
    res = client.reconnect()
    print(f"Reconnect result was {res}")
    connectionCount = connectionCount + 1
    print(f"Reconnect result was {res}, connection count is now {connectionCount}")
    client.publish(
        f"AKLC/monitor/{scriptID}/LWT", payload="Running", qos=0, retain=True
    )
    return


# ********************************************************************
def mqtt_on_message(client, userdata, msg):
    """This procedure is called each time a mqtt message is received"""
    global msgCount, AKLC_Status, AKLC_Network, AKLC_Node, AKLC_Gateway, dProj

    testPr(f"mqtt message received {msg.topic} : {msg.payload}")
    msgCount = msgCount + 1

    # separate the topic up so we can work with it
    cTopic = msg.topic.split("/")
    cDict = {}

    # get the payload as a string
    try:
        sPayload = msg.payload.decode()
    except Exception as e:
        print(
            f"Houston, we had an error {e} decoding the payload. Topic was {msg.topic}, payload was {msg.payload}"
        )
        return

    # Check for nodes using regular topic structure
    if cTopic[0] == "AKLC":
        # testPr("Aklc TEST message received, topic {}, payload {}".format(msg.topic, msg.payload))
        # Check types of message from the topic

        if cTopic[1] == "Status":
            AKLC_Status = AKLC_Status + 1
            # These are status messages sent by gateways. Data in CSV format
            cPayload = sPayload.split(",")
            cNode = cPayload[0]
            testPr(
                f"Gateway status (AKLC/Status) message received for {cNode}, payload is {cPayload}"
            )
            # Check and update the gateway data
            if node_validate(cNode):
                # print(f"Make/get node {cNode}")
                gw, created = Node.objects.get_or_create(nodeID=cNode)
                # print(f"MG Success")
                if created:
                    print(f"Gateway {gw.nodeID} created")
                gw.msgReceived(client, eMail_From, eMail_topic)
                gw.isGateway = True
                gw.lastStatus = sPayload
                gw.lastStatusTime = timezone.make_aware(
                    datetime.datetime.now(), timezone.get_current_timezone()
                )

                gw.incrementMsgCnt()
                gw.save()
                nJson = gw.make_json(sPayload)
                testPr(f"Gateway JSON is {nJson}")
                if "Uptime" in nJson:
                    gw.bootTimeUpdate(nJson["Uptime"])
                if "Uptime(s)" in nJson:
                    gw.bootTimeUpdate(nJson["Uptime(s)"] / 60)
                if "Uptime(m)" in nJson:
                    gw.bootTimeUpdate(nJson["Uptime(m)"])
                if "HWType" in nJson:
                    gw.hardware = nJson["HWType"]
                if "Version" in nJson:
                    gw.software = nJson["Version"]
                if "Reply" in nJson:
                    client.publish(f"AKLC/Control/{gw.nodeID}", "Status received")
                gw.save()
            else:
                testPr(f"Gateway {cNode} not processed")

        elif cTopic[1] == "Gateway":
            # These are data messages from nodes sent on by a gateway, payload should be CSV
            # print("Gateway message received")
            AKLC_Gateway = AKLC_Gateway + 1
            cPayload = sPayload.split(",")  # the payload should be CSV
            if len(cPayload) < 2:
                testPr(f"Gateway msg {msg.topic} received, invalid payload {sPayload}")
                return
            testPr(
                f"Gateway msg (AKLC/Gateway) received, Node {cPayload[1]}, Gateway {cPayload[0]}, payload is {sPayload}"
            )

            if cPayload[1].startswith("Test"):
                testPr("Test message, ignored")
                return
            if "GWSTATUS" in cPayload[0]:
                cPayload.pop(0)
                return  # Actually, just ignore it, rubbish message

            if node_validate(cPayload[1]):  # check if the nodeID is valid
                # get the node, or create it if not found
                # print("Valid node {}".format(cPayload[1]))
                nd, created = Node.objects.get_or_create(nodeID=cPayload[1])
                nd.msgReceived(client, eMail_From, eMail_topic)
                if cPayload[2] != "OK":
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
                sJson = json.dumps(nJson)
                nd.jsonLoad(sJson)
                testPr(f"JSON is {nJson}")
                # if "Uptime" in nJson:
                #    nd.bootTimeUpdate(nJson["Uptime"])
                # if "Uptime(s)" in nJson:
                #    nd.bootTimeUpdate(nJson["Uptime(s)"] / 60)
                # if "Uptime(m)" in nJson:
                #    nd.bootTimeUpdate(nJson["Uptime(m)"])
                nd.save()

            # Check and update the gateways info
            if node_validate(cPayload[0]):  # payload[0] is the gateway
                # print("Valid gateway {}".format(cPayload[0]))
                gw, created = Node.objects.get_or_create(nodeID=cPayload[0])
                gw.msgReceived(client, eMail_From, eMail_topic)
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
            testPr(
                f"Network message (AKLC/Network) received |{sPayload}|, topic |{msg.topic}|"
            )
            # print("Topic length = {}".format(len(cTopic)))
            AKLC_Network = AKLC_Network + 1
            if not is_json(sPayload):
                print(
                    f"Network style message error, payload is |{sPayload}|, topic is |{msg.topic}|"
                )
                return

            jPayload = json.loads(sPayload)  # the payload should be JSON

            # we need to ignore MQTT messages with a payload that has "Status": "Missing". Those are generated by us!
            try:
                if "Status" in jPayload and jPayload["Status"] == "Missing":
                    testPr("Picked up a status = missing message")
                else:
                    if len(cTopic) > 2:
                        devID = cTopic[2]
                    elif "NodeID" in jPayload:
                        devID = jPayload["NodeID"]
                    elif "Gateway" in jPayload:
                        devID = jPayload["Gateway"]
                    else:
                        print(
                            f"Bad status message, topic: {msg.topic}, payload: {sPayload}"
                        )
                        return
                    if node_validate(devID):
                        # print("Processing network message")
                        # print(jPayload)
                        nd, created = Node.objects.get_or_create(nodeID=devID)
                        nd.msgReceived(client, eMail_From, eMail_topic)
                        nd.lastStatus = sPayload
                        nd.lastStatusTime = timezone.make_aware(
                            datetime.datetime.now(), timezone.get_current_timezone()
                        )
                        nd.jsonLoad(sPayload)
                        nd.incrementMsgCnt()
                        if "Reply" in jPayload:
                            client.publish(
                                f"AKLC/Control/{nd.nodeID}", "Status received"
                            )
                        nd.save()

            except Exception as e:
                print(e)
                print(f"Houston, we have an error {e}")
        elif (
            cTopic[1] == "Node"
        ):  # These are data messages sent by gateways and nodes. Data in JSON format
            testPr(
                f"Node message (AKLC/Node) received |{sPayload}|, topic |{msg.topic}|"
            )
            AKLC_Node = AKLC_Node + 1

            if not is_json(sPayload):
                print(f"Node style message error, payload is |{sPayload}|")
                return

            jPayload = json.loads(sPayload)  # the payload should be JSON
            if len(cTopic) > 2:
                # print("Topic[2] is {}".format(cTopic[2]))
                if node_validate(cTopic[2]):
                    testPr(f"Processing node message for {cTopic[2]}")
                    nd, created = Node.objects.get_or_create(nodeID=cTopic[2])
                    nd.msgReceived(client, eMail_From, eMail_topic)
                    nd.lastData = sPayload
                    nd.lastDataTime = timezone.make_aware(
                        datetime.datetime.now(), timezone.get_current_timezone()
                    )
                    nd.incrementMsgCnt()
                    if "Reply" in jPayload:
                        client.publish(f"AKLC/Control/{nd.nodeID}", "Data received")
                    nd.save()

    else:  # not AKLC, a team subscription
        # the payload is expected to be json
        if not is_json(sPayload):
            print(
                f"Project message received, should be JSON but was topic: {msg.topic} & payload: {sPayload}"
            )
            return
        jPayload = json.loads(sPayload)
        testPr(f"Team message arrived, topic is {msg.topic}, payload is {sPayload}")
        if cTopic[0] in dProj:
            dProj[cTopic[0]] = dProj[cTopic[0]] + 1
        if "NodeID" in jPayload:
            try:
                nd, created = Node.objects.get_or_create(nodeID=jPayload["NodeID"])
                nd.msgReceived(client, eMail_From, eMail_topic)
                if "Status" in jPayload:
                    nd.lastStatus = sPayload
                    nd.lastStatusTime = timezone.make_aware(
                        datetime.datetime.now(), timezone.get_current_timezone()
                    )
                else:
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
            except Exception as e:
                print(f"Team error {e}, message topic:{msg.topic}, payload :{sPayload}")


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
        testPr(f"Update node {node.nodeID} is down!")
        node.textStatus = "Missing"
        node.status = "X"
        node.notification_sent = True
        node.upTime = 0
        node.onlineTime = 0
        node.status_sent = timezone.now()
        node.save()
        cDict = {"node": node}  # dict to pass to template
        uNotify = NodeUser.objects.filter(
            nodeID=node.id
        )  # get a list af those users to send notifications to
        for usr in uNotify:
            if usr.email:
                # print(f"Send notification email to {usr.user.email}")
                if usr.nodeID.email_down_template:
                    sendNotifyEmail(
                        "Node down notification for {}".format(node.nodeID),
                        cDict,
                        f"monitor/{usr.nodeID.email_down_template.fileName}",
                        mqtt_client,
                        usr.user,
                        node=node,
                    )
                else:
                    sendNotifyEmail(
                        "Node down notification for {}".format(node.nodeID),
                        cDict,
                        "monitor/email-down.html",
                        mqtt_client,
                        usr.user,
                        node=node,
                    )
                print(
                    f"Node {node.nodeID} marked as down and email notification sent to {usr.user.username}"
                )
                usr.lastemail = timezone.now()
            if usr.sms:
                sendNotifySMS(node, "monitor/sms-down.html", mqtt_client, usr.user)
                print(
                    f"Node {node.nodeID} marked as down and SMS notification sent to {usr.user.username}"
                )
                usr.smsSent = True
                usr.lastsms = timezone.now()
            usr.save()
    return


# ******************************************************************************
def sendNotifyEmail(
    inSubject, inDataDict, inTemplate, mqtt_client, mailUser, node=None
):
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
        if testFlag:
            payload["Subject"] += " from development system"

        # Error happening here
        mqtt_client.publish(eMail_topic, json.dumps(payload))
        print(f"Email sent to {mailUser.email}")

        notifLog = notificationLog(
            address=mailUser.email,
            subject=payload["Subject"],
            body=html2text.html2text(body),
            user=mailUser,
        )
        if node:
            notifLog.node = node
        notifLog.save()

    except Exception as e:
        print(e)
        print(f"Houston, we have an error {e}")

    return


# ******************************************************************************
def sendNotifySMS(inNode, inTemplate, mqtt_client, mailUser, node=None):
    """A function to send email notification
    """
    testPr(f"Send an SMS to {mailUser.username} about {inNode.nodeID}")
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
        if testFlag:
            payload["Text"] = "(Dev) " + body
        else:
            payload["Text"] = body
        mqtt_client.publish(sMs_topic, json.dumps(payload))

        notifLog = notificationLog(
            address=uProfile.phoneNumber,
            body=payload["Text"],
            user=mailUser,
            node=inNode,
        )
        notifLog.save()

    except Exception as e:
        print(e)
        print(f"Houston, we have an error {e}")

    return


# ******************************************************************
def sendReport(aNotifyUsers, mqttClient):
    """
  Function collates data and sends a full system report
  """
    testPr("Sending report")

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
    repeaterOKList = []
    repeaterDownList = []
    for a in allNodes:
        if a.isGateway:
            if a.status == "C":
                gatewayOKList.append(a)
            else:
                gatewayDownList.append(a)
        elif a.isRepeater:
            if a.status == "C":
                repeaterOKList.append(a)
            else:
                repeaterDownList.append(a)
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
        "repeaterOK": repeaterOKList,
        "repeaterDown": repeaterDownList,
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
def sendDailyReminder(mqttClient):
    """
    Checks to see if reminder emails should be sent
    """
    print("Daily reminder checks")
    allUsers = User.objects.all()
    for usr in allUsers:
        for nu in usr.nodeuser_set.all():
            testPr(f"Node user {nu}, status {nu.nodeID.status}")
            if nu.daily:
                if nu.nodeID.status == "X":
                    if nu.nodeID.email_reminder_template:
                        testPr(f"Send reminder to {usr} that {nu.nodeID} is down")
                        cDict = {"user": usr}
                        cDict["node"] = nu.nodeID
                        sendNotifyEmail(
                            f"Daily reminder that {nu.nodeID} is still unresponsive",
                            cDict,
                            f"monitor/{nu.nodeID.email_reminder_template.fileName}",
                            mqttClient,
                            usr,
                            node=nu,
                        )

# ******************************************************************
def sendWebNotify(mqtt_client):
    """
    Sends notifications left in the webNotification table
    """
    wN = webNotification.objects.filter(processed=False)

    print("Checking for web notifications")

    if wN:
        print(f"We have {len(wN)} web notifications to process")

        for w in wN:
            if w.email:
                payload= {"To": w.address}
                payload["From"] = eMail_From
                payload["Body"] = w.body
                payload["Subject"] = w.subject
                mqtt_client.publish(eMail_topic, json.dumps(payload))
                print(f"Email sent to {w.address}, payload is: {payload}")

                
            if w.sms:
                payload = {"Number": w.address}
                if testFlag:
                    payload["Text"] = "(Dev) " + w.body
                else:
                    payload["Text"] = w.body
                mqtt_client.publish(sMs_topic, json.dumps(payload))
                print(f"SMS sent to {w.address}")

            notifLog = notificationLog(
                address=w.address,
                subject=w.subject,
                body=html2text.html2text(w.body),
            )
            if w.user:
                notifLog.user = w.user
            if w.node:
                notifLog.node = w.node
            notifLog.save()
            w.processed = True
            w.processed_dt = timezone.now()
            w.save()



# ******************************************************************
def sys_monitor():
    """ The main program that sends updates to the MQTT system
    """

    global scriptID

    print(" ")
    print(" ")
    print("---------------------------------")
    print("Start function - script monitor")
    print("---------------------------------")

    gConfig, created = Config.objects.get_or_create(id=1)

    print(eMqtt_client_id)
    print(eMqtt_host)
    print(eMqtt_port)

    # The mqtt client is initialised
    print(f"Connect to MQTT queue {eMqtt_host}")

    client = mqtt.Client()

    # functions called by mqtt client
    client.on_connect = mqtt_on_connect
    client.on_message = mqtt_on_message
    client.on_disconnect = mqtt_on_disconnect

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
    statusTimer = timezone.now()
    startTime = timezone.make_aware(
        datetime.datetime.now(), timezone.get_current_timezone()
    )

    # remember when we started
    startedTime = timezone.now()

    if testRunDaily == "T":  # if this environment flag is true, run the daily report
        print("Send test daily report")
        allUsers = Profile.objects.filter(user__username__startswith="jim")

        sendDailyReminder(client)

        allNodes = Node.objects.all()
        for n in allNodes:
            # if nothing then our 'patience' will run out
            if (timezone.now() - n.lastseen) > datetime.timedelta(
                minutes=n.allowedDowntime
            ):
                print(
                    "Node {} not seen for over {} minutes".format(n, n.allowedDowntime)
                )
                missing_node(n, client)

    print("About to start loop")

    while True:
        time.sleep(1)

        try:
            # this section runs regularly (every 15 sec) and does a number of functions
            if (timezone.now() - checkTimer) > datetime.timedelta(
                0, gConfig.NodeCheckPeriod
            ):  # second value is seconds to pause between....
                # update the checkpoint timer
                checkTimer = timezone.now()  # reset timer

                # print("Timer check {}".format(timezone.make_aware(datetime.datetime.now(), timezone.get_current_timezone())))
                gConfig.refresh_from_db()
                tdRunning = timezone.now() - startedTime
                if tdRunning.total_seconds() > (
                    gConfig.NodeCheckDelay * 60
                ):  # dont check if nodes are down until you have been running for a while

                    allNodes = Node.objects.all()
                    for n in allNodes:
                        # if nothing then our 'patience' will run out
                        if (timezone.now() - n.lastseen) > datetime.timedelta(
                            minutes=n.allowedDowntime
                        ):
                            # print("Node {} not seen for over {} minutes".format(n, n.allowedDowntime))
                            missing_node(n, client)
                    gConfig.NodeCheckTime = timezone.now()
                    gConfig.save()
                # if (timezone.now() - startTime) > datetime.timedelta(hours=1):    # this section is ony run if the script has been running for an hour

                localTime = datetime.time(
                    hour=timezone.localtime().hour, minute=timezone.localtime().minute
                )
                # print(f"localtime: {localTime}, gConfig.SummaryReportTime: {gConfig.SummaryReportTime}")

                if localTime > gConfig.SummaryReportTime:
                    testPr("Report time")
                    # run at certain time of the day
                    # print(f"DB record: {gConfig.LastSummary.astimezone()}, timezone.now day: {timezone.localtime()}")
                    # print(f"DB record day: {gConfig.LastSummary.astimezone().day}, timezone.localtime day: {timezone.localtime().day}")
                    # print(f"DB record hour: {gConfig.LastSummary.astimezone().hour}, timezone.localtime hour: {timezone.localtime().hour}")
                    if gConfig.LastSummary.astimezone().day != timezone.localtime().day:
                        testPr("Send 8am messages")

                        allUsers = Profile.objects.all()

                        sendDailyReminder(client)

                        uReport = []
                        for usr in allUsers:
                            # print("User is {}, email is {}".format(usr.user.username, usr.user.email))
                            if usr.reportType == "F":
                                uReport.append(usr.user)
                                testPr(f"Full report to {usr.user.email}")

                        # sendReport(uReport, client)
                        sendReport(allUsers, client)

                        # update our notification data and save
                        # write the data to the config table
                        gConfig.LastSummary = timezone.localtime()
                        gConfig.save()

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

                #check to see if there are any messages that need to be sent
                sendWebNotify(client)

        except Exception as e:
            print(f"Houston, we have an error {e}")

        # print(f"{timezone.now()} - {statusTimer} is {timezone.now() - statusTimer}, and diff is {datetime.timedelta(minutes=gConfig.MqttStatusPeriod)}")

        if (timezone.now() - statusTimer) > datetime.timedelta(
            minutes=gConfig.MqttStatusPeriod
        ):
            print("Send MQTT Status")
            statusTimer = timezone.now()  # reset timer
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
                "AKLC_Node": AKLC_Node,
                "AKLC_Network": AKLC_Network,
                "AKLC_Status": AKLC_Status,
                "AKLC_Gateway": AKLC_Gateway,
                # "Projects": dProj,
            }
            for p, v in dProj.items():
                payLoad[p] = v
            print(f"Regular reporting payload is {payLoad}")
            client.publish(
                f"AKLC/monitor/{scriptID}/status",
                payload=json.dumps(payLoad),
                qos=0,
                retain=False,
            )


# ********************************************************************
if __name__ == "__main__":
    sys_monitor()
