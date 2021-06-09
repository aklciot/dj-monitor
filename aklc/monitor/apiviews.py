from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import Http404, HttpResponse, HttpResponseRedirect
from rest_framework.views import APIView
from django.urls import reverse

from .models import Team, Node, MessageType, MessageItem
from .serializers import (
    TeamSerializer,
    TeamSerializerDetail,
    NodeSerializer,
    NodeDetailSerializer,
    MessageTypeSerializer,
    MessageTypeSerializerDetail,
)


@api_view(["GET", "POST"])
def team_list(request):

    """
    List all Teams
    """
    if request.user.is_staff:
        if request.method == "GET":
            teams = Team.objects.all()
            serializer = TeamSerializer(teams, many=True)
            return Response(serializer.data)

        elif request.method == "POST":
            serializer = TeamSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    return HttpResponseRedirect(reverse("monitor:login"))


@api_view(["GET"])
def api_team_view(request, team_ref):
    """
    List a teams details
    """
    if request.user.is_staff:
        if request.method == "GET":
            team = Team.objects.filter(id=team_ref)
            # team = Team.objects.all()
            serializer = TeamSerializerDetail(team, many=True)
            return Response(serializer.data)

        elif request.method == "POST":
            serializer = TeamSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    return HttpResponseRedirect(reverse("monitor:login"))

"""
@api_view(["GET"])
def api_team_view(request, team_ref):
   
    if request.user.is_staff:
        if request.method == "GET":
            team = Team.objects.filter(id=team_ref)
            # team = Team.objects.all()
            serializer = TeamSerializerDetail(team, many=True)
            return Response(serializer.data)

        elif request.method == "POST":
            serializer = TeamSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    return HttpResponseRedirect(reverse("monitor:login"))
"""

@api_view(["GET"])
def api_node_view(request, node_ref):
    """
    List a nodes details
    """
    if request.user.is_staff:
        if request.method == "GET":
            node = Node.objects.filter(id=node_ref)
            serializer = NodeDetailSerializer(node, many=True)
            return Response(serializer.data)

        elif request.method == "POST":
            serializer = NodeDetailSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    return HttpResponseRedirect(reverse("monitor:login"))


@api_view(["GET"])
def message_list(request):
    """
    List all Teams
    """
    if request.user.is_staff:
        if request.method == "GET":
            msgs = MessageType.objects.all()
            serializer = MessageTypeSerializer(msgs, many=True)
            return Response(serializer.data)

    return HttpResponseRedirect(reverse("monitor:login"))


@api_view(["GET"])
def message_detail(request, msgtype_ref):
    """
    List all Teams
    """
    if request.user.is_staff:
        if request.method == "GET":
            msg = MessageType.objects.filter(id=msgtype_ref)
            serializer = MessageTypeSerializerDetail(msg, many=True)
            return Response(serializer.data)

    return HttpResponseRedirect(reverse("monitor:login"))

