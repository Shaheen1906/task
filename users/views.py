# users/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import CreateView, TemplateView
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth import login
from django.urls import reverse_lazy
from .forms import UserRegisterForm, UserLoginForm # Import our custom forms
from django.contrib import messages # For displaying messages to the user

# Class-based view for user registration
class RegisterView(CreateView):
    form_class = UserRegisterForm # Use our custom registration form
    template_name = 'users/register.html'
    success_url = reverse_lazy('login') # Redirect to login page after successful registration

    def form_valid(self, form):
        user = form.save()
        login(self.request, user) # Log the user in immediately after registration
        messages.success(self.request, 'Account created successfully! You are now logged in.')
        return redirect('home') # Redirect to home page after login

    def form_invalid(self, form):
        messages.error(self.request, 'Error creating account. Please correct the errors below.')
        return super().form_invalid(form)

# Class-based view for user login
class CustomLoginView(LoginView):
    authentication_form = UserLoginForm # Use our custom login form
    template_name = 'users/login.html'
    redirect_authenticated_user = True # Redirect authenticated users trying to access login page

    def form_valid(self, form):
        messages.success(self.request, f'Welcome back, {self.request.user.username}!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Invalid username or password.')
        return super().form_invalid(form)

# Class-based view for user logout
class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('login') # Redirect to login page after logout

    def dispatch(self, request, *args, **kwargs):
        messages.info(request, 'You have been successfully logged out.')
        return super().dispatch(request, *args, **kwargs)

# View for Forgot Password (basic implementation for now, will expand with email functionality later)
class ForgotPasswordView(TemplateView):
    template_name = 'users/forgot_password.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PasswordResetForm()
        return context

    def post(self, request, *args, **kwargs):
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            # In a real application, you would send an email with a reset link here.
            # For now, we'll just simulate success.
            messages.success(request, 'If an account with that email exists, a password reset link has been sent.')
            return redirect('login')
        else:
            messages.error(request, 'Please enter a valid email address.')
            return render(request, self.template_name, {'form': form})
