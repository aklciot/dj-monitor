from __future__ import unicode_literals
from django.db import models

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
    description = models.CharField(max_length=200, blank=True, null = True)
    
    def __str__(self):
        return self.nodeID
    
