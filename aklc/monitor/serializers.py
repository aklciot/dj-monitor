from rest_framework import serializers
from monitor.models import Team, Node, MessageItem, MessageType


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ["id", "teamID", "descr"]

class NodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Node
        fields = [
            "id",
            "nodeID",
            "lastseen",
            "isGateway",
            "isRepeater",
            "descr",
            "textStatus",
        ]

class NodeDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Node
        fields = [
            "id",
            "nodeID",
            "descr",
            "lastseen",
            "isGateway",
            "isRepeater",
            "hardware",
            "software",
            "textStatus",
            "bootTime",
            "onlineTime",
            "cameOnline",
            "battName",
            "battLevel",
            "battWarn",
            "battCritical",
            "latitude",
            "longitude",
            "locationOverride",
            "messagetype",
            "thingsboardUpload",
            "thingsboardCred",
            "influxUpload",
            "RSSI",
            "lastJSON",
            "lastData",
            "lastDataTime",
            "lastStatus",
            "lastStatusTime",
        ]


class TeamSerializerDetail(serializers.ModelSerializer):
    nodes = NodeSerializer(many=True, read_only=True)

    class Meta:
        model = Team
        fields = ["id", "teamID", "descr", "nodes"]

class MessageItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageItem
        fields = ["id", "msgID", "name", "order", "fieldType", "isTag"]


class MessageTypeSerializerDetail(serializers.ModelSerializer):
    items = MessageItemSerializer(many=True, read_only=True)

    class Meta:
        model = MessageType
        fields = ["id", "msgName", "descr", "items"]


class MessageTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageType
        fields = ["id", "msgName", "descr"]

