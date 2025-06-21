from django.db import models
from django.conf import settings
from users.models import Group
import uuid

# Create your models here.
class Task(models.Model):
    # Use UUID as primary key for robust unique identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, help_text="Short description of the task.")
    description = models.TextField(blank=True, help_text="Detailed description of the task.")
    # Task owner (the user who created it)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_tasks',
        help_text="The user who created this task."
    )
    # Assignee (the user responsible for completing it)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, # If assignee is deleted, task remains but assignee is null
        related_name='assigned_tasks',
        null=True,
        blank=True,
        help_text="The user currently assigned to this task."
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='tasks',
        null=True,
        blank=True,
        help_text="The group this task belongs to (optional for personal tasks)."
    )

    STATUS_CHOICES = [
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('overdue', 'Overdue'),
    ]
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='ongoing',
        help_text="Current status of the task."
    )
    due_date = models.DateField(null=True, blank=True, help_text="Optional due date for the task.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Task"
        verbose_name_plural = "Tasks"
        ordering = ['due_date', 'created_at'] # Order by due date then creation date

    def __str__(self):
        return f"{self.title} (Status: {self.status})"

    def save(self, *args, **kwargs):
        # Auto-set status to 'overdue' if due_date is in the past and task is not completed
        from datetime import date
        if self.due_date and self.due_date < date.today() and self.status == 'ongoing':
            self.status = 'overdue'
        super().save(*args, **kwargs)
