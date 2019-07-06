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

def admin_event_view(request):
	off_day_event_category = EventCategory.objects.get(name="Red day")
	cruise_day_event_category = EventCategory.objects.get(name="Cruise day")
	all_events = list(Event.objects.all().exclude(category=cruise_day_event_category).exclude(category=off_day_event_category))
	events = []
	for event in all_events:
		if event.is_scheduled_event():
			events.append(event)

	return render(request, 'reserver/admin_events.html', {'events':events})

def event_overview(request, **kwargs):
	if request.user.is_superuser:
		has_dates_selected = False
		start_date_string = ""
		end_date_string = ""
		events = []

		if kwargs.get("start_date") and kwargs.get("end_date"):
			has_dates_selected = True
			start_date_string = kwargs.get("start_date")
			end_date_string = kwargs.get("end_date")

			start_date = timezone.make_aware(datetime.datetime.strptime(start_date_string, '%Y-%m-%d'))
			end_date = timezone.make_aware(datetime.datetime.strptime(end_date_string, '%Y-%m-%d'))
			if start_date > end_date:
				# swap dates
				temp_date = start_date
				start_date = end_date
				end_date = temp_date

				temp_date_string = start_date_string
				start_date_string = end_date_string
				end_date_string = temp_date_string

			events = get_events_in_period(start_date, end_date)
			events = filter(filter_events, events)
		else:
			messages.add_message(request, messages.INFO, mark_safe('<i class="fa fa-info-circle" aria-hidden="true"></i> Event overview'))
	else:
		raise PermissionDenied

	return render(request,
		"reserver/admin_event_overview.html",
		{
			'days': get_days_with_events(events),
			'has_dates_selected': has_dates_selected,
			'start_date': start_date_string,
			'end_date': end_date_string,
		}
	)

def event_overview_pdf(request, **kwargs):
	if request.user.is_superuser:
		start_date_string = ""
		end_date_string = ""
		events = []

		if kwargs.get("start_date") and kwargs.get("end_date"):
			has_dates_selected = True
			start_date_string = kwargs.get("start_date")
			end_date_string = kwargs.get("end_date")

			start_date = timezone.make_aware(datetime.datetime.strptime(start_date_string, '%Y-%m-%d')).replace(hour=0, minute=0, second=0)
			end_date = timezone.make_aware(datetime.datetime.strptime(end_date_string, '%Y-%m-%d')).replace(hour=23, minute=59, second=59)
			if start_date > end_date:
				# swap dates
				temp_date = start_date
				start_date = end_date
				end_date = temp_date

				temp_date_string = start_date_string
				start_date_string = end_date_string
				end_date_string = temp_date_string

			events = get_events_in_period(start_date, end_date)
			events = filter(filter_events, events)
		else:
			messages.add_message(request, messages.INFO, mark_safe('<i class="fa fa-info-circle" aria-hidden="true"></i> Event overview'))
			return render(request,
				"reserver/admin_event_overview.html",
				{
					'days': get_days_with_events(events),
					'has_dates_selected': has_dates_selected,
					'start_date': start_date_string,
					'end_date': end_date_string,
				}
			)
	else:
		raise PermissionDenied

	context = {
		'pagesize': 'A4',
		'title': 'Period summary for ' + start_date.strftime('%d.%m.%Y') + ' to ' + end_date.strftime('%d.%m.%Y'),
		'days': get_days_with_events(events),
		'start_date': start_date,
		'end_date': end_date,
		'http_host': request.META['HTTP_HOST']
	}

	return render_to_pdf_response(
		request,
		'reserver/pdfs/event_overview_pdf.html',
		context,
		download_filename='event_summary_for_' + str(start_date_string) + '_to_' + str(end_date_string) + '.pdf'
	)

class CreateEvent(CreateView):
	model = Event
	template_name = 'reserver/event_create_form.html'
	form_class = EventForm

	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "created event"
		action.save()
		return reverse_lazy('events')

class EventEditView(UpdateView):
	model = Event
	template_name = 'reserver/event_edit_form.html'
	form_class = EventForm

	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "edited event"
		action.save()
		return reverse_lazy('events')

class EventDeleteView(DeleteView):
	model = Event
	template_name = 'reserver/event_delete_form.html'

	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "deleted event"
		action.save()
		return reverse_lazy('events')
