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

## Trapnz script
This script is dedicated to updating the TRAP.NZ API with records from appropriate live traps.

#### Using the API
Trap.nz API [documentation](https://api.trap.nz/)

To use the API, first register so you have a username and password. Then ask for a client_id & client_secret, I had to do this via email.

The script first obtains an access token that is used to authenticate API updates. This expires on a regular basis and needs to be refreshed with a refresh token that is provided along with the access token. The script will get a refreshed token 60 secs before te old one expires.

#### Configuring nodes on Monitor (this program)
Data will only be uploaded if:
* The trapNZ flag is set on a node. Click on the node to display, scroll down to the 'Auto Update' section, click on `Auto Update Control` and then ensure that `Upload to TRAP.NZ API` is checked.
* The data to be upload must be published to `EnvironmentalServices` in JSON format. # key fields are:
    * NodeID - must be the name of a node in monitor
    * Event - must be 'T' (trigger) or 'H' (heartbeat)
    * State - must be 'O' (open) or 'C' (closed)

#### Configuring traps on TRAP.NZ
It is necessary to 'link' a trap on TRAP.NZ with the records uploaded by theAPI. TRAP.NZ considers uploaded data as 'sensor' data, so a 'trap'is linked to a 'sensor'.

To do this, in TRAP.NZ, edit the trap in question, click on the 'More' bar and the update 'Sensor' details.
* Sensor provider - this is 'Auckland Council'
* Sensor ID - this is our nodeID

