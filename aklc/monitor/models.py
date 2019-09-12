from __future__ import unicode_literals
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import datetime
from django.utils import timezone

# Create your models here.
class Team(models.Model):
    teamID = models.CharField(max_length=50)
    descr = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.teamID


class Node(models.Model):
    nodeID = models.CharField(max_length=30)
    lastseen = models.DateTimeField(blank=True, null=True)
    cameOnline = models.DateTimeField(blank=True, null=True)
    status_sent = models.DateTimeField(null=True, blank=True)
    isGateway = models.BooleanField(blank=True, default=False)
    notification_sent = models.BooleanField(default=False)
    status = models.CharField(max_length=1, default=" ", help_text="C is current, X is down, M in maintenance mode")
    textStatus = models.CharField(max_length=10, blank=True, null=True)
    nextUpdate = models.DateTimeField(blank=True, null=True)
    topic = models.CharField(max_length=50, blank=True, null=True)
    descr = models.TextField(blank=True, null=True, help_text="")
    lastData = models.TextField(blank=True, null=True)
    lastStatus = models.TextField(blank=True, null=True)
    allowedDowntime = models.IntegerField(default=60, help_text="Minutes that the node can be 'unheard' before being marked as Offline")
    hardware = models.CharField(max_length=50, blank=True, null=True)
    software = models.CharField(max_length=50, blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude  = models.FloatField(blank=True, null=True)
    battName = models.CharField(max_length=40, blank=True, null=True, help_text="The attribute name in JSON messages used for battery levels")
    battMonitor = models.BooleanField(default=False)
    battLevel = models.FloatField(default = 0.0)
    battWarn = models.FloatField(default = 0.0, help_text="The battery level, below which warning message are generated")
    battCritical = models.FloatField(default = 0.0, help_text="The battery level, below which critical warning message are generated")
    RSSI = models.FloatField(default = 0.0)
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True)
    portal = models.URLField(max_length=100, blank=True, null=True, help_text="A link where more data on this node is available")

    def __str__(self):
        return self.nodeID

    def passOnData(self):
        """
        This function returns data about items that have processed data, 
        Gateways, the nodes they have processed data
        Nodes, the gateways they have used
        """
        if self.isGateway:
            passAll = NodeGateway.objects.filter(gatewayID = self)
        else:
            passAll = NodeGateway.objects.filter(nodeID = self)
        passAll = passAll.filter(lastdata__gte=(timezone.make_aware(datetime.datetime.now(), timezone.get_current_timezone()) - datetime.timedelta(days=7)))
        return(passAll)

    def msgReceived(self):
        """
        This function updates data when a new message is received
        """
        self.lastseen = timezone.make_aware(datetime.datetime.now(), timezone.get_current_timezone())
        if self.status != "C":
            self.textStatus = "Online"
            self.status = "C"
            self.cameOnline = timezone.make_aware(datetime.datetime.now(), timezone.get_current_timezone())
        return()

    
class NodeUser(models.Model):
    nodeID = models.ForeignKey(Node, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    email = models.BooleanField(blank=True, default=False)
    sms  = models.BooleanField(blank=True, default=False)
    lastemail = models.DateTimeField(blank=True, null=True)
    lastsms = models.DateTimeField(blank=True, null=True)
    smsSent = models.BooleanField(blank=True, default=False)
        
    def __str__(self):
        return("{}: {}".format(self.nodeID, self.user.username))

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phoneNumber = models.CharField(max_length=50, blank=True, null=True)
    reportType = models.CharField(max_length=1, blank=True, null=True, default='S')

    def __str__(self):
        return self.user.username


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
	if created:
		Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
	instance.profile.save()

class NodeGateway(models.Model):
    nodeID = models.ForeignKey(Node, on_delete=models.CASCADE)
    gatewayID = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="gateway",)
    lastdata = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return("Node : {}, Gateway : {}".format(self.nodeID, self.gatewayID))