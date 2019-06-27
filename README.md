# dj-monitor
The IoT monitoring system consists of 3 components configured to run in docker containers.
#### Postgres database
The database is used to maintain a persistent record of nodes operating and reporting through the MQTT broker
#### Web system
The web system is how users an interact with node/gateway data. Some basic data about the nodes can be saved and latest data received is also available
#### Monitor
The monitor does a number of functions:
- listens to MQTT queue and updates node info in the database
- sends out sms and email notifications if a node has not been heard from for a while. The delay can be configured by node on the web component
- sends out daily summary reports by email
- purges the database of node no longer used.

## Installation
1. Install docker and docker-compose
