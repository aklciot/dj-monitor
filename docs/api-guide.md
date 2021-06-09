# API Guide

The monitor system exposes some API's which provide access to data stored in the monitor system.

## Access & authentication
The system used basic authentication with the same user name and password used to access details of the system. You do need to request access rights to the API, just email [Jim](mailto:westji@aklc.govt.nz).

## Available API's

* [Teams/project list](#Teams/projects)
* [Team detail](#Team)

Data is available in JSON

### Teams/projects list

Nodes are usually associated with a **Team** or **Project**. 

API URL <https://monitor.innovateauckland.nz/api/teams>

```
[
    {
        "id": 4,
        "teamID": "AIMS",
        "descr": ""
    },
]
```
The 'id' is the identifier and needs to be used at access team/project details including associated nodes.

### Team detail API

This will provide basic data on a team/project, but will also provide basic data on all nodes associated with the team.

API URL <https://monitor.innovateauckland.nz/api/teamdetail/team_id>. The team_id is the ID shown in the Team list API [above](#Teams/projects)

```
{
        "id": 8,
        "teamID": "AIR",
        "descr": "",
        "nodes": [
            {
                "id": 32,
                "nodeID": "Air201",
                "lastseen": "2020-12-04T09:33:24.446975+13:00",
                "isGateway": false,
                "isRepeater": false,
                "descr": "",
                "textStatus": "Missing"
            },
            {
                "id": 33,
                "nodeID": "Air202",
                "lastseen": "2020-12-04T09:33:39.299881+13:00",
                "isGateway": false,
                "isRepeater": false,
                "descr": "",
                "textStatus": "Missing"
            },
        ]
    }
]
```
The "id" for each node can be used to access further data from the [node detail API](#node)

### Node detail API

This will provide full data on a node.

API URL <https://monitor.innovateauckland.nz/api/nodedetail/node_id>. The node_id is the ID for a node shown in the Team detail API [above](#Teams)

```
[
    {
        "id": 13,
        "nodeID": "TTGWCX",
        "descr": null,
        "lastseen": "2020-12-04T09:38:03.321726+13:00",
        "isGateway": true,
        "isRepeater": false,
        "hardware": null,
        "software": null,
        "textStatus": "Missing",
        "bootTime": "2020-11-15T04:36:03.322053+13:00",
        "onlineTime": 0.0,
        "cameOnline": "2020-12-04T08:57:28.777872+13:00",
        "battName": null,
        "battLevel": 0.0,
        "battWarn": 0.0,
        "battCritical": 0.0,
        "latitude": -36.850178,
        "longitude": 174.733005,
        "locationOverride": false,
        "messagetype": null,
        "thingsboardUpload": false,
        "thingsboardCred": null,
        "influxUpload": false,
        "RSSI": 0.0,
        "lastJSON": null,
        "lastData": "TTGWCX,Air203,20.0,60.0,11758.0,6423.0,4.3,-109,-36.83,174.83,Bayfield",
        "lastDataTime": "2020-12-04T09:33:39.412977+13:00",
        "lastStatus": "{\n    \"Gateway\": \"TTGWCX\",\n    \"Status\": \"OK\",\n    \"Version\": \"2.3.5\",\n    \"Type\": \"TTV1\",\n    \"Uptime\": 27662,\n    \"Latitude\": -36.850178,\n    \"Longitude\": 174.733005,\n    \"Project\": \"Bayfield\",\n    \"location\": \"Coxs Bay\"\n}",
        "lastStatusTime": "2020-12-04T09:38:03.321939+13:00"
    }
]
```

