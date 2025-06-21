from django.db import models
from django.contrib.auth.models import AbstractUser # Use AbstractUser to extend Django's User
from django.conf import settings # Import settings to reference AUTH_USER_MODEL
import uuid # For generating unique IDs for groups and tasks


# Define Group Model
class Group(models.Model):
    # Use UUID as primary key for robust unique identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True, help_text="Name of the group")
    # Link to the user who created the group (admin)
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='managed_groups',
        help_text="The user who is the admin of this group."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Group"
        verbose_name_plural = "Groups"
        ordering = ['name'] # Order groups by name

    def __str__(self):
        return self.name

# Define Membership Model to link Users and Groups
class Membership(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='group_memberships',
        help_text="The user participating in the group."
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='members',
        help_text="The group the user is a member of."
    )
    date_joined = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'group') # A user can only be a member of a group once
        verbose_name = "Membership"
        verbose_name_plural = "Memberships"
        ordering = ['group__name', 'user__username'] # Order by group name then username

    def __str__(self):
        return f"{self.user.username} in {self.group.name}"

