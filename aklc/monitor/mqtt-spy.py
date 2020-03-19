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

# need this to access django models and templates
sys.path.append("/code/aklc")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aklc.settings")
django.setup()

from monitor.models import (
    Node,
    Team,
    MqttQueue,
    MqttMessage,
)
from django.contrib.auth.models import User


# ********************************************************************
"""
This function is called when the MQTT client connects to the MQTT broker
"""
def mqtt_on_connect(client, userdata, flags, rc):
    """
      This procedure is called on connection to the mqtt broker
    """

    print(f"Connected to {userdata.descr} with result code {rc}")
    sub_topic = "AKLC/#"
    client.subscribe(sub_topic)
    print("mqtt Subscribed to " + sub_topic)

    # Teams are 1st level TOPICs, used to separate data for various communities
    # We subscribe to all defined teams
    aTeams = Team.objects.all()
    for t in aTeams:
        sub_topic = t.teamID + "/#"
        print("MQTT Subscribed to {}".format(sub_topic))
        client.subscribe(sub_topic)
    return

# ********************************************************************
"""
This function is called when an mqtt message is received
"""
def mqtt_on_message(client, userdata, msg):
    """
      This procedure is called when a msg is recieved
    """
    #print(f"Msg recived on {userdata.descr}, topic {msg.topic}, payload {msg.payload}")
    
    # first have to find a node id
    cNode = ""
    cTopic = msg.topic.split("/")
    sPayload = msg.payload.decode()

    if cTopic[0] == "AKLC":
        #print(f"AKLC msg received, next is {cTopic[1]}, payload is {sPayload}")
        if cTopic[1] == "Status":  # Status messages from Gateways, data in CSV format
            try:
                cPayload = sPayload.split(",")
                cNode=cPayload[0]
                #print(f"Status - Node is {cNode}")
            except Exception as e:
                print(e)
                print(f"Houston, we have an error {e}")

        elif cTopic[1] == "Gateway":  # Data message passed on by gateway, data in CSV format
            cPayload = sPayload.split(",")
            if "Test" in cPayload[1]:
                #print(f"Test message received, topic is {msg.topic}, payload is {sPayload}, msg not processed")
                return           
            cNode=cPayload[1]

        elif (
            cTopic[1] == "Node" or cTopic[1] == "Network"
        ):
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

    else: # must be a team message
        jPayload = json.loads(sPayload)
        if "NodeID" in jPayload:
            cNode = jPayload["NodeID"]
    
    # Lets get the node record
    try:
        node = Node.objects.get(nodeID=cNode)
        #print(f"Node found {node.nodeID}")
    except:
        return

    
    try:
        #print(f"node is {node.nodeID}, mqttQueue is {userdata.descr}")
        mqttMsg, created = MqttMessage.objects.get_or_create(node=node, mqttQueue=userdata)
        mqttMsg.topic = msg.topic
        mqttMsg.payload = sPayload
        mqttMsg.save()

    except Exception as e:
        print(e)
        print(f"Houston, we have an error {e}")
    return



# ******************************************************************
def mqtt_spy():
    """ The main program that sends updates to the MQTT system
    """

    aMqtt = MqttQueue.objects.all()
    cMqtt = []
    
    for m in aMqtt:
        print(f"Set up mqtt queue {m.descr}")
        #clnt = mqtt.Client(userdata=m)
        cMqtt.append(mqtt.Client(userdata=m))
        cMqtt[-1].on_connect = mqtt_on_connect
        cMqtt[-1].on_message = mqtt_on_message
        print(f"User is {m.user}, pw is {m.pw}")
        if m.user:
            print("User present")
            cMqtt[-1].username_pw_set(m.user, m.pw)
        
        print(f"Connect to {m.host} on port {m.port}")
        cMqtt[-1].connect(m.host, m.port, 60)
        
        print("Client connect requested")
        cMqtt[-1].loop_start()
        
        time.sleep(5)
    

    while True:
        time.sleep(1)


    print("Finished")


# ********************************************************************
if __name__ == "__main__":
    mqtt_spy()

