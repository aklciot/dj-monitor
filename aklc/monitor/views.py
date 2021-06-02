# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.views import generic
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import auth, messages
from django.urls import reverse
from django.utils import timezone
import datetime, os

# Create your views here.
from django.http import HttpResponse, HttpResponseRedirect

from .models import (
    Node,
    NodeUser,
    MessageType,
    MessageItem,
    Team,
    MqttQueue,
    MqttStore,
    notificationLog,
    webNotification,
)

from .forms import (
    NodeDetailForm,
    NodeNotifyForm,
    MessageTypeDetailForm,
    MessageItemDetailForm,
    NodeMessageForm,
    ProjectDetailForm,
    ProjectAddForm,
    UserProfileForm,
    PasswordResetForm,
    NodeUserDetailForm,
)

from django.forms import modelformset_factory
from django.contrib.auth.forms import PasswordChangeForm

from .support import sendNotification

testFlag = os.getenv("AKLC_TESTING", False)


def index(request):
    """
    View that displays all current nodes.
    """
    dMonthAgo = timezone.make_aware(
        datetime.datetime.now(), timezone.get_current_timezone()
    ) - datetime.timedelta(days=31)
    # get all the nodes
    nodeList = (
        Node.objects.order_by("nodeID")
        .exclude(status="M")
        .exclude(lastseen__lte=dMonthAgo)
    )
    # remove any Gateways
    nodeList = nodeList.exclude(isGateway=True)

    nodeByTeam = (
        Node.objects.order_by("team", "nodeID")
        .exclude(status="M")
        .exclude(lastseen__lte=dMonthAgo)
    )
    nodeByTeam = nodeByTeam.exclude(isGateway=True).exclude(isRepeater=True)

    noTeamNode = nodeByTeam.exclude(team__isnull=False)

    nodeBlock = []
    if len(nodeByTeam) != len(noTeamNode):
        teamDict = {"Name": nodeByTeam[0].team.teamID, "teamBlock": []}
        tTeam = nodeByTeam[0].team

        # teamBlock = []
        innerBlock = []
        nCnt = 0

        for n in nodeByTeam:

            if n.team != tTeam:  # change teams
                # print(f"Team change, now {n.team}")
                teamDict["teamBlock"].append(innerBlock)
                nodeBlock.append(teamDict)
                if not n.team:
                    # print(f"Break at {n.nodeID}")
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
        else:
            teamDict = {}
    # Now do those with no team assigned
    teamDict = {"Name": "No project", "teamBlock": []}
    # print("Process no team")
    innerBlock = []
    nCnt = 0
    # teamBlock = []
    for n in nodeByTeam:
        if not n.team:
            # print(n.nodeID)
            innerBlock.append(n)
            nCnt += 1
        if nCnt > 5:
            nCnt = 0
            teamDict["teamBlock"].append(innerBlock)
            innerBlock = []
    if len(innerBlock) > 0:
        teamDict["teamBlock"].append(innerBlock)
    nodeBlock.append(teamDict)

    # print(nodeBlock)

    context = {"nodeList": nodeList, "nodeactive": "Y", "nodeBlock": nodeBlock}
    if os.getenv("AKLC_TESTING", False):
        context["dev_msg"] = "(Development)"
    # context = {"nodeList": nodeList, "nodeactive": "Y"}
    if request.user.groups.filter(name="BetaTesters").exists():
        return render(request, "monitor/index2.html", context)
    else:
        return render(request, "monitor/index2.html", context)


def index_gw(request):
    """
    View for Gateways.
    """
    dMonthAgo = timezone.make_aware(
        datetime.datetime.now(), timezone.get_current_timezone()
    ) - datetime.timedelta(days=31)
    nodeList = (
        Node.objects.order_by("nodeID")
        .exclude(status="M")
        .exclude(lastseen__lte=dMonthAgo)
    )
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
    if os.getenv("AKLC_TESTING", False):
        context["dev_msg"] = "(Development)"

    if request.user.groups.filter(name="BetaTesters").exists():
        return render(request, "monitor/index_gw2.html", context)
    else:
        return render(request, "monitor/index_gw2.html", context)


def index_rp(request):
    """
    View for repeaters.
    """
    dMonthAgo = timezone.make_aware(
        datetime.datetime.now(), timezone.get_current_timezone()
    ) - datetime.timedelta(days=31)
    nodeList = (
        Node.objects.order_by("nodeID")
        .exclude(status="M")
        .exclude(lastseen__lte=dMonthAgo)
    )
    # Remove anything that is not a repeater
    nodeList = nodeList.exclude(isRepeater=False)

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
    if os.getenv("AKLC_TESTING", False):
        context["dev_msg"] = "(Development)"

    return render(request, "monitor/index_rp.html", context)


# @login_required
@permission_required("monitor.view_messagetype")
def index_msg(request):
    """
    View for message types.
    """
    msgList = MessageType.objects.order_by("msgName")
    context = {"msgList": msgList, "msgactive": "Y"}
    if testFlag:
        context["dev_msg"] = "(Development)"

    return render(request, "monitor/index_msg.html", context)


@login_required
def index_prj(request):
    """
    View for projects.
    """
    prjList = Team.objects.order_by("teamID")
    context = {"prjList": prjList, "prjactive": "Y"}
    if testFlag:
        context["dev_msg"] = "(Development)"
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
    nLog = notificationLog.objects.filter(node=node)[:50]
    context = {
        "node": node,
        "user": request.user,
        "aNodeUser": aNodeUsers,
        "passData": passList,
        "nodeactive": "Y",
        "nLog": nLog,
    }
    if request.user.is_staff:
        context["staff"] = "Y"
    if testFlag:
        context["dev_msg"] = "(Development)"
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
    nLog = notificationLog.objects.filter(node=gw)[:50]
    context = {
        "gateway": gw,
        "user": request.user,
        "aNodeUser": aNodeUsers,
        "passData": passList,
        "gatewayactive": "Y",
        "nLog": nLog,
    }
    if testFlag:
        context["dev_msg"] = "(Development)"
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
    nLog = notificationLog.objects.filter(node=rp)[:50]
    context = {
        "node": rp,
        "user": request.user,
        "aNodeUser": aNodeUsers,
        "passData": passList,
        "repeateractive": "Y",
        "nLog": nLog,
    }
    if testFlag:
        context["dev_msg"] = "(Development)"
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
    elif node.isRepeater:
        context["repeateractive"] = "Y"
    else:
        context["nodeactive"] = "Y"
    if testFlag:
        context["dev_msg"] = "(Development)"
    return render(request, "monitor/nodeUpdate.html", context)


@login_required
def nodeMqttLog(request, node_ref, mq_ref):
    node = get_object_or_404(Node, pk=node_ref)
    mqttQueue = get_object_or_404(MqttQueue, pk=mq_ref)
    mqMsg = MqttStore.objects.filter(node=node, mqttQueue=mqttQueue)[:50]
    context = {
        "node": node,
        "mqttQueue": mqttQueue,
        "mqMsg": mqMsg,
    }
    if node.isGateway:
        context["gatewayactive"] = "Y"
    elif node.isRepeater:
        context["repeateractive"] = "Y"
    else:
        context["nodeactive"] = "Y"
    return render(request, "monitor/nodeMqttLog.html", context)


@login_required
def gatewayMqttLog(request, gateway_ref, mq_ref):
    gateway = get_object_or_404(Node, pk=gateway_ref)
    mqttQueue = get_object_or_404(MqttQueue, pk=mq_ref)
    mqMsg = MqttStore.objects.filter(gateway=gateway, mqttQueue=mqttQueue)[:50]
    context = {
        "node": gateway,
        "mqttQueue": mqttQueue,
        "mqMsg": mqMsg,
        "gatewayactive": "Y",
    }
    return render(request, "monitor/nodeMqttLog.html", context)


@login_required
def repeaterUpdate(request, rp_ref):
    """
    View to process info update form from nodes or gateways
    """
    node = get_object_or_404(Node, pk=rp_ref)
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

    context["repeateractive"] = "Y"
    if testFlag:
        context["dev_msg"] = "(Development)"
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
        if node.isGateway:
            return HttpResponseRedirect(
                reverse("monitor:gatewayDetail", args=[node.id])
            )
        elif node.isRepeater:
            return HttpResponseRedirect(
                reverse("monitor:repeaterDetail", args=[node.id])
            )
        else:
            return HttpResponseRedirect(reverse("monitor:nodeDetail", args=[node.id]))
    # if a GET (or any other method) we'll create a blank form
    else:
        nf = NodeNotifyForm({"email": nu.email, "sms": nu.sms, "notification": "Y"})

    context = {"form": nf, "node": node}
    # print(f"User is: {request.user.username}, staff status is {request.user.is_staff}")
    if request.user.is_staff:
        context["staff"] = "Y"

    if node.isGateway:
        context["gatewayactive"] = "Y"
    elif node.isRepeater:
        context["repeateractive"] = "Y"
    else:
        context["nodeactive"] = "Y"
    if testFlag:
        context["dev_msg"] = "(Development)"
    return render(request, "monitor/nodeModNotify.html", context)


@login_required
def nodeModNotifyOthers(request, node_ref):
    """
    View to process the form that manages other peoples notification preferences for a specific node
    """
    node = get_object_or_404(Node, pk=node_ref)
    admins = User.objects.filter(is_superuser=True)

    # NodeUserFormSet = modelformset_factory(
    #    NodeUser, form=NodeUserDetailForm, extra=1, can_delete=True
    # )

    NodeUserFormSet = modelformset_factory(
        NodeUser, fields=("user", "sms", "email"), extra=1, can_delete=True
    )

    if request.method == "POST":
        fItems = NodeUserFormSet(
            request.POST,
            queryset=node.nodeuser_set.all().exclude(user=request.user),
            prefix="ITEMS",
        )
        if fItems.is_valid():
            # print("Get or create")

            for i in fItems:
                # print(i.__dict__)
                if i.is_valid() and i.cleaned_data:
                    i.instance.nodeID = node
                    context = {"nu": i.instance}
                    context["formData"] = i.cleaned_data
                    if i.cleaned_data["DELETE"]:
                        sendNotification(
                            admins,
                            inEmail=True,
                            inSubject=f"A notification was deleted from {node.nodeID}",
                            context=context,
                            inTemplate="monitor/email/notifRemove.html",
                            inNode=node,
                        )
                        i.instance.delete()
                    elif i.cleaned_data["sms"] or i.cleaned_data["email"]:
                        nuOld = NodeUser.objects.filter(
                            nodeID=node, user=i.instance.user
                        )
                        if len(nuOld) == 0:
                            context["origSMS"] = "None"
                            context["origEmail"] = "None"
                            sendNotification(
                                admins,
                                inEmail=True,
                                inSubject=f"A notification was added for {node.nodeID}",
                                context=context,
                                inTemplate="monitor/email/notifChange.html",
                                inNode=node,
                            )

                        else:
                            context["origSMS"] = nuOld[0].sms
                            context["origEmail"] = nuOld[0].email
                            if (nuOld[0].sms != i.cleaned_data["sms"]) or (
                                nuOld[0].email != i.cleaned_data["email"]
                            ):
                                sendNotification(
                                    admins,
                                    inEmail=True,
                                    inSubject=f"A notification was changed for {node.nodeID}",
                                    context=context,
                                    inTemplate="monitor/email/notifChange.html",
                                    inNode=node,
                                )
                        i.save()
                    else:  # no choices
                        sendNotification(
                            admins,
                            inEmail=True,
                            inSubject=f"A notification was deleted from {node.nodeID}",
                            context=context,
                            inTemplate="monitor/email/notifRemove.html",
                            inNode=node,
                        )
                        i.instance.delete()
                else:
                    # print(f"{i} is invalid")
                    x = 1

        return HttpResponseRedirect(reverse("monitor:nodeDetail", args=[node.id]))
    # if a GET (or any other method) we'll create a blank form
    else:
        # nf = NodeUserDetailForm(instance=node)
        fItems = NodeUserFormSet(
            queryset=node.nodeuser_set.all().exclude(user=request.user), prefix="ITEMS"
        )

    context = {"node": node, "fItems": fItems}

    if node.isGateway:
        context["gatewayactive"] = "Y"
    elif node.isRepeater:
        context["repeateractive"] = "Y"
    else:
        context["nodeactive"] = "Y"
    if testFlag:
        context["dev_msg"] = "(Development)"
    return render(request, "monitor/nodeModNotifyOthers.html", context)


@login_required
def nodeMsgUpdate(request, node_ref):
    node = get_object_or_404(Node, pk=node_ref)
    if request.method == "POST":
        nf = NodeMessageForm(request.POST, instance=node)
        if nf.is_valid():
            nf.save()

            return HttpResponseRedirect(reverse("monitor:nodeDetail", args=[node.id]))
    # if a GET (or any other method) we'll create a blank form
    else:
        nf = NodeMessageForm(instance=node)

    context = {"form": nf, "node": node}
    if node.isGateway:
        context["gatewayactive"] = "Y"
    elif node.isRepeater:
        context["repeateractive"] = "Y"
    else:
        context["nodeactive"] = "Y"
    if testFlag:
        context["dev_msg"] = "(Development)"
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
    elif node.isRepeater:
        context["repeateractive"] = "Y"
    else:
        context["nodeactive"] = "Y"
    if testFlag:
        context["dev_msg"] = "(Development)"
    return render(request, "monitor/nodeRemove.html", context)


def tb1(request, node_ref):
    node = Node.objects.get(id=node_ref)
    context = {"node": node}
    if testFlag:
        context["dev_msg"] = "(Development)"
    return render(request, "monitor/tb1.html", context)


def tb2(request, node_ref):
    node = Node.objects.get(id=node_ref)
    context = {"node": node}
    if testFlag:
        context["dev_msg"] = "(Development)"
    return render(request, "monitor/tb2.html", context)


@login_required
def msgDetail(request, msg_ref):
    msg = get_object_or_404(MessageType, pk=msg_ref)
    msgItems = msg.messageitem_set.all()
    msgNodes = msg.node_set.all()
    context = {"msg": msg, "msgItems": msgItems, "msgNodes": msgNodes}
    context["msgactive"] = "Y"
    if testFlag:
        context["dev_msg"] = "(Development)"
    return render(request, "monitor/msgDetail.html", context)


@login_required
def msgUpdate(request, msg_ref):
    msg = get_object_or_404(MessageType, pk=msg_ref)

    MsgItemFormSet = modelformset_factory(
        MessageItem, form=MessageItemDetailForm, extra=3, can_delete=True
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
    if testFlag:
        context["dev_msg"] = "(Development)"
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
    if testFlag:
        context["dev_msg"] = "(Development)"
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
        # print("Post message received")
        nf = ProjectDetailForm(request.POST, instance=prj)
        if nf.is_valid():
            # print("Valid BK 1")
            nf.save()

            return HttpResponseRedirect(
                reverse("monitor:projectDetail", args=[prj_ref])
            )
    # if a GET (or any other method) we'll create a blank form
    else:
        nf = ProjectDetailForm(instance=prj)

    context = {"form": nf, "prj": prj}
    context["prjactive"] = "Y"
    # print(context)
    return render(request, "monitor/projectUpdate.html", context)


@login_required
def projectAdd(request):
    # prj = get_object_or_404(Team, pk=prj_ref)

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
        nf = ProjectAddForm()

    context = {"form": nf}
    context["prjactive"] = "Y"
    return render(request, "monitor/projectAdd.html", context)


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


@login_required
def userProfile(request):
    context = {"data": ""}

    return render(request, "monitor/userProfile.html", context)


@login_required
def userUpdate(request):
    user = request.user
    if request.method == "POST":
        nf = UserProfileForm(request.POST)
        if nf.is_valid():
            user.first_name = nf.cleaned_data["firstName"]
            user.last_name = nf.cleaned_data["surName"]
            user.email = nf.cleaned_data["email"]
            user.profile.phoneNumber = nf.cleaned_data["phoneNumber"]
            user.save()

        return HttpResponseRedirect(reverse("monitor:userProfile"))
    # if a GET (or any other method) we'll create a blank form
    else:
        nf = UserProfileForm(
            {
                "firstName": user.first_name,
                "surName": user.last_name,
                "email": user.email,
                "phoneNumber": user.profile.phoneNumber,
            }
        )
    context = {"form": nf}
    if testFlag:
        context["dev_msg"] = "(Development)"
    return render(request, "monitor/userUpdate.html", context)


@login_required
def passwordChange(request):
    if request.method == "POST":
        f = PasswordChangeForm(request.POST)
        if f.is_valid():
            f.save(request)
            # messages.success(request, "Password reset information sent by email")
            return redirect("monitor:passwordChangeDone")
    else:
        f = PasswordResetForm()
    context = {"form": f}
    return render(request, "accounts/password_change.html", context)


def passwordReset(request):
    return


def dashBoard(request):
    return render(request, "monitor/NetworkStatusPage.html")


def about(request):
    return render(request, "monitor/about.html")


def contact(request):
    return render(request, "monitor/contact.html")
