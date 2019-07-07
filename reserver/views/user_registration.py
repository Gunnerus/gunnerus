from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.core.exceptions import PermissionDenied
from django.utils.encoding import force_text
from django.utils.http import urlsafe_base64_decode

from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import login

from django.http import HttpResponseRedirect

from reserver.utils import send_activation_email
from reserver.utils import account_activation_token

from reserver.models import EmailTemplate
from reserver.forms import UserRegistrationForm, UserDataForm

from reserver.jobs import send_template_only_email

def register_view(request):
	user_form = UserRegistrationForm(request.POST or None)
	userdata_form = UserDataForm(request.POST or None)
	if request.method == 'POST':
		if (userdata_form.is_valid() and user_form.is_valid()):
			user = user_form.save()
			user.is_active = True
			user.save()
			ud = userdata_form.save(commit=False)
			ud.user = user
			ud.email_confirmed = False
			ud.save()
			send_activation_email(request, user)
			return HttpResponseRedirect(reverse_lazy('home'))
	return render(request, 'reserver/user_registration/register.html', {'userdata_form':userdata_form, 'user_form':user_form})

def send_activation_email_view(request):
	if request.user.is_authenticated():
		send_activation_email(request, request.user)
	else:
		raise PermissionDenied
	return HttpResponseRedirect(reverse_lazy('home'))

def activate_view(request, uidb64, token):
	try:
		uid = force_text(urlsafe_base64_decode(uidb64))
		user = User.objects.get(pk=uid)
	except (TypeError, ValueError, OverflowError, User.DoesNotExist):
		user = None

	if user is not None and account_activation_token.check_token(user, token):
		user.userdata.email_confirmed = True
		user.userdata.save()
		login(request, user)
		messages.add_message(request, messages.SUCCESS, "Your account's email address has been confirmed!")
		# Sends notification mail to admins about a new user.
		admin_user_emails = [admin_user.email for admin_user in list(User.objects.filter(userdata__role='admin'))]
		send_template_only_email(admin_user_emails, EmailTemplate.objects.get(title='New user'), user=user)
		return redirect('home')
	else:
		raise PermissionDenied
