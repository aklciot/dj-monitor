from django.contrib import admin

# Register your models here.
from .models import Node, NodeUser, Profile, Team, NodeGateway, MessageType, MessageItem

admin.site.register(Node)
admin.site.register(NodeUser)
admin.site.register(Profile)
admin.site.register(Team)
admin.site.register(NodeGateway)
admin.site.register(MessageType)
admin.site.register(MessageItem)
