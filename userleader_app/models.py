from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils.translation import gettext_lazy as _


# Create your models here.

class CustomUser(AbstractUser):
    first_name = models.CharField(max_length=220, null=True, blank=True)
    last_name = models.CharField(max_length=220, null=True, blank=True)
    email = models.EmailField(_('email'), unique=True)

    groups = models.ManyToManyField(Group, blank=True, related_name='custom_users')
    user_permissions = models.ManyToManyField(Permission, blank=True, related_name='custom_users')

    def __str__(self):
        return self.username
