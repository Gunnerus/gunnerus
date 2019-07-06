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

def admin_eventcategory_view(request):
	from reserver.utils import check_default_models
	check_default_models()
	eventcategories = list(EventCategory.objects.all())

	return render(request, 'reserver/admin_eventcategories.html', {'eventcategories':eventcategories})

class CreateEventCategory(CreateView):
	model = EventCategory
	template_name = 'reserver/eventcategory_create_form.html'
	form_class = EventCategoryNonDefaultForm

	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "created event category"
		action.save()
		return reverse_lazy('eventcategories')

class EventCategoryEditView(UpdateView):
	model = EventCategory
	template_name = 'reserver/eventcategory_edit_form.html'

	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		self.object = get_object_or_404(EventCategory, pk=self.kwargs.get('pk'))
		if self.object.is_default:
			action.action = "edited built-in event category"
		else:
			action.action = "edited event category"
		action.save()
		return reverse_lazy('eventcategories')

	def get_form_class(self):
		self.object = get_object_or_404(EventCategory, pk=self.kwargs.get('pk'))
		if self.object.is_default:
			return EventCategoryForm
		else:
			return EventCategoryNonDefaultForm

class EventCategoryDeleteView(DeleteView):
	model = EventCategory
	template_name = 'reserver/eventcategory_delete_form.html'

	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "deleted event category"
		action.save()
		return reverse_lazy('eventcategories')

# Simple version with no feedback, only resets the object and refreshes the page.
def event_category_reset_view(request, pk):
	from reserver.utils import default_event_categories
	event_category = get_object_or_404(EventCategory, pk=pk)
	default = next(df for df in default_event_categories if df[0] == event_category.name)
	event_category.name = default[0]
	event_category.icon = default[1]
	event_category.colour = default[2]
	event_category.description = default[3]
	event_category.is_default = True
	event_category.save()
	action = Action(user=request.user, timestamp=timezone.now(), target=str(event_category))
	action.action = "reset event category to default"
	action.save()
	messages.add_message(request, messages.SUCCESS, mark_safe('The contents of the event category "' + str(event_category) + '" was reset to its default values.'))
	return HttpResponseRedirect(reverse_lazy('eventcategories'))