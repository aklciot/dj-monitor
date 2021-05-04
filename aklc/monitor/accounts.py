from __future__ import unicode_literals

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.views import generic
from django.contrib.auth.decorators import login_required, permission_required
from django.urls import reverse
from django.utils import timezone
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import auth, messages

import datetime, os

#from .models import Node, NodeUser, MessageType, MessageItem, Team, MqttQueue, MqttStore

#from .forms import (
#    NodeDetailForm,
#    NodeNotifyForm,
#    MessageTypeDetailForm,
#    MessageItemDetailForm,
#    NodeMessageForm,
#    ProjectDetailForm,
#    ProjectAddForm,
#)

from django.forms import modelformset_factory
# Create your views here.

def login(request):
    if request.user.is_authenticated:
        return redirect("monitor:index")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = auth.authenticate(username=username, password=password)

        if user is not None:
            # correct username and password login the user
            auth.login(request, user)
            return redirect("monitor:index")

        else:
            messages.error(request, "Error wrong username/password")

    return render(request, "accounts/login.html")

def logout(request):
    auth.logout(request)
    return render(request, "accounts/logout.html")
