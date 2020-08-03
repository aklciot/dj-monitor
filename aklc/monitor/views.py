# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User
from django.views import generic
from django.contrib.auth.decorators import login_required
from django.urls import reverse

# Create your views here.
from django.http import HttpResponse, HttpResponseRedirect

from .models import Node, NodeUser, MessageType, MessageItem, Team
from .forms import (
    NodeDetailForm,
    NodeNotifyForm,
    MessageTypeDetailForm,
    MessageItemDetailForm,
    NodeMessageForm,
    ProjectDetailForm,
    ProjectAddForm,
)
from django.forms import modelformset_factory


# class IndexView(generic.ListView):
#    template_name = "monitor/index.html"
#    context_object_name = "nodeList"
#
#    def get_queryset(self):
#        return Node.objects.order_by("nodeID").exclude(status="M")


def index(request):
    """
    View that displays all current nodes.
    """
    # get all the nodes
    nodeList = Node.objects.order_by("nodeID").exclude(status="M")
    # remove any Gateways
    nodeList = nodeList.exclude(isGateway=True)

    nodeByTeam = Node.objects.order_by("team", "nodeID").exclude(status="M")
    nodeByTeam = nodeByTeam.exclude(isGateway=True)
    nodeByTeam = nodeByTeam.exclude(isRepeater=True)
    noTeamNode = nodeByTeam.exclude(team__isnull=True)
    nodeBlock = []
    teamDict = {"Name": nodeByTeam[0].team.teamID, "teamBlock": []}
    # print(nodeDict)
    tTeam = nodeByTeam[0].team
    # teamBlock = []
    innerBlock = []
    nCnt = 0

    for n in nodeByTeam:

        if n.team != tTeam:  # change teams
            print(f"Team change, now {n.team}")
            teamDict["teamBlock"].append(innerBlock)
            nodeBlock.append(teamDict)
            if not n.team:
                print(f"Break at {n.nodeID}")
                break

            # set up for next team
            teamDict = {"Name": n.team.teamID, "teamBlock": []}
            tTeam = n.team
            nCnt = 0
            innerBlock = []
            teamBlock = []

        if nCnt > 5:
            nCnt = 0
            teamDict["teamBlock"].append(innerBlock)
            innerBlock = []

        innerBlock.append(n)
        nCnt += 1

    # Now do those with no team assigned
    teamDict = {"Name": "No project", "teamBlock": []}
    print("Process no team")
    innerBlock = []
    nCnt = 0
    # teamBlock = []
    for n in nodeByTeam:
        if not n.team:
            print(n.nodeID)
            innerBlock.append(n)
            nCnt += 1
        if nCnt > 5:
            nCnt = 0
            teamDict["teamBlock"].append(innerBlock)
            innerBlock = []
    if len(innerBlock) > 0:
        teamDict["teamBlock"].append(innerBlock)
    nodeBlock.append(teamDict)

    print(nodeBlock)

    context = {"nodeList": nodeList, "nodeactive": "Y", "nodeBlock": nodeBlock}
    # context = {"nodeList": nodeList, "nodeactive": "Y"}
    if request.user.groups.filter(name="BetaTesters").exists():
        return render(request, "monitor/index2.html", context)
    else:
        return render(request, "monitor/index.html", context)


def index_gw(request):
    """
    View for Gateways.
    """
    nodeList = Node.objects.order_by("nodeID").exclude(status="M")
    # Remove anything that is not a gateway
    nodeList = nodeList.exclude(isGateway=False)
    gw_block = []  # will be a list of lists
    nCnt = 1
    innerList = []
    for g in nodeList:  # cycle through the gateways
        innerList.append(g)
        nCnt += 1
        if nCnt > 6:
            gw_block.append(innerList)
            nCnt = 1
            innerList = []
    
    if len(innerList) > 0:
        gw_block.append(innerList)

    context = {"nodeList": nodeList, "gatewayactive": "Y", "gw_block": gw_block}
    if request.user.groups.filter(name="BetaTesters").exists():
        return render(request, "monitor/index_gw2.html", context)
    else:
        return render(request, "monitor/index_gw.html", context)

def index_rp(request):
    """
    View for repeaters.
    """
    nodeList = Node.objects.order_by("nodeID").exclude(status="M")
    # Remove anything that is not a repeater
    nodeList = nodeList.exclude(isRepeater=False)
    print(f"There are {len(nodeList)} repeaters")
    rp_block = []  # will be a list of lists
    nCnt = 1
    innerList = []
    for g in nodeList:  # cycle through the gateways
        innerList.append(g)
        nCnt += 1
        if nCnt > 6:
            rp_block.append(innerList)
            nCnt = 1
            innerList = []
    
    if len(innerList) > 0:
        rp_block.append(innerList)

    context = {"repeaterList": rp_block, "repeateractive": "Y"}
    return render(request, "monitor/index_rp.html", context)


@login_required
def index_msg(request):
    """
    View for message types.
    """
    msgList = MessageType.objects.order_by("msgName")
    context = {"msgList": msgList, "msgactive": "Y"}
    return render(request, "monitor/index_msg.html", context)


@login_required
def index_prj(request):
    """
    View for projects.
    """
    prjList = Team.objects.order_by("teamID")
    context = {"prjList": prjList, "prjactive": "Y"}
    return render(request, "monitor/index_prj.html", context)


@login_required
def nodeDetail(request, node_ref):
    """
    View to display details of a node
    """
    node = get_object_or_404(Node, pk=node_ref)
    passList = node.passOnData()  # gateways that have processed msg from this node
    aNodeUsers = NodeUser.objects.filter(
        nodeID=node
    )  # users that have an 'interest' in this node
    context = {
        "node": node,
        "user": request.user,
        "aNodeUser": aNodeUsers,
        "passData": passList,
        "nodeactive": "Y",
    }
    return render(request, "monitor/nodeDetail.html", context)


@login_required
def gatewayDetail(request, gateway_ref):
    """
    View to display Gateway details
    """
    gw = get_object_or_404(Node, pk=gateway_ref)
    aNodeUsers = NodeUser.objects.filter(
        nodeID=gw
    )  # users that have an 'interest' in this gateway
    passList = gw.passOnData()  # nodes that have been processed by this gateway
    context = {
        "gateway": gw,
        "user": request.user,
        "aNodeUser": aNodeUsers,
        "passData": passList,
        "gatewayactive": "Y",
    }
    return render(request, "monitor/gatewayDetail.html", context)

@login_required
def repeaterDetail(request, rp_ref):
    """
    View to display Repeater details
    """
    rp = get_object_or_404(Node, pk=rp_ref)
    aNodeUsers = NodeUser.objects.filter(
        nodeID=rp
    )  # users that have an 'interest' in this gateway
    passList = rp.passOnData()  # nodes that have been processed by this repeater
    context = {
        "node": rp,
        "user": request.user,
        "aNodeUser": aNodeUsers,
        "passData": passList,
        "repeateractive": "Y",
    }
    return render(request, "monitor/repeaterDetail.html", context)


@login_required
def nodeUpdate(request, node_ref):
    """
    View to process info update form from nodes or gateways
    """
    node = get_object_or_404(Node, pk=node_ref)
    if request.method == "POST":

        nf = NodeDetailForm(
            request.POST, instance=node
        )  # NodeDetailForm defines in forms.py
        if nf.is_valid():
            nf.save()
            return HttpResponseRedirect(reverse("monitor:nodeDetail", args=[node.id]))
        else:
            print("Invalid form")
    # if a GET (or any other method) we'll create a blank form
    else:
        nf = NodeDetailForm(instance=node)
    context = {"form": nf, "node": node}
    2
    if node.isGateway:
        context["gatewayactive"] = "Y"
    else:
        context["nodeactive"] = "Y"
    return render(request, "monitor/nodeUpdate.html", context)

@login_required
def repeaterUpdate(request, node_ref):
    """
    View to process info update form from nodes or gateways
    """
    node = get_object_or_404(Node, pk=node_ref)
    if request.method == "POST":

        nf = NodeDetailForm(
            request.POST, instance=node
        )  # NodeDetailForm defines in forms.py
        if nf.is_valid():
            nf.save()
            return HttpResponseRedirect(reverse("monitor:nodeDetail", args=[node.id]))
        else:
            print("Invalid form")
    # if a GET (or any other method) we'll create a blank form
    else:
        nf = NodeDetailForm(instance=node)
    context = {"form": nf, "node": node}
    2
    if node.isGateway:
        context["gatewayactive"] = "Y"
    else:
        context["nodeactive"] = "Y"
    return render(request, "monitor/nodeUpdate.html", context)


@login_required
def nodeModNotify(request, node_ref):
    """
    View to process the form that manages peoples notification preferences for a specific node
    """
    node = get_object_or_404(Node, pk=node_ref)
    nu, created = NodeUser.objects.get_or_create(nodeID=node, user=request.user)

    if request.method == "POST":
        nf = NodeNotifyForm(request.POST)
        if nf.is_valid():
            # print("Get or create")

            if nf.cleaned_data["notification"] == "N":
                nu.delete()
            else:
                if nf.cleaned_data["sms"] or nf.cleaned_data["email"]:
                    nu.sms = nf.cleaned_data["sms"]
                    nu.email = nf.cleaned_data["email"]
                    nu.save()
                else:
                    nu.delete()
        return HttpResponseRedirect(reverse("monitor:nodeDetail", args=[node.id]))
    # if a GET (or any other method) we'll create a blank form
    else:
        nf = NodeNotifyForm({"email": nu.email, "sms": nu.sms, "notification": "Y"})

    context = {"form": nf, "node": node}
    if node.isGateway:
        context["gatewayactive"] = "Y"
    else:
        context["nodeactive"] = "Y"
    return render(request, "monitor/nodeModNotify.html", context)


@login_required
def nodeMsgUpdate(request, node_ref):
    node = get_object_or_404(Node, pk=node_ref)
    print("BP1")
    if request.method == "POST":
        print("Post message received")
        nf = NodeMessageForm(request.POST, instance=node)
        if nf.is_valid():
            print("Valid BK 1")
            nf.save()

            return HttpResponseRedirect(reverse("monitor:nodeDetail", args=[node.id]))
    # if a GET (or any other method) we'll create a blank form
    else:
        nf = NodeMessageForm(instance=node)

    context = {"form": nf, "node": node}
    if node.isGateway:
        context["gatewayactive"] = "Y"
    else:
        context["nodeactive"] = "Y"
    return render(request, "monitor/nodeMsgUpdate.html", context)


@login_required
def nodeRemove(request, node_ref):
    node = get_object_or_404(Node, pk=node_ref)
    if request.method == "POST":
        removeMe = "N"
        try:
            removeMe = request.POST["remove"]
        except:
            return HttpResponseRedirect(reverse("monitor:nodeDetail", args=[node.id]))
        if removeMe == "Y":
            node.status = "M"
            node.save()
            return HttpResponseRedirect(reverse("monitor:index"))
    context = {"node": node}
    if node.isGateway:
        context["gatewayactive"] = "Y"
    else:
        context["nodeactive"] = "Y"
    return render(request, "monitor/nodeRemove.html", context)


def tb1(request, node_ref):
    node = Node.objects.get(id=node_ref)
    context = {"node": node}
    return render(request, "monitor/tb1.html", context)


def tb2(request, node_ref):
    node = Node.objects.get(id=node_ref)
    context = {"node": node}
    return render(request, "monitor/tb2.html", context)


@login_required
def msgDetail(request, msg_ref):
    msg = get_object_or_404(MessageType, pk=msg_ref)
    msgItems = msg.messageitem_set.all()
    msgNodes = msg.node_set.all()
    context = {"msg": msg, "msgItems": msgItems, "msgNodes": msgNodes}
    context["msgactive"] = "Y"
    return render(request, "monitor/msgDetail.html", context)


@login_required
def msgUpdate(request, msg_ref):
    msg = get_object_or_404(MessageType, pk=msg_ref)

    MsgItemFormSet = modelformset_factory(
        MessageItem, form=MessageItemDetailForm, extra=1, can_delete=True
    )

    if request.method == "POST":
        nf = MessageTypeDetailForm(request.POST, instance=msg)
        fItems = MsgItemFormSet(
            request.POST,
            queryset=msg.messageitem_set.all(),
            prefix="ITEMS",
            initial=[{"msgID": msg}],
        )
        if nf.is_valid() and fItems.is_valid():
            nf.save()

            for i in fItems:
                if i.is_valid() and i.cleaned_data:
                    i.instance.msgID = msg
                    # print(i.__dict__)
                    # print("Order is {}".format(i.cleaned_data))
                    if i.cleaned_data["DELETE"]:
                        # print("Delete this record")
                        i.instance.delete()
                    else:
                        i.save()

                else:
                    print("{} is NOT OK".format(i))
            return HttpResponseRedirect(reverse("monitor:msgDetail", args=[msg.id]))
    # if a GET (or any other method) we'll create a blank form
    else:
        nf = MessageTypeDetailForm(instance=msg)
        fItems = MsgItemFormSet(
            queryset=msg.messageitem_set.all(), prefix="ITEMS", initial=[{"msgID": msg}]
        )
    context = {"form": nf, "msg": msg, "fItems": fItems}

    context["msgactive"] = "Y"
    return render(request, "monitor/msgUpdate.html", context)


@login_required
def msgAdd(request):

    MsgItemFormSet = modelformset_factory(
        MessageItem, form=MessageItemDetailForm, extra=2
    )

    if request.method == "POST":
        nf = MessageTypeDetailForm(request.POST,)
        fItems = MsgItemFormSet(request.POST, queryset=MessageItem.objects.none())
        if nf.is_valid() and fItems.is_valid():
            nf.save()

            for i in fItems:
                if i.is_valid() and i.cleaned_data:
                    i.instance.msgID = nf.instance
                    # print(i.__dict__)
                    # print("Order is {}".format(i.cleaned_data))
                    i.save()

                else:
                    print("{} is NOT OK".format(i))
            return HttpResponseRedirect(
                reverse("monitor:msgDetail", args=[nf.instance.id])
            )
    # if a GET (or any other method) we'll create a blank form
    else:
        nf = MessageTypeDetailForm()
        fItems = MsgItemFormSet(queryset=MessageItem.objects.none())
    context = {"form": nf, "fItems": fItems}

    context["msgactive"] = "Y"
    return render(request, "monitor/msgAdd.html", context)


@login_required
def projectDetail(request, prj_ref):
    prj = get_object_or_404(Team, pk=prj_ref)
    prjNodes = prj.node_set.all()
    context = {"prj": prj, "prjNodes": prjNodes}
    context["prjactive"] = "Y"
    return render(request, "monitor/projectDetail.html", context)


@login_required
def projectUpdate(request, prj_ref):
    prj = get_object_or_404(Team, pk=prj_ref)
    # print("BP1")
    if request.method == "POST":
        print("Post message received")
        nf = ProjectDetailForm(request.POST, instance=prj)
        if nf.is_valid():
            print("Valid BK 1")
            nf.save()

            return HttpResponseRedirect(
                reverse("monitor:projectDetail", args=[prj_ref])
            )
    # if a GET (or any other method) we'll create a blank form
    else:
        nf = ProjectDetailForm(instance=prj)

    context = {"form": nf, "prj": prj}
    context["prjactive"] = "Y"
    print(context)
    return render(request, "monitor/projectUpdate.html", context)


@login_required
def projectAdd(request):
    # prj = get_object_or_404(Team, pk=prj_ref)
    print("BP1")
    if request.method == "POST":
        print("Post message received")
        nf = ProjectAddForm(request.POST)
        if nf.is_valid():
            print("Valid BK 1")
            prj = Team(teamID=nf.cleaned_data["teamID"], descr=nf.cleaned_data["descr"])
            prj.save()

            return HttpResponseRedirect(reverse("monitor:projectDetail", args=[prj.id]))
    # if a GET (or any other method) we'll create a blank form
    else:
        print("BP2")
        nf = ProjectAddForm()

    context = {"form": nf}
    context["prjactive"] = "Y"
    return render(request, "monitor/projectAdd.html", context)


def dashBoard(request):
    return render(request, "monitor/NetworkStatusPage.html")
