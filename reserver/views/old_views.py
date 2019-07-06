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

def path_to_qr_view(request, b64_path):
	qr = pyqrcode.create("http://"+request.META['HTTP_HOST']+str(base64.b64decode(b64_path), "utf-8 "))
	buffer = io.BytesIO()
	qr.png(buffer, scale=15)
	return HttpResponse(buffer.getvalue(), content_type="image/png")

def index_view(request):
	if request.user.is_authenticated():
		if not request.user.userdata.email_confirmed and request.user.userdata.role == "":
			messages.add_message(request, messages.WARNING, mark_safe("You have not yet confirmed your email address. Your account will not be eligible for approval or submitting cruises before this is done. If you typed the wrong email address while signing up, correct it in your profile and we'll send you a new one. You may have to add no-reply@rvgunnerus.no to your contact list if our messages go to spam."+"<br><br><a class='btn btn-primary' href='"+reverse('resend-activation-mail')+"'>Resend activation email</a>"))
		elif request.user.userdata.email_confirmed and request.user.userdata.role == "":
			messages.add_message(request, messages.WARNING, "Your user account has not been approved by an administrator yet. You may save cruise drafts and edit them, but you may not submit cruises for approval before your account is approved.")
	return render(request, 'reserver/index.html')

def login_redirect(request):
	redirect_target = reverse_lazy('home')
	if request.user.is_authenticated():
		if request.user.userdata.role == "invoicer":
			redirect_target = reverse_lazy('invoicer-overview')
		elif request.user.userdata.role == "admin":
			redirect_target = reverse_lazy('admin')
	else:
		raise PermissionDenied
	return redirect(redirect_target)

#Methods for automatically creating and deleting notifications related to cruises and seasons when they are created

cruise_deadline_email_templates = {
	'16 days missing info',
	'Last cancellation date',
}

cruise_administration_email_templates = {
	'Cruise dates approved',
	'Cruise information approved',
	'Cruise rejected',
	'Cruise unapproved',
	'Cruise information unapproved',
}

cruise_departure_email_templates = {
	'1 week until departure',
	'2 weeks until departure',
	'Departure tomorrow',
}

season_email_templates = {
	'Internal season opening',
	'External season opening'
}

#To be run when a cruise is submitted, and the cruise and/or its information is approved. Takes cruise and template group as arguments to decide which cruise to make which notifications for
def create_cruise_notifications(cruise, template_group):
	templates = list(EmailTemplate.objects.filter(group=template_group))
	cruise_day_event = CruiseDay.objects.filter(cruise=cruise).order_by('event__start_time').first().event
	notifs = []
	delete_cruise_notifications(cruise, template_group)
	for template in templates:
		notif = EmailNotification()
		notif.event = cruise_day_event
		notif.template = template
		notif.save()
		notifs.append(notif)
	jobs.create_jobs(jobs.scheduler, notifs)
	jobs.scheduler.print_jobs()

#To be run when a cruise is approved
def create_cruise_administration_notification(cruise, template, **kwargs):
	cruise_day_event = CruiseDay.objects.filter(cruise=cruise).order_by('event__start_time').first().event
	notif = EmailNotification()
	if kwargs.get("message"):
		notif.extra_message = kwargs.get("message")
	else:
		notif.extra_message = ""
	notif.event = cruise_day_event
	notif.template = EmailTemplate.objects.get(title=template)
	notif.save()
	jobs.create_jobs(jobs.scheduler, [notif])

#To be run when a cruise's information is approved, and the cruise goes from being unapproved to approved
def create_cruise_deadline_and_departure_notifications(cruise):
	create_cruise_notifications(cruise, 'Cruise deadlines')
	create_cruise_notifications(cruise, 'Cruise departure')
	create_cruise_notifications(cruise, 'Admin deadline notice') #Does not match existing template group, so does nothing

#To be run when a cruise or its information is unapproved
def delete_cruise_notifications(cruise, template_group): #See models.py for Email_Template groups
	cruise_event = CruiseDay.objects.filter(cruise=cruise).order_by('event__start_time').first().event
	all_notifications = EmailNotification.objects.filter(event=cruise_event)
	deadline_notifications = all_notifications.filter(template__group=template_group)
	for notif in deadline_notifications:
		notif.delete()
	jobs.restart_scheduler()

#To be run when a cruise is unapproved
def delete_cruise_deadline_notifications(cruise):
	delete_cruise_notifications(cruise, 'Cruise deadlines')
	delete_cruise_notifications(cruise, 'Admin deadline notice')

#To be run when a cruise's information is unapproved or the cruise is unapproved
def delete_cruise_departure_notifications(cruise,  template_group='Cruise departure'):
	delete_cruise_notifications(cruise, template_group)

#To be run when a cruise is unapproved while its information is approved
def delete_cruise_deadline_and_departure_notifications(cruise):
	delete_cruise_notifications(cruise, 'Cruise deadlines')
	delete_cruise_notifications(cruise, 'Cruise departure')

#To be run when a new season is made
def create_season_notifications(season):
	season_event = season.season_event

	internal_opening_event = season.internal_order_event
	if (internal_opening_event.start_time > timezone.now()):
		internal_notification = EmailNotification()
		internal_notification.event = internal_opening_event
		internal_notification.template = EmailTemplate.objects.get(title="Internal season opening")
		internal_notification.save()
		jobs.create_jobs(jobs.scheduler, [internal_notification])

	external_opening_event = season.external_order_event
	if (external_opening_event.start_time > timezone.now()):
		external_notification = EmailNotification()
		external_notification.event = external_opening_event
		external_notification.template = EmailTemplate.objects.get(title="External season opening")
		external_notification.save()
		jobs.create_jobs(jobs.scheduler, [external_notification])

#To be run when a season is changed/deleted
def delete_season_notifications(season):
	internal_opening_event = season.internal_order_event
	external_opening_event = season.external_order_event
	internal_notifications = EmailNotification.objects.filter(event=internal_opening_event, template__title="Internal season opening")
	external_notifications = EmailNotification.objects.filter(event=external_opening_event, template__title="External season opening")
	for notif in internal_notifications:
		notif.delete()
	for notif in external_notifications:
		notif.delete()
	jobs.restart_scheduler()

#To be run when a season is changed

def get_cruise_pdf(request, pk):
	return "Not implemented"

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

def admin_view(request):
	last_actions = list(Action.objects.filter(timestamp__lte=timezone.now(), timestamp__gt=timezone.now()-datetime.timedelta(days=30)))[:-4:-1]
	cruises_need_attention = get_cruises_need_attention()
	upcoming_cruises = get_upcoming_cruises()
	unapproved_cruises = get_unapproved_cruises()
	users_not_approved = get_users_not_approved()
	current_year = timezone.now().year
	next_year = timezone.now().year+1
	internal_days_remaining = 150-CruiseDay.objects.filter(event__start_time__year = current_year, cruise__is_approved = True, cruise__leader__userdata__organization__is_NTNU = True).count()
	external_days_remaining = 30-CruiseDay.objects.filter(event__start_time__year = current_year, cruise__is_approved = True, cruise__leader__userdata__organization__is_NTNU = False).count()
	internal_days_remaining_next_year = 150-CruiseDay.objects.filter(event__start_time__year = next_year, cruise__is_approved = True, cruise__leader__userdata__organization__is_NTNU = True).count()
	external_days_remaining_next_year = 30-CruiseDay.objects.filter(event__start_time__year = next_year, cruise__is_approved = True, cruise__leader__userdata__organization__is_NTNU = False).count()
	if(len(cruises_need_attention) > 1):
		messages.add_message(request, messages.WARNING, mark_safe(('<i class="fa fa-exclamation-triangle" aria-hidden="true"></i> %s approved cruises have not had their information approved yet.' % str(len(cruises_need_attention)))+"<br><br><a class='btn btn-primary' href='#approved-cruises-needing-attention'><i class='fa fa-arrow-down' aria-hidden='true'></i> Jump to cruises</a>"))
	elif(len(cruises_need_attention) == 1):
		messages.add_message(request, messages.WARNING, mark_safe('<i class="fa fa-exclamation-triangle" aria-hidden="true"></i> An approved cruise has not had its information approved yet.'+"<br><br><a class='btn btn-primary' href='#approved-cruises-needing-attention'><i class='fa fa-arrow-down' aria-hidden='true'></i> Jump to cruise</a>"))
	if(len(users_not_approved) > 1):
		messages.add_message(request, messages.INFO, mark_safe(('<i class="fa fa-info-circle" aria-hidden="true"></i> %s users need attention.' % str(len(users_not_approved)))+"<br><br><a class='btn btn-primary' href='#users-needing-attention'><i class='fa fa-arrow-down' aria-hidden='true'></i> Jump to users</a>"))
	elif(len(users_not_approved) == 1):
		messages.add_message(request, messages.INFO, mark_safe('<i class="fa fa-info-circle" aria-hidden="true"></i> A user needs attention.'+"<br><br><a class='btn btn-primary' href='#users-needing-attention'><i class='fa fa-arrow-down' aria-hidden='true'></i> Jump to user</a>"))
	if(len(unapproved_cruises) > 1):
		messages.add_message(request, messages.INFO, mark_safe(('<i class="fa fa-info-circle" aria-hidden="true"></i> %s cruises are awaiting approval.' % str(len(unapproved_cruises)))+"<br><br><a class='btn btn-primary' href='#unapproved-cruises-needing-attention'><i class='fa fa-arrow-down' aria-hidden='true'></i> Jump to cruises</a>"))
	elif(len(unapproved_cruises) == 1):
		messages.add_message(request, messages.INFO, mark_safe('<i class="fa fa-info-circle" aria-hidden="true"></i> A cruise is awaiting approval.'+"<br><br><a class='btn btn-primary' href='#unapproved-cruises-needing-attention'><i class='fa fa-arrow-down' aria-hidden='true'></i> Jump to cruise</a>"))
	return render(request, 'reserver/admin_overview.html', {'unapproved_cruises':unapproved_cruises, 'upcoming_cruises':upcoming_cruises, 'cruises_need_attention':cruises_need_attention, 'users_not_verified':users_not_approved, 'internal_days_remaining':internal_days_remaining, 'external_days_remaining':external_days_remaining, 'internal_days_remaining_next_year':internal_days_remaining_next_year, 'external_days_remaining_next_year':external_days_remaining_next_year, 'current_year':current_year, 'next_year':next_year, 'last_actions':last_actions})

def admin_cruise_view(request):
	cruises = list(Cruise.objects.filter(is_approved=True).order_by('-cruise_start'))
	cruises_need_attention = get_cruises_need_attention()
	if(len(cruises_need_attention) > 1):
		messages.add_message(request, messages.WARNING, mark_safe(('<i class="fa fa-exclamation-triangle" aria-hidden="true"></i> %s upcoming cruises have not had their information approved yet.' % str(len(cruises_need_attention)))+"<br><br><a class='btn btn-primary' href='"+reverse('admin')+"#approved-cruises-needing-attention'><i class='fa fa-arrow-right' aria-hidden='true'></i> Jump to cruises</a>"))
	elif(len(cruises_need_attention) == 1):
		messages.add_message(request, messages.WARNING, mark_safe('<i class="fa fa-exclamation-triangle" aria-hidden="true"></i> An upcoming cruise has not had its information approved yet.'+"<br><br><a class='btn btn-primary' href='"+reverse('admin')+"#approved-cruises-needing-attention'><i class='fa fa-arrow-right' aria-hidden='true'></i> Jump to cruise</a>"))
	return render(request, 'reserver/admin_cruises.html', {'cruises':cruises})

def admin_user_view(request):
	users = list(UserData.objects.exclude(role="").order_by('-role', 'user__last_name', 'user__first_name'))
	users_not_approved = get_users_not_approved()
	if(len(users_not_approved) > 1):
		messages.add_message(request, messages.INFO, mark_safe(('<i class="fa fa-info-circle" aria-hidden="true"></i> %s users need attention.' % str(len(users_not_approved)))+"<br><br><a class='btn btn-primary' href='"+reverse('admin')+"#users-needing-attention'><i class='fa fa-arrow-right' aria-hidden='true'></i> Jump to users</a>"))
	elif(len(users_not_approved) == 1):
		messages.add_message(request, messages.INFO, mark_safe('<i class="fa fa-info-circle" aria-hidden="true"></i> A user needs attention.'+"<br><br><a class='btn btn-primary' href='"+reverse('admin')+"#users-needing-attention'><i class='fa fa-arrow-right' aria-hidden='true'></i> Jump to user</a>"))
	return render(request, 'reserver/admin_users.html', {'users':users})

from hijack.signals import hijack_started, hijack_ended

def log_hijack_started(sender, hijacker_id, hijacked_id, request, **kwargs):
	user = User.objects.get(id=hijacker_id)
	target_user = User.objects.get(id=hijacked_id)
	action = Action(user=user, target=str(target_user))
	action.action = "took control of user"
	action.timestamp = timezone.now()
	action.save()

hijack_started.connect(log_hijack_started)

def log_hijack_ended(sender, hijacker_id, hijacked_id, request, **kwargs):
	user = User.objects.get(id=hijacker_id)
	target_user = User.objects.get(id=hijacked_id)
	action = Action(user=user, target=str(target_user))
	action.action = "released control of user"
	action.timestamp = timezone.now()
	action.save()

hijack_ended.connect(log_hijack_ended)

class UserDataEditView(UpdateView):
	model = UserData
	template_name = 'reserver/userdata_edit_form.html'
	form_class = AdminUserDataForm

	def get_success_url(self):
		return reverse_lazy('admin-users')

def admin_actions_view(request):
	actions = Action.objects.all()
	actions = actions[::-1]
	paginator = Paginator(actions, 20)
	page = request.GET.get('page')
	try:
		page_actions = paginator.page(page)
	except PageNotAnInteger:
		# If page is not an integer, deliver first page.
		page_actions = paginator.page(1)
	except EmptyPage:
		# If page is out of range (e.g. 9999), deliver last page of results.
		page_actions = paginator.page(paginator.num_pages)

	return render(request, 'reserver/admin_actions.html', {'actions':page_actions})

def admin_statistics_view(request):
	#last_statistics = list(Statistics.objects.filter(timestamp__lte=timezone.now(), timestamp__gt=timezone.now()-datetime.timedelta(days=30)))
	last_statistics = list(Statistics.objects.filter(timestamp__lte=timezone.now()))
	seen_timestamps = set()
	unique_statistics = []
	for statistic in last_statistics:
		if statistic.timestamp.strftime('%Y-%m-%d') not in seen_timestamps:
			unique_statistics.append(statistic)
			seen_timestamps.add(statistic.timestamp.strftime('%Y-%m-%d'))
	operation_years = []
	for season in Season.objects.all():
		season_start_year = season.season_event.start_time.year
		season_end_year = season.season_event.end_time.year
		if season_start_year not in operation_years:
			operation_years.append(season_start_year)
		if season_end_year not in operation_years:
			operation_years.append(season_end_year)

	unique_statistics.reverse()

	paginator = Paginator(unique_statistics, 20)
	page = request.GET.get('page')
	try:
		page_statistics = paginator.page(page)
	except PageNotAnInteger:
		# If page is not an integer, deliver first page.
		page_statistics = paginator.page(1)
	except EmptyPage:
		# If page is out of range (e.g. 9999), deliver last page of results.
		page_statistics = paginator.page(paginator.num_pages)

	return render(request, 'reserver/admin_statistics.html', {'statistics':page_statistics})

def admin_work_hour_view(request, **kwargs):
	if (request.user.is_superuser):
		template = "reserver/admin_work_hours.html"

		seasons = Season.objects.all()
		years = []

		# default: use the current year
		year = datetime.datetime.strftime(timezone.now(), '%Y')
		years.append(year)

		for season in seasons:
			years.append(season.season_event.start_time.strftime("%Y"))
			years.append(season.season_event.end_time.strftime("%Y"))

		years = reversed(sorted(list(set(years))))

		if kwargs.get("year"):
			year = kwargs.get("year")

		start_date = timezone.make_aware(datetime.datetime.strptime(year+"-01-01", '%Y-%m-%d'))
		end_date = timezone.make_aware(datetime.datetime.strptime(year+"-12-31", '%Y-%m-%d'))

		invoices = InvoiceInformation.objects.filter(is_paid=True, cruise__cruise_end__lte=end_date+datetime.timedelta(days=1), cruise__cruise_start__gte=start_date-datetime.timedelta(days=1)).order_by('cruise__cruise_start') # is_finalized=True
		crew_users = User.objects.filter(is_staff=True)

	else:
		raise PermissionDenied

	return render(request,
		template,
		{
			'selected_year': year,
			'years': years,
			'crew_users': crew_users
		}
	)

def food_view(request, pk):
	cruise = Cruise.objects.get(pk=pk)
	days = list(CruiseDay.objects.filter(cruise=cruise.pk))
	return render(request, 'reserver/food.html', {'cruise':cruise, 'days':days})

def login_view(request):
	return render(request, 'reserver/login.html')