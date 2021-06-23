# Backend processes
There are 3 scripts that run continuously to support the monitoring system

## Monitor script
This subscribes to the MQTT queue in use and uses the messages on the queue to update the back end database that the Web component works off.

Functions include:
* Create new record when a new node/repeater/gateway is seen on the queue
* Update data records based on the MQTT messages

## Updater script
This script is used to update Thingsboard and Influx systems, aslso based on data in the MQTT queue

## Spy script
