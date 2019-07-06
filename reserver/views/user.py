from django.shortcuts import get_list_or_404, get_object_or_404, render, redirect
from django.db.models import Q
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.views.generic import ListView
from django.contrib.auth.decorators import login_required
from django.views.generic.detail import SingleObjectMixin
from django.contrib import messages
from django.utils.safestring import mark_safe
from reserver.utils import render_add_cal_button, account_activation_token
from django.utils.encoding import force_text
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes
from django.utils import six
import os, tempfile, zipfile
from django.http import HttpResponse
from wsgiref.util import FileWrapper
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from easy_pdf.views import PDFTemplateView
from easy_pdf.rendering import html_to_pdf, make_response, render_to_pdf_response
from django.utils.decorators import method_decorator
from django import template
import pyqrcode
import io
import base64

from reserver.utils import check_for_and_fix_users_without_userdata, send_user_approval_email
from reserver.models import *
from reserver.forms import *
from reserver.test_models import create_test_models
from reserver import jobs
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail, get_connection

from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.template import loader
from django.utils import timezone
from reserver.utils import init, send_activation_email
import datetime
import json
from reserver.jobs import send_email, send_template_only_email
from django.conf import settings

class UserView(UpdateView):
	template_name = 'reserver/user.html'
	model = User
	form_class = UserForm
	slug_field = "username"
	success_url = reverse_lazy('user-page')

	def post(self, request, *args, **kwargs):
		messages.add_message(request, messages.SUCCESS, "Profile updated.")
		return super(UserView, self).post(request, *args, **kwargs)

	def get_form_kwargs(self):
		kwargs = super(UserView, self).get_form_kwargs()
		kwargs.update({'request': self.request})
		return kwargs

	def get_context_data(self, **kwargs):
		context = super(UserView, self).get_context_data(**kwargs)

		if not self.request.user.userdata.email_confirmed and self.request.user.userdata.role == "":
			messages.add_message(self.request, messages.WARNING, mark_safe("You have not yet confirmed your email address. Your account will not be eligible for approval or submitting cruises before this is done. If you typed the wrong email address while signing up, correct it in the form below and we'll send you a new one. You may have to add no-reply@rvgunnerus.no to your contact list if our messages go to spam."+"<br><br><a class='btn btn-primary' href='"+reverse('resend-activation-mail')+"'>Resend activation email</a>"))
		elif self.request.user.userdata.email_confirmed and self.request.user.userdata.role == "":
			messages.add_message(self.request, messages.WARNING, "Your user account has not been approved by an administrator yet. You may save cruise drafts and edit them, but you may not submit cruises for approval before your account is approved.")

		# add submitted cruises to context
		submitted_cruises = list(set(list(Cruise.objects.filter(leader=self.request.user, is_submitted=True) | Cruise.objects.filter(owner=self.request.user, is_submitted=True))))
		context['my_submitted_cruises'] = sorted(list(submitted_cruises), key=lambda x: str(x.cruise_start), reverse=True)

		# add unsubmitted cruises to context
		unsubmitted_cruises = list(set(list(Cruise.objects.filter(leader=self.request.user, is_submitted=False) | Cruise.objects.filter(owner=self.request.user, is_submitted=False))))
		context['my_unsubmitted_cruises'] = sorted(list(unsubmitted_cruises), key=lambda x: str(x.cruise_start), reverse=True)
		return context

class CurrentUserView(UserView):
	def get_object(self):
		return self.request.user

def set_as_admin(request, pk):
	user = get_object_or_404(User, pk=pk)
	if request.user.is_superuser:
		user.is_staff = True
		user.is_admin = True
		user.is_superuser = True
		try:
			user_data = user.userdata
		except UserData.DoesNotExist:
			user_data = UserData()
			user_data.user = user
			user_data.save()
		old_role = user_data.role
		user_data.role = "admin"
		user.is_staff = True
		user.is_superuser = True
		user_data.save()
		user.save()
		action = Action(user=request.user, target=str(user))
		action.action = "set user as admin"
		action.timestamp = timezone.now()
		action.save()
		Cruise.objects.filter(leader=user).update(missing_information_cache_outdated=True)
		messages.add_message(request, messages.WARNING, mark_safe('User ' + str(user) + ' set as admin.'))
		if old_role == "":
			send_user_approval_email(request, user)
	else:
		raise PermissionDenied
	return redirect(request.META['HTTP_REFERER'])

def set_as_internal(request, pk):
	user = get_object_or_404(User, pk=pk)
	if request.user.is_superuser:
		try:
			user_data = user.userdata
		except UserData.DoesNotExist:
			user_data = UserData()
			user_data.user = user
			user_data.save()
		old_role = user_data.role
		user_data.role = "internal"
		user.is_staff = False
		user.is_superuser = False
		user.save()
		user_data.save()
		action = Action(user=request.user, target=str(user))
		action.action = "set user as internal user"
		action.timestamp = timezone.now()
		action.save()
		Cruise.objects.filter(leader=user).update(missing_information_cache_outdated=True)
		messages.add_message(request, messages.SUCCESS, mark_safe('User ' + str(user) + ' set as internal user.'))
		if old_role == "":
			send_user_approval_email(request, user)
	else:
		raise PermissionDenied
	return redirect(request.META['HTTP_REFERER'])

def toggle_user_crew_status(request, pk):
	# is_staff is internally used to mark crew members for the off hour calculation view.
	user = get_object_or_404(User, pk=pk)
	if request.user.is_superuser:
		action = Action(user=request.user, target=str(user))
		if user.is_staff:
			user.is_staff = False
			action.action = "set user as not crew"
			messages.add_message(request, messages.SUCCESS, mark_safe('User ' + str(user) + ' set as not crew.'))
		else:
			user.is_staff = True
			action.action = "set user as crew"
			messages.add_message(request, messages.SUCCESS, mark_safe('User ' + str(user) + ' set as crew.'))
		user.save()
		action.timestamp = timezone.now()
		action.save()
	else:
		raise PermissionDenied
	return redirect(request.META['HTTP_REFERER'])

def set_as_invoicer(request, pk):
	user = get_object_or_404(User, pk=pk)
	if request.user.is_superuser:
		try:
			user_data = user.userdata
		except UserData.DoesNotExist:
			user_data = UserData()
			user_data.user = user
			user_data.save()
		old_role = user_data.role
		user_data.role = "invoicer"
		user.is_staff = False
		user.is_superuser = False
		user.save()
		user_data.save()
		action = Action(user=request.user, target=str(user))
		action.action = "set user as invoicer"
		action.timestamp = timezone.now()
		action.save()
		Cruise.objects.filter(leader=user).update(missing_information_cache_outdated=True)
		messages.add_message(request, messages.SUCCESS, mark_safe('User ' + str(user) + ' set as invoicer.'))
		if old_role == "":
			send_user_approval_email(request, user)
	else:
		raise PermissionDenied
	return redirect(request.META['HTTP_REFERER'])

def set_as_external(request, pk):
	user = get_object_or_404(User, pk=pk)
	if request.user.is_superuser:
		try:
			user_data = user.userdata
		except UserData.DoesNotExist:
			user_data = UserData()
			user_data.user = user
			user_data.save()
		old_role = user_data.role
		user_data.role = "external"
		user.is_staff = False
		user.is_superuser = False
		user.save()
		user_data.save()
		action = Action(user=request.user, target=str(user))
		action.action = "set user as external"
		action.timestamp = timezone.now()
		action.save()
		Cruise.objects.filter(leader=user).update(missing_information_cache_outdated=True)
		messages.add_message(request, messages.SUCCESS, mark_safe('User ' + str(user) + ' set as external user.'))
		if old_role == "":
			send_user_approval_email(request, user)
	else:
		raise PermissionDenied
	return redirect(request.META['HTTP_REFERER'])

def delete_user(request, pk):
	user = get_object_or_404(User, pk=pk)
	if request.user.is_superuser:
		user.userdata.role = ""
		user.is_active = False
		user.userdata.save()
		user.save()
		action = Action(user=request.user, target=str(user))
		action.action = "deleted user"
		action.timestamp = timezone.now()
		action.save()
		Cruise.objects.filter(leader=user).update(missing_information_cache_outdated=True)
		messages.add_message(request, messages.WARNING, mark_safe('User ' + str(user) + ' deleted.'))
	else:
		raise PermissionDenied
	return redirect(request.META['HTTP_REFERER'])
