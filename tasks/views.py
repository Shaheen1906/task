# tasks/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View, DetailView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from tasks.models import Task
from users.models import Group, Membership # Import our models
from .forms import TaskForm, TaskStatusForm, GroupMemberForm # Import new GroupMemberForm
from datetime import date # To handle overdue status
from django.db import models # For Q objects

# Mixin to ensure only task owner or group admin can modify/delete group tasks
class TaskOwnerOrGroupAdminMixin(UserPassesTestMixin):
    def test_func(self):
        task = self.get_object()
        # Check if user is the task owner
        if task.owner == self.request.user:
            return True
        # Check if task belongs to a group and user is group admin
        if task.group and task.group.admin == self.request.user:
            return True
        # Check if task belongs to a group and user is a member (allowing deletion/edit for members is a choice)
        # For simplicity, keeping it owner/admin for modify/delete for now.
        return False
    
    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to perform this action on this task.")
        return redirect(self.request.META.get('HTTP_REFERER', reverse_lazy('task_list')))


# Mixin to ensure only the group admin can access certain group management features
class GroupAdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        group = self.get_object()
        return self.request.user == group.admin

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to perform this action.")
        return redirect(reverse_lazy('group_list')) # Redirect to group list if not admin

# Base view for task lists
class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = 'tasks/task_list.html'
    context_object_name = 'tasks'
    paginate_by = 10 # Optional: Add pagination

    def get_queryset(self):
        # Get tasks where the current user is the owner OR
        # the task is assigned to the current user OR
        # the task belongs to a group the user is a member of (including admin).

        # Filter by status (ongoing, completed, overdue) from URL parameter
        status_filter = self.request.GET.get('status')

        # Start with all tasks the user is involved in
        queryset = Task.objects.filter(
            models.Q(owner=self.request.user) |
            models.Q(assignee=self.request.user) |
            models.Q(group__members__user=self.request.user) | # Tasks in groups the user is a member of
            models.Q(group__admin=self.request.user) # Tasks in groups the user admins
        ).distinct() # Use distinct to avoid duplicates if a task satisfies multiple Q conditions

        # Apply status filter if present
        if status_filter in ['ongoing', 'completed']:
            queryset = queryset.filter(status=status_filter)
        elif status_filter == 'overdue':
            # Overdue tasks are ongoing tasks with a past due date
            queryset = queryset.filter(status='ongoing', due_date__lt=date.today())
        elif status_filter == 'all':
            pass # No additional status filter
        else: # Default to ongoing tasks (excluding overdue)
            queryset = queryset.filter(status='ongoing').exclude(due_date__lt=date.today())

        # Order tasks (e.g., by due date or creation date)
        queryset = queryset.order_by('due_date', '-created_at')
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pass the current filter status to the template for active tab indication
        context['current_status_filter'] = self.request.GET.get('status', 'ongoing')
        return context

# View for creating a new task
class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = 'tasks/task_form.html'
    success_url = reverse_lazy('task_list') # Default redirect

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request_user'] = self.request.user
        # If group_id is in URL, pass it to the form
        group_id = self.kwargs.get('group_id') # Use self.kwargs for URL parameters
        if group_id:
            try:
                group = Group.objects.get(pk=group_id)
                kwargs['specific_group'] = group
            except Group.DoesNotExist:
                messages.error(self.request, "Invalid group specified.")
                # Fallback to general task list or handle error
                return redirect(reverse_lazy('task_list'))
        return kwargs

    def form_valid(self, form):
        # Save the form instance without committing to the database yet
        task = form.save(commit=False)
        task.owner = self.request.user # Explicitly set owner

        # If a specific group was provided in the URL, set it on the task instance
        group_id = self.kwargs.get('group_id')
        if group_id:
            try:
                task.group = Group.objects.get(pk=group_id)
            except Group.DoesNotExist:
                messages.error(self.request, "Invalid group specified during task creation.")
                return self.form_invalid(form)

        # Assignee logic: If no assignee is explicitly set, default to the owner for personal tasks
        # For group tasks, if no assignee, set to current user if they are a member.
        if not task.assignee and not task.group:
            task.assignee = self.request.user
        elif task.group and not task.assignee:
            if self.request.user in task.group.members.all():
                 task.assignee = self.request.user
            else:
                messages.warning(self.request, "Task created for group but no assignee selected, or you are not a member to self-assign. It is unassigned.")

        task.save() # Now save the instance to the database

        messages.success(self.request, 'Task created successfully!')
        # Redirect to group detail if created for a group, otherwise to task list
        if group_id:
            return redirect(reverse_lazy('group_detail', kwargs={'pk': group_id}))
        return redirect(self.get_success_url())


# View for updating an existing task
class TaskUpdateView(LoginRequiredMixin, TaskOwnerOrGroupAdminMixin, UpdateView):
    model = Task
    form_class = TaskForm
    template_name = 'tasks/task_form.html'
    context_object_name = 'task'

    def get_success_url(self):
        # If task has a group, redirect to group detail, otherwise to task list
        if self.object.group:
            return reverse_lazy('group_detail', kwargs={'pk': self.object.group.pk})
        return reverse_lazy('task_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request_user'] = self.request.user
        # When updating, if the task belongs to a group, pass that group to filter assignees
        if self.object.group:
            kwargs['specific_group'] = self.object.group
        return kwargs

    def form_valid(self, form):
        # Save the form instance without committing to the database yet
        task = form.save(commit=False)

        # Only task owner can change due date for overdue tasks
        if 'due_date' in form.changed_data and task.status == 'overdue' and self.request.user != task.owner:
            messages.error(self.request, "Only the task owner can change the due date of an overdue task.")
            # Do not save changes, just return invalid form
            return self.form_invalid(form)
        
        # If the task was edited from a group's page and the group field was disabled,
        # ensure the group relationship is not accidentally lost or changed if not intended by the form.
        # This implicitly retains the original task.group as form.instance already has it loaded.
        # The key change is calling save() after potential modifications.
        
        task.save() # Now save the instance to the database

        messages.success(self.request, 'Task updated successfully!')
        # Redirect based on whether the task is associated with a group
        if task.group:
            return redirect(reverse_lazy('group_detail', kwargs={'pk': task.group.pk}))
        return redirect(self.get_success_url())


# View to mark a task as complete (or change status)
class TaskMarkCompleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk)

        # Check if the user is authorized to mark this task complete
        is_owner = task.owner == request.user
        is_assignee = (task.assignee == request.user and task.assignee is not None)
        is_group_admin = task.group and task.group.admin == request.user
        is_group_member = task.group and Membership.objects.filter(group=task.group, user=request.user).exists()


        if not (is_owner or is_assignee or is_group_admin or is_group_member):
            messages.error(request, "You are not authorized to change the status of this task.")
            return redirect(request.META.get('HTTP_REFERER', reverse_lazy('task_list')))

        # Direct update of status
        if task.status != 'completed': # Only update if not already completed
            task.status = 'completed'
            task.save()
            messages.success(request, f'Task "{task.title}" marked as completed!')
        else:
            messages.info(request, f'Task "{task.title}" is already completed.')

        return redirect(request.META.get('HTTP_REFERER', reverse_lazy('task_list')))


# Group Management Views
class GroupListView(LoginRequiredMixin, ListView):
    model = Group
    template_name = 'groups/group_list.html'
    context_object_name = 'groups'

    def get_queryset(self):
        return Group.objects.filter(
            models.Q(admin=self.request.user) |
            models.Q(members__user=self.request.user)
        ).distinct().order_by('name')


class GroupCreateView(LoginRequiredMixin, CreateView):
    model = Group
    fields = ['name']
    template_name = 'groups/group_form.html'
    success_url = reverse_lazy('group_list')

    def form_valid(self, form):
        form.instance.admin = self.request.user
        group = form.save()
        Membership.objects.create(user=self.request.user, group=group)
        messages.success(self.request, f'Group "{group.name}" created successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Create New Group'
        return context


class GroupDetailView(LoginRequiredMixin, DetailView):
    model = Group
    template_name = 'groups/group_detail.html'
    context_object_name = 'group'

    def get_queryset(self):
        return Group.objects.filter(
            models.Q(admin=self.request.user) |
            models.Q(members__user=self.request.user)
        ).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group = self.get_object()
        context['members'] = group.members.all().order_by('user__username')
        context['tasks'] = group.tasks.all().order_by('due_date', '-created_at')
        context['is_admin'] = (self.request.user == group.admin)
        return context


class GroupUpdateView(GroupAdminRequiredMixin, UpdateView):
    model = Group
    fields = ['name']
    template_name = 'groups/group_form.html'
    context_object_name = 'group'

    def get_success_url(self):
        return reverse_lazy('group_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, f'Group "{form.instance.name}" updated successfully.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Edit Group'
        return context


class GroupDeleteView(GroupAdminRequiredMixin, DeleteView):
    model = Group
    template_name = 'groups/group_confirm_delete.html'
    context_object_name = 'group'
    success_url = reverse_lazy('group_list')

    def form_valid(self, form):
        messages.success(self.request, f'Group "{self.object.name}" deleted successfully.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Delete Group'
        return context


class GroupMemberManageView(GroupAdminRequiredMixin, UpdateView):
    model = Group
    form_class = GroupMemberForm
    template_name = 'groups/group_member_manage.html'
    context_object_name = 'group'

    def get_success_url(self):
        return reverse_lazy('group_detail', kwargs={'pk': self.object.pk})

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(
            data=self.request.POST if self.request.method == 'POST' else None,
            files=self.request.FILES if self.request.method == 'POST' else None,
            group=self.get_object()
        )

    def form_valid(self, form):
        group = self.get_object()
        selected_members = form.cleaned_data['members']

        if group.admin not in selected_members:
            selected_members = list(selected_members) + [group.admin]

        current_members = [m.user for m in group.members.exclude(user=group.admin)]

        members_to_add = set(selected_members) - set(current_members)
        for user_to_add in members_to_add:
            if user_to_add != group.admin:
                Membership.objects.get_or_create(group=group, user=user_to_add)

        members_to_remove = set(current_members) - set(selected_members)
        for user_to_remove in members_to_remove:
            Membership.objects.filter(group=group, user=user_to_remove).delete()

        messages.success(self.request, f'Members for group "{group.name}" updated successfully.')
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Manage Members for "{self.object.name}"'
        return context