# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User
from django.views import generic
from django.contrib.auth.decorators import login_required
from django.urls import reverse

# Create your views here.
from django.http import HttpResponse, HttpResponseRedirect

from .models import Node, NodeUser
from .forms import NodeDetailForm, NodeNotifyForm

class IndexView(generic.ListView):
    template_name = "monitor/index.html"
    context_object_name = "nodeList"
    
    def get_queryset(self):
        return Node.objects.order_by('nodeID')
    
def index(request):
    nodeList = Node.objects.order_by('nodeID')
    context = {'nodeList': nodeList}
    return render(request, 'monitor/index.html', context)

@login_required
def nodeDetail(request, node_ref):
    node = Node.objects.get(id = node_ref)
    context = {'node': node, 'user': request.user}
    return render(request, 'monitor/nodeDetail.html', context)

@login_required
def nodeUpdate(request, node_ref):
    node = get_object_or_404(Node, pk=node_ref)
    if request.method == 'POST':
        nf = NodeDetailForm(request.POST, instance=node)
        if nf.is_valid():
            nf.save()
            return HttpResponseRedirect(reverse('monitor:nodeDetail', args=[node.id]))
     # if a GET (or any other method) we'll create a blank form
    else:
        nf = NodeDetailForm(instance=node)
    context = {'form': nf, 'node': node}
    return render(request, 'monitor/nodeUpdate.html', context)

@login_required
def nodeModNotify(request, node_ref):
    node = get_object_or_404(Node, pk=node_ref)
    nu, created = NodeUser.objects.get_or_create(nodeID = node, username = request.user)
    if request.method == 'POST':
        nf = NodeNotifyForm(request.POST)
        if nf.is_valid():
            print("Get or create")
            
            if nf.cleaned_data['notification'] == 'N':
                nu.delete()
            else:
                if nf.cleaned_data['sms'] or nf.cleaned_data['email']:
                    nu.sms = nf.cleaned_data['sms']
                    nu.email = nf.cleaned_data['email']
                    nu.save()
                else:
                    nu.delete()
        return HttpResponseRedirect(reverse('monitor:nodeDetail', args=[node.id]))
    # if a GET (or any other method) we'll create a blank form
    else:
        nf = NodeNotifyForm({'email': nu.email, 'sms': nu.sms, 'notification': 'Y'})

    context = {'form': nf, 'node': node}
    return render(request, 'monitor/nodeModNotify.html', context)

def tb1(request, node_ref):
    node = Node.objects.get(id = node_ref)
    context = {'node': node}
    return render(request, 'monitor/tb1.html', context)

def tb2(request, node_ref):
    node = Node.objects.get(id = node_ref)
    context = {'node': node}
    return render(request, 'monitor/tb2.html', context)
        