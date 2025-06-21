from django.urls import path
from .views import RegisterView, CustomLoginView, CustomLogoutView, ForgotPasswordView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('forgot_password/', ForgotPasswordView.as_view(), name='forgot_password'),
]
