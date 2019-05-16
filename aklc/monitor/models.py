from __future__ import unicode_literals
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# Create your models here.
# Create your models here.
class Node(models.Model):
    nodeID = models.CharField(max_length=30)
    lastseen = models.DateTimeField(blank=True, null = True)
    statusSent = models.DateTimeField(blank=True, null = True)
    isGateway = models.BooleanField(blank=True, default = False)
    notificationSent = models.BooleanField(blank=True, default = False)
    status = models.CharField(max_length=10, blank=True, null = True)
    nextUpdate = models.DateTimeField(blank=True, null = True)
    topic = models.CharField(max_length=50, blank=True, null = True)
    descr = models.TextField(blank=True, null = True)
    topic = models.CharField(max_length=30, blank=True, null = True)
    lastData = models.TextField(blank=True, null = True)
    lastStatus = models.TextField(blank=True, null = True)
    
    def __str__(self):
        return self.nodeID
    
class NodeUser(models.Model):
    nodeID = models.ForeignKey(Node, on_delete=models.CASCADE)
    username = models.ForeignKey(User, on_delete=models.CASCADE)
    email = models.BooleanField(blank=True, default = False)
    sms  = models.BooleanField(blank=True, default = False)

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phoneNumber = models.CharField(max_length=50, blank=True, null=True)
    reportType = models.CharField(max_length=1, blank=True, null=True, default='S')

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
	if created:
		Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
	instance.profile.save()
