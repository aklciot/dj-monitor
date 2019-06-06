import django
import sys
import os
from django.conf import settings
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import json
import datetime
import time
from django.utils import timezone
from django import template
from email.mime.text import MIMEText
#timezone.make_aware(yourdate, timezone.get_current_timezone())

sys.path.append("/code/aklc")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aklc.settings")

eMqtt_client_id = os.getenv("AKLC_MQTT_CLIENT_ID", "mqtt_monitor")
eMqtt_host = os.getenv("AKLC_MQTT_HOST", "172.17.0.4")
eMqtt_port = os.getenv("AKLC_MQTT_PORT", "1883")
eMqtt_user = os.getenv("AKLC_MQTT_USER", "")
eMqtt_password = os.getenv("AKLC_MQTT_PASSWORD", "")
eMail_From = os.getenv("AKLC_MAIL_FROM", "info@innovateauckland.nz")

django.setup()

from monitor.models import Node

# ********************************************************************
def mqtt_on_connect(client, userdata, flags, rc):
    """
      This procedure is called on connection to the mqtt broker
    """
    #global nodes_config
    
    print("Connected to mqtt with result code "+str(rc))
    sub_topic = "AKLC/#"
    client.subscribe(sub_topic)
    print("mqtt Subscribed to " + sub_topic)
    
#********************************************************************
def mqtt_on_message(client, userdata, msg):
    """This procedure is called each time a mqtt message is received"""

    print("mqtt message received {} : {}".format(msg.topic, msg.payload))

    #separate the topic up so we can work with it
    cTopic = msg.topic.split("/")
    cDict = {}
    sPayload = msg.payload.decode()


    # Check for nodes using regular topic structure
    if cTopic[0] == "AKLC":
        print("Processing AKLC message, next level is |{}|".format(cTopic[1]))
        # Check types of message from the topic
        if "Gateway" == cTopic[1]:
            print("Processing Gateway message")
            # These are messages from nodes sent on by a gateway
            
            cPayload = sPayload.split(",")   # the payload should be CSV
            
            print("Node {}, Gateway {}".format(cPayload[1], cPayload[0]))
            if node_validate(cPayload[1]):
                nd, created = Node.objects.get_or_create(nodeID = cPayload[1])
                        
                nd.lastseen = timezone.make_aware(datetime.datetime.now(), timezone.get_current_timezone())
                nd.textStatus = "Online"
                nd.status = 'C'
                nd.lastData = sPayload
                nd.save()
          	# Check and update the gateways info
            if node_validate(cPayload[0]):
                gw, created = Node.objects.get_or_create(nodeID = cPayload[0])
                gw.lastseen = timezone.make_aware(datetime.datetime.now(), timezone.get_current_timezone())
                gw.isGateway = True
                gw.textStatus = "Online"
                gw.status = "C"
                gw.lastData = sPayload
                gw.save()
              
              
        if cTopic[1] == "Status":      # These are status messages sent by gateways. Data in CSV format
            cPayload = msg.payload.split(",")
            cNode = cPayload[0]             
            print("Processing status message for {}".format(cNode))
            
            # Check and update the gateways dictionary
            if node_validate(cPayload[0]):
                gw, created = Node.objects.get_or_create(nodeID = cPayload[0])
                        
                gw.lastseen = timezone.make_aware(datetime.datetime.now(), timezone.get_current_timezone())
                gw.isGateway = True
                gw.textStatus = "Online"
                gw.status = "C"
                gw.lastData = sPayload
                gw.save()
              

        if cTopic[1] == "Network":      # These are status messages sent by gateways and nodes. Data in JSON format
            jPayload = json.loads(msg.payload)   # the payload should be JSON
            #print("Network status message received from {}".format(cTopic[2]))
            bUpdate = True
            # we need to ignore MQTT messages with a payload that has "Status": "Missing". Those are generated by us!
            if "Status" in jPayload:
                if jPayload["Status"] == "Missing":
                    print("Picked up a status = missing message")
                    bUpdate = False
            if bUpdate and node_validate(cTopic[2]):
                #print("Processing network message")
                nd, created = Node.objects.get_or_create(nodeID = cTopic[2])
                nd.lastseen = timezone.make_aware(datetime.datetime.now(), timezone.get_current_timezone())
                nd.textStatus = "Online"
                nd.status = "C"
                nd.lastData = sPayload
                if nd.battName in jPayload:
                    nd.battValue = jPayload[nd.battName]
                nd.save()

  


# ********************************************************************
def node_validate(inNode):
    """Function to validate node names and eliminate Klingon """
    # Only the characters below are accepted in nodeID's
    for c in inNode:
        if c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890_-':
          print("Invalid char {}".format(c))
          return(False)
    if inNode == "sys-monitor":     # we don't monitor ourself!
        return(False)
    return(True)

#******************************************************************
def missing_node(node, mqtt_client):
  """
  Procedure run when a node has not been seen for a while
  """
  if node.status == 'C':
    node.textStatus = "Missing"
    node.status = "X"
    node.notification_sent = True
    node.status_sent = timezone.make_aware(datetime.datetime.now(), timezone.get_current_timezone())
    node.save()
    cDict = {'node': node}
    sendNotifyEmail("Node down notification for {}".format(node.nodeID), cDict, "monitor/email-down.html", mqtt_client)
    print("Node {} marked as down and notification sent".format(node.nodeID))
  return

# ******************************************************************************
def sendNotifyEmail(inSubject, inDataDict, inTemplate, mqtt_client):
    """A function to send email notification
    """
    payload = {}
    try:
       
        t = template.loader.get_template(inTemplate)
        body = t.render(inDataDict)
      
        msg = MIMEText(body, 'html') 
        msg['From'] = eMail_From
        msg['To'] = "jim@west.net.nz"
        msg['Subject'] = inSubject
      
        payload['To'] = "jim@west.net.nz"
        payload['From'] = 'info@innovateauckland.nz'
        payload['Body'] = msg.as_string()

        mqtt_client.publish('AKLC/send/email', json.dumps(payload))

    except Exception as e:
        print(e)
        print("Houston, we have an error {}".format(e))  
       
    return


#******************************************************************
def sys_monitor():
    """ The main program that sends updates to the MQTT system
    """

    print("Start function")

    print(eMqtt_client_id)
    print(eMqtt_host)
    print(eMqtt_port)

    #The mqtt client is initialised
    client = mqtt.Client(client_id=eMqtt_client_id)

    #functions called by mqtt client
    client.on_connect = mqtt_on_connect
    client.on_message = mqtt_on_message
    print("MQTT env set up done")

    try:

    # set up the local MQTT environment
        client.username_pw_set(eMqtt_user, eMqtt_password)
        client.connect(eMqtt_host, int(eMqtt_port), 60)
    except Exception as e:
        print(e)

    # used to manage mqtt subscriptions
    client.loop_start()

    #initialise the checkpoint timer
    checkTimer = timezone.now()   

    print("About to start loop")

    while True:
      time.sleep(1)
      
      # this section runs regularly (every 15 sec) and does a number of functions
      if (timezone.now() - checkTimer) > datetime.timedelta(0,15):  #second value is seconds to pause between....
        # update the checkpoint timer
        checkTimer = timezone.now()                                 #reset timer
        
        print("Timer check")

        allNodes = Node.objects.all()

        for n in allNodes:
            #if nothing then our 'patience' will run out
            if (timezone.now() - n.lastseen) > datetime.timedelta(minutes=n.allowedDowntime):
                print("Node {} not seen for over {} minutes".format(n, n.allowedDowntime))
                missing_node(n, client)
               


#********************************************************************
if __name__ == "__main__":
    sys_monitor()
