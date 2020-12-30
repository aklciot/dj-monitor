# dj-monitor
The IoT monitoring system consists of 3 components configured to run in docker containers.
#### Postgres database
The database is used to maintain a persistent record of nodes operating and reporting through the MQTT broker
#### Web system
The web system is how users an interact with node/gateway data. Some basic data about the nodes can be saved and latest data received is also available. This is a standard [django](https://www.djangoproject.com/) system. 
#### Monitor-script
The monitor does a number of functions:
- listens to MQTT queue and updates node info in the database
- sends out sms and email notifications if a node has not been heard from for a while. The delay can be configured by node on the web component
- sends out daily summary reports by email
- purges the database of nodes no longer used.
#### Updater
The updater script listens to the principle MQTT queue and attempts to update node data in both Thingsboard and Influx. In order to do this for data messages send in CSV it looks for message definitions in the postgres database
#### Spy
This script listens to all MQTT queues defined (in the postgres database) and records the last MQTT messages for each node. Using this it is possible to see from the web system which MQTT queues the messages have been published.

## Installation
1. Install docker and docker-compose
2. Clone this repository
3. When the system is run up the first time a bash shell is needed, the wen container is best for this. Then run:
    * python manage.py migrate
    * python manage.py createsuperuser

    
