from django.contrib import admin

# Register your models here.
from .models import Node, NodeUser, Profile

admin.site.register(Node)
admin.site.register(NodeUser)
admin.site.register(Profile)
