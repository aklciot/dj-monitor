from __future__ import unicode_literals
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import datetime
from django.utils import timezone
import json

# Create your models here.
class Team(models.Model):
    teamID = models.CharField(max_length=50)
    descr = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Project"
        
    def __str__(self):
        return self.teamID

class MessageType(models.Model):
    msgName = models.CharField(max_length=30)
    descr = models.TextField(blank=True, null=True, help_text="")
            
    class Meta:
        ordering = ["msgName"]
        verbose_name = "Message Type"

    def __str__(self):
        return("{}".format(self.msgName))

class MessageItem(models.Model):
    FIELD_TYPE_CHOICES = [
        ('S', 'String'),
        ('I', 'Integer'),
        ('F', 'Float'),
    ]
    msgID = models.ForeignKey(MessageType, on_delete=models.CASCADE)
    name = models.CharField(max_length=15, help_text="The element name, will be used in JSON messages")
    order = models.IntegerField()
    fieldType = models.CharField(max_length=1, help_text="Field type can be 'S': string, 'I': integer, 'F': float", choices= FIELD_TYPE_CHOICES )
    isTag = models.BooleanField(blank=True, default=False, help_text="Use as a tag when uploading to Influx")
    
    class Meta:
        ordering = ["order"]
        verbose_name = "Message Item"

    def __str__(self):
        return("{}: {}".format(self.msgID.msgName, self.name)) 


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
    #dataMsgCount = models.IntegerField(default=0)
    uptime = models.FloatField(default=0)
    RSSI = models.FloatField(default = 0.0)
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True)
    portal = models.URLField(max_length=100, blank=True, null=True, help_text="A link where more data on this node is available")
    messagetype = models.ForeignKey(MessageType, blank=True, null=True, help_text="This message type will be used to convert incoming CSV data to JSON format", on_delete = models.SET_NULL)
    influxUpload = models.BooleanField("Upload to InfluxDB", default=False, help_text="Select this if you want data uploaded to InfluxDB.")
    thingsboardUpload = models.BooleanField("Upload to Thingsboard", default=False, help_text="Select this if you want data uploaded to Thingsboard on AWS2. NB Thingsboard cred also needs to be completed.")
    locationOverride = models.BooleanField("Location override", default=False, help_text="If selected, incoming location data will be ignored and stored data passed on")
    projectOverride = models.BooleanField("Project override", default=False, help_text="If selected, any incoming Project name will be ignored and stored Project passed on")
    thingsboardCred = models.CharField("Thingsboard credentials", max_length=40, blank=True, null=True, help_text="The credentials needed for thingsboard data load")

    class Meta:
        ordering = ["nodeID"]

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

    def jsonLoad(self, sInput):
        """
        Process as JSON string and updates any relevant node/gateway attributes
        """
        #print("JSON update run")
        jPayload = json.loads(sInput)
        # Set battery level
        if self.battName in jPayload:
            #print("Battery value found {}".format(jPayload[nd.battName]))
            self.battLevel = jPayload[self.battName]
        #try:
        #    if not self.locationOverride:
        #        if "latitude" in jPayload:
        #            if isinstance(jPayload["latitude"], str):
        #                self.latitude = float(jPayload["latitude"])
        #            else:
        #                self.latitude = jPayload["latitude"]
        #        if "Latitude" in jPayload:
        #            if isinstance(jPayload["Latitude"], str):
        #                self.latitude = float(jPayload["Latitude"])
        #            else:
        #                self.latitude = jPayload["Latitude"]
        #except Exception as e:
        #    print(e)
        #    print("Houston, we have an error {}".format(e))  
        
        if not self.locationOverride:
            if "longitude" in jPayload:
                if isinstance(jPayload["longitude"], str):
                    self.longitude = float(jPayload["longitude"])
                else:
                    self.longitude = jPayload["longitude"]
            if "Longitude" in jPayload:
                if isinstance(jPayload["Longitude"], str):
                    self.longitude = float(jPayload["Longitude"])
                else:
                    self.longitude = jPayload["Longitude"]
 
        if "RSSI" in jPayload:
            if isinstance(jPayload["RSSI"], int) or isinstance(jPayload["RSSI"], float):
                self.RSSI = jPayload["RSSI"]
            else:
                print("Invalid data for RSSI, recieved '{}'".format(jPayload["RSSI"]))
        return()
    
    def incrementMsgCnt(self):
        """
        Function increases message count for current node by 1
        If new hour send update to influxdb
        """
        
        tDate = timezone.make_aware(datetime.datetime.now(), timezone.get_current_timezone())
        aStat = self.nodemsgstats_set.all().filter(dt = tDate, hr = tDate.hour)
               
        if len(aStat) == 0:
            nMsg = NodeMsgStats(node=self, dt = tDate, hr = tDate.hour)
            nMsg.msgCount = 1
            nMsg.save()
        else:
            nMsg = aStat[0]
            nMsg.msgCount = nMsg.msgCount + 1
            nMsg.save()

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


class NodeMsgStats(models.Model):
    """
    This message type collects data on the number of messages sent or relayed by a node or gateway
    """
    node = models.ForeignKey(Node, on_delete=models.CASCADE)
    dt = models.DateField()
    hr = models.IntegerField()
    msgCount = models.IntegerField(default = 0)

    def __str__(self):
        return("{}: {} : {}".format(self.node.nodeID, self.dt, self.hr))
