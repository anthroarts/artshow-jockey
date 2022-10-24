from django.db import models


class AuthorizationCode(models.Model):
    code = models.CharField(max_length=100, primary_key=True)


class BearerToken(models.Model):
    token = models.CharField(max_length=100, primary_key=True)
