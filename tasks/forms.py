# tasks/forms.py

from django import forms
from tasks.models import Task
from users.models import Group, Membership
from django.contrib.auth import get_user_model

User = get_user_model()

# Form for creating and updating individual tasks
class TaskForm(forms.ModelForm):
    # Overriding the queryset for assignee and group to make them optional
    assignee = forms.ModelChoiceField(
        queryset=User.objects.all().order_by('username'), # Default: all users
        required=False,
        empty_label="Unassigned",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    group = forms.ModelChoiceField(
        queryset=Group.objects.all().order_by('name'), # Default: all groups
        required=False,
        empty_label="Personal Task",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    due_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=False,
        help_text="Optional due date for the task."
    )

    class Meta:
        model = Task
        fields = ['title', 'description', 'due_date', 'assignee', 'group', 'status']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Task Title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Task Description (optional)'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'title': 'Task Title',
            'description': 'Description',
            'due_date': 'Due Date',
            'assignee': 'Assign To',
            'group': 'Belongs to Group',
            'status': 'Status',
        }

    def __init__(self, *args, **kwargs):
        # Allow passing the request user and potentially a specific group to the form
        self.request_user = kwargs.pop('request_user', None)
        self.specific_group = kwargs.pop('specific_group', None) # New: for when editing/creating task within a group
        super().__init__(*args, **kwargs)

        if self.request_user:
            # Filter groups for the current user (admin or member)
            user_groups_as_member_ids = Membership.objects.filter(user=self.request_user).values_list('group__id', flat=True)
            user_groups_as_admin_ids = Group.objects.filter(admin=self.request_user).values_list('id', flat=True)
            allowed_group_ids = list(set(list(user_groups_as_member_ids) + list(user_groups_as_admin_ids)))
            self.fields['group'].queryset = Group.objects.filter(id__in=allowed_group_ids).order_by('name')

            # If a specific group is provided (e.g., when creating a task from GroupDetailView)
            if self.specific_group:
                # Set the initial group for the form and disable the field
                self.fields['group'].initial = self.specific_group
                self.fields['group'].widget.attrs['disabled'] = 'disabled'
                # Filter assignees to only members of this specific group
                group_member_ids = Membership.objects.filter(group=self.specific_group).values_list('user__id', flat=True)
                self.fields['assignee'].queryset = User.objects.filter(id__in=group_member_ids).order_by('username')
            elif self.instance.pk and self.instance.group: # If editing an existing task with a group
                 # Filter assignees to only members of the task's current group
                group_member_ids = Membership.objects.filter(group=self.instance.group).values_list('user__id', flat=True)
                self.fields['assignee'].queryset = User.objects.filter(id__in=group_member_ids).order_by('username')
            else:
                # For personal tasks or when no group is selected, assignee can be any user (or self)
                self.fields['assignee'].queryset = User.objects.all().order_by('username')


# Form specifically for marking a task as complete (or changing status)
class TaskStatusForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

# Form for adding/removing members from a group
class GroupMemberForm(forms.Form):
    # Use CheckboxSelectMultiple to allow selecting multiple users
    members = forms.ModelMultipleChoiceField(
        queryset=User.objects.all().order_by('username'),
        widget=forms.CheckboxSelectMultiple,
        required=False, # Allows removing all members if desired
        help_text="Select users to add/remove from the group."
    )

    def __init__(self, *args, **kwargs):
        self.group = kwargs.pop('group', None)
        super().__init__(*args, **kwargs)
        if self.group:
            # Set initial selected members to current group members
            current_members = self.group.members.values_list('user', flat=True)
            self.fields['members'].initial = list(current_members)
            # Exclude the group admin from the selectable members, as admin is always a member
            self.fields['members'].queryset = User.objects.exclude(id=self.group.admin.id).order_by('username')

