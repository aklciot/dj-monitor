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
    aTeams = Team.objects.all()
    for t in aTeams:
      sub_topic = t.teamID + "/#"
      print("MQTT Subscribed to {}".format(sub_topic))
      client.subscribe(sub_topic)


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
    cPayload = sPayload.split(",")   # should the payload should be CSV

    # Check for nodes using regular topic structure
    if cTopic[0] == "AKLC":
        #print("Aklc message received, topic {}, payload {}".format(msg.topic, msg.payload))
        # Check types of message from the topic

        if cTopic[1] == "Status":         # Status messages from Gateways, data in CSV format
          #print("AKLC Status message received, payload is {}".format(sPayload))
          
          try:
            node = Node.objects.get(nodeID = cPayload[0])   # Lets 
            #print("Gateway {} found".format(node.nodeID))

            if node.messagetype:
              jOut = csv_to_json(cPayload, node)
              #print("Messagetype found")

              if node.thingsboardUpload:
                #print("Thingsboard upload")
                mRes = publish.single(topic = eTB_topic, payload = json.dumps(jOut['jStr']), 
                    hostname = eTB_host, port = eTB_port, 
                    auth = {'username':node.thingsboardCred})

              if node.influxUpload:
                #print("Influx gateway upload")
                json_body = [
                  {
                    "measurement": "Gateway",
                    "tags": jOut['jTags'],
                    "fields": jOut['jData'],
                  }
                ]

                InClient.write_points(json_body)

          except Exception as e:
            print(e)
            print("Cant find {} in database, error is {}".format(cPayload[1], e))  


        elif cTopic[1] == "Gateway":      # Data message passed on by gateway, data in CSV format
          #print("AKLC Gateway message received, payload is {}".format(sPayload))
          
          try:
            node = Node.objects.get(nodeID = cPayload[1])   # Lets 
            #print("Node {} found".format(node.nodeID))

            if node.messagetype:
              #print("Messagetype found")
              jOut = csv_to_json(cPayload, node)

              if node.influxUpload:
                if node.team:
                  cTeam = node.team.teamID
                else:
                  cTeam = "unknown"
                json_body = [
                  {
                    "measurement": cTeam,
                    "tags": jOut['jTags'],
                    "fields": jOut['jData'],
                  }
                ]

                InClient.write_points(json_body)

              if node.thingsboardUpload:
                #print("Thingsboard upload")
                mRes = publish.single(topic = eTB_topic, payload = json.dumps(jOut['jStr']), 
                    hostname = eTB_host, port = eTB_port, 
                    auth = {'username':node.thingsboardCred})

          except Exception as e:
            print(e)
            print("Cant find {} in database, error is {}".format(cPayload[1], e))  

        #elif cTopic[1] == "Network":      # These are status messages sent by gateways and nodes. Data in JSON format
        #  x =1
        elif cTopic[1] == "Node" or cTopic[1] == "Network":         # These are JSON messages, both data & status
          #print("NODE/NETWORK type message received, topic: {}, payload: {}".format(msg.topic, sPayload))

          if is_json(sPayload):           # these messages should always be JSON
            jStr = json.loads(sPayload)
            # lets find the node name
            if len(cTopic) > 2:
              cNode = cTopic[2]
            elif "Gateway" in jStr:
              cNode = jStr["Gateway"]
            elif "nodeID" in jStr:
              cNode = jStr["Gateway"]
            else:
              print("No node info could be found, ignore message")
              cNode = "XXXXXXXXX"

            try:
              node = Node.objects.get(nodeID = cNode)
              print("Found node {}".format(cNode))
              if node.thingsboardUpload:
                #print("Publish to TB")
                if node.locationOverride:
                  jStr['latitude'] = node.latitude
                  jStr['longitude'] = node.longitude
                  sPayload = json.dumps(jStr)
                publish.single(topic = eTB_topic, payload = sPayload, 
                      hostname = eTB_host, port = eTB_port, 
                      auth = {'username':node.thingsboardCred})

              if node.influxUpload:
                jOut = json_for_influx(sPayload, node)
                if node.team:
                  sMeasure = node.team.teamID
                elif 'project' in sPayload:
                  sMeasure = sPayload['project']
                else:
                  sMeasure = "AKLC"
                json_body = [
                  {
                    "measurement": sMeasure,
                    "tags": jOut['jTags'],
                    "fields": jOut['jData'],
                  }
                ]
                #print("The payload for Influx is {}".format(json_body))
                InClient.write_points(json_body)

            except Exception as e:
              print(e)
          else:
            print("Payload not JSON")


    else:     # not AKLC, a team subscription
      #print("TEAM message received")
      # the payload is expected to be json

      jPayload = json.loads(sPayload)
      #print("Team message arrived, topic is {}, payload is {}".format(msg.topic, sPayload))
      
      if "NodeID" in jPayload:
        #print("The NodeID is {}".format(jPayload["NodeID"]))
        try:
          node = Node.objects.get(nodeID = jPayload["NodeID"])

          jOut = json_for_influx(sPayload, node)
          json_body = [
                  {
                    "measurement": cTopic[0],
                    "tags": jOut['jTags'],
                    "fields": jOut['jData'],
                  }
                ]
          
          InClient.write_points(json_body)
          #print("Influx updated from TEAM message, package is {}".format(json_body))
          
        except Exception as e:
          print("Team error {}".format())
          print(e)
        

#******************************************************************
def json_for_influx(sPayload, nNode):
  """
  Function evaluates a jason input and splits it into tags & fierlds for influx upload
  """
  cTags = ['gateway', 'nodeid', 'location', 'latitude', 'longitude', 'repeater', 'project', 'software', 'version', 'type']
  jTags = {}
  jData = {}

  jPayload = json.loads(sPayload)
  
  #print("json_for_influx entered, payload is {}".format(sPayload))

  for jD in list(jPayload):
    if jD.lower() in cTags:             #Then this must be a tag
      jTags[jD] = jPayload[jD]
    else:
      jData[jD] = jPayload[jD]
  
  #Location correction
  if nNode.locationOverride:
    if 'latitude' in jData:
      jTags['latitude'] = nNode.latitude
    elif 'Latitude' in jData:
      jTags['Latitude'] = nNode.latitude
    elif 'longitude' in jData:
      jTags['longitude'] = nNode.longitude
    elif 'Longitude' in jData:
      jTags['Longitude'] = nNode.longitude
  
  if nNode.projectOverride:
    if 'project' in jData:
      jTags['project'] = nNode.topic
    if 'Project' in jData:
      jTags['Project'] = nNode.topic

  jOutput = {'jTags': jTags, 'jData': jData}
  #print("jTags is {}\njData is {}".format(jOutput['jTags'], jOutput['jData'] ))
  return(jOutput)



#******************************************************************
def csv_to_json(cPayload, nNode):
  """
  Function converts a CSV payload to JSON for thingsboard & Influx based on data in the MesssageType record if it exists
  """
  
  jStr = {}
  jTags = {}
  jData = {}
  
  #print("csv_to_json entered, payload is {}".format(cPayload))
  for mItem in nNode.messagetype.messageitem_set.all():
    #print("  msgItem is {}, value is {}".format(mItem.name, cPayload[mItem.order-1]))
    # some validation here

    if mItem.order > len(cPayload):
      print("Too many items in message type record for the payload, order is {}".format(mItem.order))
      break

    try:
      if mItem.fieldType == 'I':
        val =  int(float(cPayload[mItem.order-1]))
      elif mItem.fieldType == 'F':
        val = float(cPayload[mItem.order-1])
      else:
        val = cPayload[mItem.order-1]
      if nNode.locationOverride:
        if mItem.name == 'latitude' or mItem.name == 'Latitude':
          val = nNode.latitude
        if mItem.name == 'longitude' or mItem.name == 'Longitude':
          val = nNode.longitude
    except Exception as e:
      print(e)

    jStr[mItem.name] = val
    if mItem.isTag:
      jTags[mItem.name] = val
    else:
      jData[mItem.name] = val

  jOutput = {'jStr': jStr, 'jTags': jTags, 'jData': jData}
  #print("jStr is {}\njTags is {}\njData is {}".format(jOutput['jStr'], jOutput['jTags'], jOutput['jData'] ))
  return(jOutput)




#******************************************************************
def mqtt_updater():
    """ The main program that sends updates to the MQTT system
    """
    global InClient

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
        print("Pickled stats read")
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
        print("Time to send radio stats, pickle date is {}, current date is {}".format(stats_data["LastStats"], tDate))
        tDate2 = timezone.make_aware(datetime.datetime.now() - datetime.timedelta(minutes=5), timezone.get_current_timezone())
        aStat = NodeMsgStats.objects.all().filter(dt = tDate2, hr = tDate2.hour)
        print("Date used to get data is {}".format(tDate2))
        #aStats = NodeMsgStats.objects.all().filter()
        radioTot = 0
        radioNodes = 0
        gatewayTot = 0
        radioGw = 0
        #print("Number of stat nodes is {}".format(len(aStat)))
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
          #print(json_body)
          InClient.write_points(json_body)
          if s.node.isGateway:
            gatewayTot = gatewayTot + s.msgCount
            radioGw = radioGw + 1
          else:
            radioTot = radioTot + s.msgCount
            radioNodes = radioNodes + 1
          
          try:
            if s.node.thingsboardUpload:
              print("Send radio stat message to Thingsboard for {}".format(s.node.nodeID))
              jStr = {}   # create empty dict
              jStr['radioCount'] = s.msgCount
              
              print("Heres the JSON string {}".format(json.dumps(jStr)))

              #mRes = publish.single(topic = eTB_topic, payload = json.dumps(jStr), 
              #      hostname = eTB_host, port = eTB_port, 
              #      auth = {'username':s.node.thingsboardCred})
          except Exception as e:
            print(e)
          

        # Now send totals
        print("Send totals now")
        json_body = [
          {
           "measurement": "radio_stats",
           "tags": {
            "nodeID": "AllNodes",
           },
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

        # Save the time we sent to stats
        stats_data["LastStats"] = tDate
        try:
          statsPfile = open("stats.pkl", 'wb')
          pickle.dump(stats_data, statsPfile)
          statsPfile.close()
          print("Write date {} to pickle file".format(tDate))
        except Exception as e:
          print(e)
          print("Stats Pickle failed")



#********************************************************************
if __name__ == "__main__":
    mqtt_updater()
