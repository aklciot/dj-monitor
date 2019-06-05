from __future__ import unicode_literals
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# Create your models here.
# Create your models here.
class Node(models.Model):
    nodeID = models.CharField(max_length=30)
    lastseen = models.DateTimeField(blank=True, null=True)
    status_sent = models.DateTimeField(null=True, blank=True)
    isGateway = models.BooleanField(blank=True, default=False)
    notification_sent = models.BooleanField(default=False)
    status = models.CharField(max_length=1, default=" ", help_text="C is current, X is down, M in maintenance mode")
    textStatus = models.CharField(max_length=10, blank=True, null=True)
    nextUpdate = models.DateTimeField(blank=True, null=True)
    topic = models.CharField(max_length=50, blank=True, null=True)
    descr = models.TextField(blank=True, null=True)
    topic = models.CharField(max_length=30, blank=True, null=True)
    lastData = models.TextField(blank=True, null=True)
    lastStatus = models.TextField(blank=True, null=True)
    allowedDowntime = models.IntegerField(default=60, help_text="Minutes that the node can be 'unheard' before being marked as Offline")
    hardware = models.CharField(max_length=50, blank=True, null=True)
    software = models.CharField(max_length=50, blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude  = models.FloatField(blank=True, null=True)
    battName = models.CharField(max_length=40, blank=True, null=True)
    battValue = models.FloatField(default = 0.0)
    battWarning = models.FloatField(default = 0.0)
    battCritical = models.FloatField(default = 0.0)

    def __str__(self):
        return self.nodeID
    
class NodeUser(models.Model):
    nodeID = models.ForeignKey(Node, on_delete=models.CASCADE)
    username = models.ForeignKey(User, on_delete=models.CASCADE)
    email = models.BooleanField(blank=True, default=False)
    sms  = models.BooleanField(blank=True, default=False)
    lastemail = models.DateTimeField(blank=True, null=True)
    lastsms = models.DateTimeField(blank=True, null=True)
    smsSent = models.BooleanField(blank=True, default=False)

    def __str__(self):
        return("{}: {}".format(self.nodeID, self.username))

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phoneNumber = models.CharField(max_length=50, blank=True, null=True)
    reportType = models.CharField(max_length=1, blank=True, null=True, default='S')

    def __str__(self):
        return self.user


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
	if created:
		Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
	instance.profile.save()
