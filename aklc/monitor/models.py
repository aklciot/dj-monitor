from __future__ import unicode_literals
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import datetime
from django.utils import timezone
from django import template
import json
import numbers

# Create your models here.
class Team(models.Model):
    """
    Model for a Team, usually referred to as a Project by the IoT team.
    """

    teamID = models.CharField(max_length=50)
    descr = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["teamID"]
        verbose_name = "Project"

    def __str__(self):
        return self.teamID


class MessageType(models.Model):
    """
    Model to define different CSV message types.

    The message type consists of this header model and a number of MessageItem
    elements which need to be ordered as in the incoming payload.
    """

    msgName = models.CharField(max_length=30)
    descr = models.TextField(blank=True, null=True, help_text="")

    class Meta:
        ordering = ["msgName"]
        verbose_name = "Message Type"

    def __str__(self):
        return self.msgName


class MessageItem(models.Model):
    """
    Model for message items which are part of the MessageType element.
    """

    FIELD_TYPE_CHOICES = [
        ("S", "String"),
        ("I", "Integer"),
        ("F", "Float"),
    ]
    msgID = models.ForeignKey(MessageType, on_delete=models.CASCADE)
    name = models.CharField(
        max_length=15, help_text="The element name, will be used in JSON messages"
    )
    order = models.IntegerField()
    fieldType = models.CharField(
        max_length=1,
        help_text="Field type can be 'S': string, 'I': integer, 'F': float",
        choices=FIELD_TYPE_CHOICES,
    )
    isTag = models.BooleanField(
        blank=True,
        default=False,
        help_text="Use as a field tag when uploading to Influx",
    )

    class Meta:
        ordering = ["order"]
        verbose_name = "Message Item"

    def __str__(self):
        return f"{self.msgID.msgName}: {self.name}"


class HtmlTemplate(models.Model):
    """
    This model is used to list available templates
    """

    templateName = models.CharField(max_length=50, blank=True, null=True)
    fileName = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return self.templateName


class Node(models.Model):
    """
    Model definition for the Node object.

    Functions:
        passOnData - send info about associated nodes/gateways
        msgReceived - updates the node when a new message arrives
        jsonLoad(input) - processes JSON input
        incrementMsgCnt - increments message count for node
    """

    nodeID = models.CharField(max_length=30)
    lastseen = models.DateTimeField(blank=True, null=True)
    cameOnline = models.DateTimeField(blank=True, null=True)
    upTime = models.FloatField("Uptime in minutes", default=0.0)
    # uptime = models.FloatField(default=0)

    bootTime = models.DateTimeField(blank=True, null=True)
    onlineTime = models.FloatField("Online in minutes", default=0.0)
    status_sent = models.DateTimeField(null=True, blank=True)
    notification_sent = models.BooleanField(default=False)
    nextUpdate = models.DateTimeField(blank=True, null=True)
    lastStatusTime = models.DateTimeField(blank=True, null=True)
    lastDataTime = models.DateTimeField(blank=True, null=True)

    isGateway = models.BooleanField(blank=True, default=False)
    isRepeater = models.BooleanField(blank=True, default=False)

    status = models.CharField(
        max_length=1,
        default=" ",
        help_text="C is current, X is down, M in maintenance mode",
    )
    textStatus = models.CharField(max_length=10, blank=True, null=True)
    topic = models.CharField(max_length=50, blank=True, null=True)
    descr = models.TextField(blank=True, null=True, help_text="")
    lastData = models.TextField(blank=True, null=True)
    lastJSON = models.TextField(blank=True, null=True)
    lastStatus = models.TextField(blank=True, null=True)
    allowedDowntime = models.IntegerField(
        default=60,
        help_text="Minutes that the node can be 'unheard' before being marked as Offline",
    )
    hardware = models.CharField(max_length=50, blank=True, null=True)
    software = models.CharField(max_length=50, blank=True, null=True)
    production = models.BooleanField(
        "Production node",
        default=False,
        help_text="If selected, node will be treated as production, not test",
    )
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    battName = models.CharField(
        max_length=40,
        blank=True,
        null=True,
        help_text="The attribute name in JSON messages used for battery levels",
    )
    battMonitor = models.BooleanField(default=False)
    battLevel = models.FloatField(default=0.0)
    battWarn = models.FloatField(
        default=0.0,
        help_text="The battery level, below which warning message are generated",
    )
    battCritical = models.FloatField(
        default=0.0,
        help_text="The battery level, below which critical warning message are generated",
    )
    # dataMsgCount = models.IntegerField(default=0)
    RSSI = models.FloatField(default=0.0)
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True)
    portal = models.URLField(
        max_length=100,
        blank=True,
        null=True,
        help_text="A link where more data on this node is available",
    )
    messagetype = models.ForeignKey(
        MessageType,
        blank=True,
        null=True,
        help_text="This message type will be used to convert incoming CSV data to JSON format",
        on_delete=models.SET_NULL,
    )
    influxUpload = models.BooleanField(
        "Upload to InfluxDB",
        default=False,
        help_text="Select this if you want data uploaded to InfluxDB.",
    )
    thingsboardUpload = models.BooleanField(
        "Upload to Thingsboard",
        default=False,
        help_text="Select this if you want data uploaded to Thingsboard on AWS2. NB Thingsboard cred also needs to be completed.",
    )
    locationOverride = models.BooleanField(
        "Location override",
        default=False,
        help_text="If selected, incoming location data will be ignored and stored data passed on",
    )
    projectOverride = models.BooleanField(
        "Project override",
        default=False,
        help_text="If selected, any incoming Project name will be ignored and stored Project passed on",
    )
    thingsboardCred = models.CharField(
        "Thingsboard credentials",
        max_length=40,
        blank=True,
        null=True,
        help_text="The credentials needed for thingsboard data load",
    )
    sms_template = models.ForeignKey(
        HtmlTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="smsTemplate",
        help_text="Optional HTML template to be used for SMS node down messages",
    )
    email_down_template = models.ForeignKey(
        HtmlTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emailDownTemplate",
        help_text="Optional HTML template to be used for email node down messages",
    )
    email_up_template = models.ForeignKey(
        HtmlTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emailUpTemplate",
        help_text="Optional HTML template to be used for email node up messages",
    )
    email_reminder_template = models.ForeignKey(
        HtmlTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emailReminderTemplate",
        help_text="Optional HTML template to be used for daily email node down reminder messages",
    )
    email_status_template = models.ForeignKey(
        HtmlTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emailStatusTemplate",
        help_text="Optional HTML template to be used for weekly email status messages",
    )

    class Meta:
        ordering = ["nodeID"]

    def __str__(self):
        return self.nodeID

    def passOnData(self):
        """
        This function returns data about items that have processed data.

        Gateways, returns the nodes they have processed data for,
        Nodes, returns the gateways that have processed their data

        Only data processed in the last 7 data is considered. 

        """
        if self.isGateway:
            passAll = NodeGateway.objects.filter(gatewayID=self).order_by("-lastdata")
        else:  # must be a node
            passAll = NodeGateway.objects.filter(nodeID=self).order_by("-lastdata")
        # Now filter the result so we only get the last 7 days
        passAll = passAll.filter(
            lastdata__gte=(
                timezone.make_aware(
                    datetime.datetime.now(), timezone.get_current_timezone()
                )
                - datetime.timedelta(days=7)
            )
        )
        return passAll

    def msgReceived(self, mqttClient, emailFrom, eMail_topic):
        """
        This function updates node data when a new message is received.
        """
        self.lastseen = timezone.make_aware(
            datetime.datetime.now(), timezone.get_current_timezone() 
        )
        if self.status != "C":  # if the node is not current, update the status
            self.textStatus = "Online"
            self.status = "C"
            self.cameOnline = timezone.make_aware(
                datetime.datetime.now(), timezone.get_current_timezone()
            )

            if self.email_up_template:
                for usr in self.nodeuser_set.all():
                    if usr.email:
                        print(f"Send email to {usr.user} that {self.nodeID} is back up")
                    
                        payload = {}
                        try:
                            inDataDict = {"node": self}
                            #inDataDict["web_base_url"] = eWeb_Base_URL
                            inDataDict["user"] = usr.user
                            t = template.loader.get_template(f"monitor/{self.email_up_template.fileName}")
                            body = t.render(inDataDict)

                            payload["To"] = usr.user.email
                            payload["From"] = emailFrom
                            payload["Body"] = body
                            payload["Subject"] = f"Device {self.nodeID} is back up"
                            mqttClient.publish(eMail_topic, json.dumps(payload))
                            print(f"Email sent to {usr.user.email}")

                        except Exception as e:
                            print(e)
                            print(f"Houston, we have an error {e}")
                    
        minDelta = (
            timezone.make_aware(
                datetime.datetime.now(), timezone.get_current_timezone()
            )
            - self.cameOnline
        )
        self.onlineTime = minDelta.total_seconds() / 60
        return ()

    def jsonLoad(self, sInput):
        """
        Process as JSON string and updates any relevant node/gateway attributes.
        """

        jPayload = json.loads(sInput)
        # Set battery level
        if self.battName in jPayload:
            self.battLevel = jPayload[self.battName]

        # process location data if we are not over riding it
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

            if "latitude" in jPayload:
                if isinstance(jPayload["latitude"], str):
                    self.latitude = float(jPayload["latitude"])
                else:
                    self.latitude = jPayload["latitude"]
            if "Latitude" in jPayload:
                if isinstance(jPayload["Latitude"], str):
                    self.latitude = float(jPayload["Latitude"])
                else:
                    self.latitude = jPayload["Latitude"]

        if "RSSI" in jPayload:
            if isinstance(jPayload["RSSI"], int) or isinstance(jPayload["RSSI"], float):
                self.RSSI = jPayload["RSSI"]
            else:
                print(f"Invalid data for RSSI, recieved {jPayload['RSSI']}")
        if "Uptime" in jPayload:
            self.bootTimeUpdate(jPayload["Uptime"])
        if "Uptime(m)" in jPayload:
            self.bootTimeUpdate(jPayload["Uptime(m)"])
        if "Uptime(s)" in jPayload:
            self.bootTimeUpdate(jPayload["Uptime(s)"] / 60)
        if "Version" in jPayload and isinstance(jPayload['Version'], str):
            self.software = jPayload['Version']
        if "Type" in jPayload and isinstance(jPayload['Type'], str):
            self.hardware = jPayload['Type']
        self.save()
        return ()

    def incrementMsgCnt(self):
        """
        Function increases message count for current node by 1.

        Looks for relevant NodeMsgStats record and either creates a new one, or updates the existing one.        
        """
        # get the django preferred date
        tDate = timezone.make_aware(
            datetime.datetime.now(), timezone.get_current_timezone()
        )

        # Look for the NodeMsgStats record for this node at this time
        aStat = self.nodemsgstats_set.all().filter(dt=tDate, hr=tDate.hour)

        if len(aStat) == 0:  # If not found, make a new one
            nMsg = NodeMsgStats(node=self, dt=tDate, hr=tDate.hour)
            nMsg.msgCount = 1
            nMsg.save()
        else:
            nMsg = aStat[0]
            nMsg.msgCount = nMsg.msgCount + 1
            nMsg.save()

        return ()

    def startTime(self):
        """
        Function returns date & time when node last started  
        """
        dt = timezone.make_aware(
            datetime.datetime.now(), timezone.get_current_timezone()
        ) - datetime.timedelta(minutes=self.upTime)

        return dt

    def make_json(self, payload):
        """
        This function will create a JSON representation of the CSV input if linked to a message_type
        """
        jStr = {}

        if not self.messagetype:
            return jStr
        print(f"Message type found {self.messagetype.msgName}")
        print(f"Payload is {payload}")
        cPayload = payload.split(",")

        # Don't try and process if a Status message. Status message has 'OK' as second value
        if len(cPayload) > 1 and cPayload[1] == "OK":
            return(jStr)

        # here we try and remove any references to any repeaters
        lRepeater = True

        while lRepeater:
            nCnt = 0
            for itm in cPayload:
                nCnt += 1
                if nCnt < 3:
                    continue
                lRepeater = False
                if itm.startswith("RP"):
                    # print(f"Remove {itm} from input")
                    cPayload.remove(itm)
                    lRepeater = True

        for mItem in self.messagetype.messageitem_set.all():
            # print("  msgItem is {}, value is {}".format(mItem.name, cPayload[mItem.order-1]))
            # some validation here

            if mItem.order > len(cPayload):
                # print(f"Message type mismatch, payload is {cPayload}, message type is {nNode.messagetype.msgName}, index is {mItem.order}")
                break

            try:
                if mItem.fieldType == "I":
                    val = float(cPayload[mItem.order - 1])
                elif mItem.fieldType == "F":
                    val = float(cPayload[mItem.order - 1])
                else:
                    val = cPayload[mItem.order - 1]

            except Exception as e:
                print(
                    f"CSV to JSON error, cPayload is {cPayload}, message type is {self.messagetype.msgName}"
                )
                print(e)

            jStr[mItem.name] = val

        print(f"jStr is {jStr}")
        return jStr

    def bootTimeUpdate(self, inMinutes):
        """Updates a node uptime and boottime based on seconds uptime"""
        if isinstance(inMinutes, numbers.Number):
            try:
                self.upTime = inMinutes
                self.bootTime = timezone.make_aware(
                    datetime.datetime.now(), timezone.get_current_timezone()
                ) - datetime.timedelta(minutes=inMinutes)
                self.save()
            except Exception as e:
                print(f"Error in bootTimeUpdate, {e}, input was {inMinutes}")
        else: 
            print(f"Input to bootTimeUpdate was not numeric {inMinutes}")
        return


class NodeUser(models.Model):
    """
    Model for relationship between a user and a node.
    """

    nodeID = models.ForeignKey(Node, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    email = models.BooleanField(blank=True, default=False)
    sms = models.BooleanField(blank=True, default=False)
    lastemail = models.DateTimeField(blank=True, null=True)
    lastsms = models.DateTimeField(blank=True, null=True)
    smsSent = models.BooleanField(blank=True, default=False)
    daily = models.BooleanField(blank=True, default=False)

    def __str__(self):
        return f"{self.nodeID}: {self.user.username}"


class Profile(models.Model):
    """
    This model is used to extend the user model.

    Current uses are:
        Record a mobile phone number which is used for SMS alerts
        Record what type of email report a user gets
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phoneNumber = models.CharField(max_length=50, blank=True, null=True)
    reportType = models.CharField(max_length=1, blank=True, null=True, default="S")
    customer = models.BooleanField(blank=True, default=False)
    pushbulletApi = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.user.username


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Function to automatically create a profile when a new user is created
    """
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Function to automatically save a profile when the associated user is save
    """
    instance.profile.save()


class NodeGateway(models.Model):
    """
    This model stores the date/time the last message from a node was passed on by a gateway.
    """

    nodeID = models.ForeignKey(Node, on_delete=models.CASCADE)
    gatewayID = models.ForeignKey(
        Node, on_delete=models.CASCADE, related_name="gateway",
    )
    lastdata = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Node : {self.nodeID}, Gateway : {self.gatewayID}"


class NodeMsgStats(models.Model):
    """
    This message type collects data on the number of messages sent or relayed by a node or gateway.
    """

    node = models.ForeignKey(Node, on_delete=models.CASCADE)
    dt = models.DateField()
    hr = models.IntegerField()
    msgCount = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.node.nodeID}: {self.dt} : {self.hr}"


class MqttQueue(models.Model):
    """
    This stores details of various mqtt queues.
    """

    descr = models.CharField(max_length=50)
    host = models.CharField(max_length=50)
    port = models.IntegerField()
    user = models.CharField(max_length=50, blank=True, null=True)
    pw = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        ordering = ["descr"]
        verbose_name = "Mqtt Queue"

    def __str__(self):
        return f"{self.descr}"


class MqttMessage(models.Model):
    """
    Stores the last mqtt message for a node
    """

    node = models.ForeignKey(Node, on_delete=models.CASCADE)
    mqttQueue = models.ForeignKey(MqttQueue, on_delete=models.CASCADE)
    received = models.DateTimeField(auto_now=True)
    first_msg = models.DateTimeField(auto_now_add=True)
    topic = models.CharField(max_length=100)
    payload = models.TextField()

    class Meta:
        ordering = ["node"]
        verbose_name = "Mqtt Message"

    def __str__(self):
        return f"Node: {self.node.nodeID}, mqtt: {self.mqttQueue.descr}, topic: {self.topic}, payload: {self.payload}, received: {self.received}"

class MqttStore(models.Model):
    """
    Stores all mqtt messages
    """

    mqttQueue = models.ForeignKey(MqttQueue, on_delete=models.CASCADE)
    received = models.DateTimeField(auto_now=True)
    topic = models.CharField(max_length=100)
    payload = models.TextField()
    qos = models.IntegerField()
    retained = models.BooleanField()

    class Meta:
        verbose_name = "Mqtt Store"

    def __str__(self):
        return f"mqtt: {self.mqttQueue.descr}, topic: {self.topic}, payload: {self.payload}, received: {self.received}, retained: {self.retained}"

class JsonError(models.Model):
    """
    Stores JSON error messages
    """

    node = models.ForeignKey(Node, on_delete=models.CASCADE)
    mqttQueue = models.ForeignKey(MqttQueue, on_delete=models.CASCADE)
    received = models.DateTimeField(auto_now=True)
    fieldKey = models.CharField(max_length=100)
    message = models.TextField()

    class Meta:
        ordering = ["mqttQueue", "node", "fieldKey"]

    def __str__(self):
        return f"Node: {self.node.nodeID}, MQTT Q: {self.mqttQueue.descr}, field: {self.fieldKey}, error: {self.message}"
