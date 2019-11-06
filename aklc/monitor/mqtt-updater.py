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

from monitor.models import Node, Profile, NodeUser, Team, NodeGateway, MessageType, MessageItem, NodeMsgStats
from django.contrib.auth.models import User

# all config parameters are set as environment variables, best practice in docker environment
eMqtt_client_id = os.getenv("AKLC_MQTT_CLIENT_ID", "mqtt_monitor_updater-1")
eMqtt_host = os.getenv("AKLC_MQTT_HOST", "mqtt.innovateauckland.nz")
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
eInflux_db = os.getenv("AKLC_INFLUX_DB", "influx")

# ********************************************************************
"""
This function is called when the MQTT client connects to the MQTT broker
"""
def mqtt_on_connect(client, userdata, flags, rc):
    """
      This procedure is called on connection to the mqtt broker
    """
      
    print("Connected to mqtt with result code "+str(rc))
    sub_topic = "AKLC/#"
    client.subscribe(sub_topic)
    print("mqtt Subscribed to " + sub_topic)

    # Teams are 1st level TOPICs, used to separate data for various communities
    # We subscribe to all devined teams
    #aTeams = Team.objects.all()
    #for t in aTeams:
    #  sub_topic = t.teamID + "/#"
    #  print(sub_topic)
    #  client.subscribe(sub_topic)


#********************************************************************

def is_json(myjson):
  """
  Function to check if an input is a valid JSON message
  """
  try:
    json_object = json.loads(myjson)
  except ValueError as e:
    return False
  return True
    
#********************************************************************
def mqtt_on_message(client, userdata, msg):
    """This procedure is called each time a mqtt message is received

    | AKLC | Gateway | Data message passed on by gateway, data in CSV format
    | AKLC | Status  | Status messages from Gateways, data in CSV format
    | AKLC | Network | Data & status messages from Gateways, data in JSON format
    | AKLC | Node    | Data & Status direct from a Node, data in JSON format

    """

    #print("mqtt message received {} : {}".format(msg.topic, msg.payload))
    #separate the topic up so we can work with it
    cTopic = msg.topic.split("/")
    cDict = {}
    
    # get the payload as a string
    sPayload = msg.payload.decode()

    # Check for nodes using regular topic structure
    if cTopic[0] == "AKLC":
        #print("Aklc message received, topic {}, payload {}".format(msg.topic, msg.payload))
        # Check types of message from the topic
        #print("Subtopic = |{}|".format(cTopic[1]))
        if cTopic[1] == "Status":         # Status messages from Gateways, data in CSV format
          print("Gateway status message received")
          cPayload = sPayload.split(",")   # the payload should be CSV
          try:
            node = Node.objects.get(nodeID = cPayload[0])   # Lets 
            print("Gateway {} found".format(node.nodeID))

            if node.messagetype:
              print("Messagetype found")

              jStr = {}   # create empty dict
              print(cPayload)
              for mItem in node.messagetype.messageitem_set.all():
                #print("  msgItem is {}, value is {}".format(mItem.name, cPayload[mItem.order-1]))
                # some validation here

                if mItem.order > len(cPayload):
                  print("Too many items in message type record for the payload, oder is {}".format(mItem.order))
                  break

                try:
                  if mItem.fieldType == 'I':
                    jStr[mItem.name] = int(cPayload[mItem.order-1])
                  elif mItem.fieldType == 'F':
                    jStr[mItem.name] = float(cPayload[mItem.order-1])
                  else:
                    jStr[mItem.name] = cPayload[mItem.order-1]
                except Exception as e:
                  print(e)

              #print(jStr)
              print("Heres the JSON string {}".format(json.dumps(jStr)))

              if node.thingsboardUpload:
                mRes = publish.single(topic = eTB_topic, payload = json.dumps(jStr), 
                    hostname = eTB_host, port = eTB_port, 
                    auth = {'username':node.thingsboardCred})

          except Exception as e:
            print(e)
            print("Cant find {} in database, error is {}".format(cPayload[1], e))  


        elif cTopic[1] == "Gateway":      # Data message passed on by gateway, data in CSV format
          
          cPayload = sPayload.split(",")   # the payload should be CSV
          try:
            node = Node.objects.get(nodeID = cPayload[1])   # Lets 
            print("Node {} found".format(node.nodeID))

            if node.messagetype:
              #print("Messagetype found")

              jStr = {}   # create empty dict
              print(cPayload)
              for mItem in node.messagetype.messageitem_set.all():
                #print("  msgItem is {}, value is {}".format(mItem.name, cPayload[mItem.order-1]))
                # some validation here

                if mItem.order > len(cPayload):
                  print("Too many items in message type record for the payload, oder is {}".format(mItem.order))
                  break

                try:
                  if mItem.fieldType == 'I':
                    jStr[mItem.name] = int(cPayload[mItem.order-1])
                  elif mItem.fieldType == 'F':
                    jStr[mItem.name] = float(cPayload[mItem.order-1])
                  else:
                    jStr[mItem.name] = cPayload[mItem.order-1]
                except Exception as e:
                  print(e)

              #print(jStr)
              print("Heres the JSON string {}".format(json.dumps(jStr)))

              if node.thingsboardUpload:
                mRes = publish.single(topic = eTB_topic, payload = json.dumps(jStr), 
                    hostname = eTB_host, port = eTB_port, 
                    auth = {'username':node.thingsboardCred})

          except Exception as e:
            print(e)
            print("Cant find {} in database, error is {}".format(cPayload[1], e))  

        elif cTopic[1] == "Network":      # These are status messages sent by gateways and nodes. Data in JSON format
          x =1
        elif cTopic[1] == "Node":         # These are data messages sent by directly by nodes. Data in JSON format
          #print("NODE type message received, topic: {}, payload: {}".format(msg.topic, sPayload))

          try:
            node = Node.objects.get(nodeID = cTopic[2])
            #print("Node {} found".format(node.nodeID))
            if node.thingsboardUpload and is_json(sPayload):
              #print("Publish to TB")
              if node.locationOverride:
                jStr = json.loads(sPayload)
                jStr['latitude'] = node.latitude
                jStr['longitude'] = node.longitude
                sPayload = json.dumps(jStr)
              publish.single(topic = eTB_topic, payload = sPayload, 
                    hostname = eTB_host, port = eTB_port, 
                    auth = {'username':node.thingsboardCred})
            else:
              print("Data not published for {}".format(node.nodeID))
          except Exception as e:
            print(e)


    else:     # not AKLC, a team subscription
      x = 1


#******************************************************************
def mqtt_updater():
    """ The main program that sends updates to the MQTT system
    """

    print("Start Updater v1.1")

    print(eMqtt_client_id)
    print(eMqtt_host)
    print(eMqtt_port)

    #The mqtt client is initialised
    client = mqtt.Client()

    #functions called by mqtt client
    client.on_connect = mqtt_on_connect
    client.on_message = mqtt_on_message
    print("MQTT env set up done")

    try:

      # set up the MQTT environment
        client.username_pw_set(eMqtt_user, eMqtt_password)
        client.connect(eMqtt_host, int(eMqtt_port), 60)
    except Exception as e:
        print(e)

    # used to manage mqtt subscriptions
    client.loop_start()


    #get any pickled stats update data
    try:
        statsPfile = open("stats.pkl", 'rb')
        stats_data = pickle.load(statsPfile)
        print("Pickled statsn read")
        statsPfile.close()
    except:
        print("Stats pickle file not found")
        # not found, set last date in the past so we get an update now
        stats_data = {"LastStats": datetime.datetime.now() + datetime.timedelta(days = -3)}

    #InClient = InfluxDBClient(host='influxdb', port=8086, username='aklciot', password='iotiscool', database='aklc')
    InClient = InfluxDBClient(host=eInflux_host, port=eInflux_port, username=eInflux_user, password=eInflux_pw, database=eInflux_db)
    print("Influx connection details - host: {}, port: {}, user: {}, password: {}, database: {}".format(eInflux_host, 
        eInflux_port, eInflux_user, eInflux_pw, eInflux_db))
    aDb = InClient.get_list_database()
    print(aDb)
    InClient.switch_database('aklc')


    while True:
      time.sleep(1)

      #check if we need to send stats
      tDate = timezone.make_aware(datetime.datetime.now(), timezone.get_current_timezone())

      if (stats_data["LastStats"].day == tDate.day) and (stats_data["LastStats"].hour == tDate.hour):
        #print("No need to send updates")
        x = 1
      else:
        print("Time to send radio stats")
        tDate2 = timezone.make_aware(datetime.datetime.now() - datetime.timedelta(minutes=5), timezone.get_current_timezone())
        aStat = NodeMsgStats.objects.all().filter(dt = tDate, hr = tDate.hour)

        #aStats = NodeMsgStats.objects.all().filter()
        radioTot = 0
        radioNodes = 0
        for s in aStat:
          json_body = [
            {
            "measurement": "radio_stats",
            "tags": {
              "nodeID": s.node.nodeID,
             },
            "fields": {
                "radioCount": s.msgCount,
              },
            }
          ]
          print(json_body)
          InClient.write_points(json_body)
          radioTot = radioTot + s.msgCount
          radioNodes = radioNodes + 1

        # Now send totals
        json_body = [
          {
           "measurement": "radio_stats",
           "tags": {
            "nodeID": "AllNodes",
           },
            "fields": {
              "radioCount": radioTot,
              "radioNodes": radioNodes,
            },
          }
        ]
        # Write the totals
        InClient.write_points(json_body)

        # Save the time we sent to stats
        stats_data["LastStats"] = tDate
        try:
          statsPfile = open("stats.pkl", 'wb')
          pickle.dump(stats_data, statsPfile)
          statsPfile.close()
        except Exception as e:
          print(e)
          print("Stats Pickle failed")



#********************************************************************
if __name__ == "__main__":
    mqtt_updater()
