from django.contrib import admin

# Register your models here.
from .models import (
    Node,
    NodeUser,
    Profile,
    Team,
    NodeGateway,
    MessageType,
    MessageItem,
    NodeMsgStats,
    MqttQueue,
    MqttMessage,
    HtmlTemplate,
)

admin.site.register(Node)
admin.site.register(NodeUser)
admin.site.register(Profile)
admin.site.register(Team)
admin.site.register(NodeGateway)
admin.site.register(MessageType)
admin.site.register(MessageItem)
admin.site.register(NodeMsgStats)
admin.site.register(MqttQueue)
admin.site.register(MqttMessage)
admin.site.register(HtmlTemplate)

