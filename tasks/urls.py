# tasks/urls.py

from django.urls import path
from .views import (
    TaskListView, TaskCreateView, TaskUpdateView, TaskMarkCompleteView,
    GroupListView, GroupCreateView, GroupDetailView, GroupUpdateView, GroupDeleteView,
    GroupMemberManageView
)

urlpatterns = [
    # Task URLs
    path('', TaskListView.as_view(), name='task_list'),
    path('create/', TaskCreateView.as_view(), name='task_create'),
    # Add a create task link that takes group_id for context
    path('create/for_group/<uuid:group_id>/', TaskCreateView.as_view(), name='task_create_for_group'),
    path('<uuid:pk>/edit/', TaskUpdateView.as_view(), name='task_edit'),
    # path('<uuid:pk>/delete/', TaskDeleteView.as_view(), name='task_delete'),
    path('<uuid:pk>/complete/', TaskMarkCompleteView.as_view(), name='task_complete'),

    # Group URLs
    path('groups/', GroupListView.as_view(), name='group_list'),
    path('groups/create/', GroupCreateView.as_view(), name='group_create'),
    path('groups/<uuid:pk>/', GroupDetailView.as_view(), name='group_detail'), # New detail view
    path('groups/<uuid:pk>/edit/', GroupUpdateView.as_view(), name='group_edit'), # New edit view
    path('groups/<uuid:pk>/delete/', GroupDeleteView.as_view(), name='group_delete'), # New delete view
    path('groups/<uuid:pk>/members/', GroupMemberManageView.as_view(), name='group_members_manage'), # New member management
]
