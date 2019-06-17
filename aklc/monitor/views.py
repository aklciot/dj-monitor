# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from django.contrib.auth.models import User
from django.views import generic

# Create your views here.
from django.http import HttpResponse

from .models import Node, NodeUser

class IndexView(generic.ListView):
    template_name = "monitor/index.html"
    context_object_name = "nodeList"
    
    def get_queryset(self):
        return Node.objects.order_by('nodeID')
    
def index(request):
    nodeList = Node.objects.order_by('nodeID')
    context = {'nodeList': nodeList}
    return render(request, 'monitor/index.html', context)

def nodeDetail(request, node_ref):
    node = Node.objects.get(id = node_ref)
    context = {'node': node, 'user': request.user}
    return render(request, 'monitor/nodeDetail.html', context)

def nodeUpdate(request, node_ref):
    node = Node.objects.get(id = node_ref)
    context = {'node': node, 'user': request.user}
    return render(request, 'monitor/nodeUpdate.html', context)

def tb1(request, node_ref):
    node = Node.objects.get(id = node_ref)
    context = {'node': node}
    return render(request, 'monitor/tb1.html', context)

def tb2(request, node_ref):
    node = Node.objects.get(id = node_ref)
    context = {'node': node}
    return render(request, 'monitor/tb2.html', context)
        