# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse

from .models import Node

def index(request):
    nodeList = Node.objects.order_by('nodeID')
    context = {'nodeList': nodeList}
    return render(request, 'monitor/index.html', context)

def nodeDetail(request, nodeID):
    return HttpResponse("A node page for {}.".format(nodeID))