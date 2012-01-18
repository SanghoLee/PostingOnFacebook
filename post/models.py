from django.db import models

class Person(models.Model):
   username = models.CharField(max_length=30, primary_key=True, unique=True)
   password = models.CharField(max_length=30) # TODO: encryption
   api_access_key = models.CharField(unique=True, max_length=30)
   fb_id = models.BigIntegerField(null=True, unique=True)
   fb_access_token = models.CharField(null=True, max_length=150, unique=True) # TODO: consider ExpireTime
