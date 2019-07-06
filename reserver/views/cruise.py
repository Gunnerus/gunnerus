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

class CruiseList(ListView):
	model = Cruise
	template_name = 'reserver/cruise_list.html'

class CruiseCreateView(CreateView):
	template_name = 'reserver/cruise_create_form.html'
	model = Cruise
	form_class = CruiseForm

	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "created cruise"
		action.save()
		return reverse_lazy('user-page')

	def get_form_kwargs(self):
		kwargs = super(CruiseCreateView, self).get_form_kwargs()
		kwargs.update({'request': self.request})
		return kwargs

	def get(self, request, *args, **kwargs):
		"""Handles creation of new blank form/formset objects."""
		self.object = None
		form_class = self.get_form_class()
		form_class.user = request.user
		form = self.get_form(form_class)
		cruiseday_form = CruiseDayFormSet()
		participant_form = ParticipantFormSet()
		document_form = DocumentFormSet()
		equipment_form = EquipmentFormSet()
		invoice_form = InvoiceFormSet()

		if not self.request.user.userdata.email_confirmed and self.request.user.userdata.role == "":
			messages.add_message(self.request, messages.WARNING, mark_safe("You have not yet confirmed your email address. Your account will not be eligible for approval or submitting cruises before this is done. If you typed the wrong email address while signing up, correct it in your profile and we'll send you a new one. You may have to add no-reply@rvgunnerus.no to your contact list if our messages go to spam."+"<br><br><a class='btn btn-primary' href='"+reverse('resend-activation-mail')+"'>Resend activation email</a>"))
		elif self.request.user.userdata.email_confirmed and self.request.user.userdata.role == "":
			messages.add_message(self.request, messages.WARNING, "Your user account has not been approved by an administrator yet. You may save cruise drafts and edit them, but you may not submit cruises for approval before your account is approved.")

		return self.render_to_response(
			self.get_context_data(
				form=form,
				cruiseday_form=cruiseday_form,
				participant_form=participant_form,
				document_form=document_form,
				equipment_form=equipment_form,
				invoice_form=invoice_form,
				is_NTNU=request.user.userdata.organization.is_NTNU,
				is_invalid=False
			)
		)

	def post(self, request, *args, **kwargs):
		"""Handles receiving submitted form and formset data and checking their validity."""
		self.object = None
		form_class = self.get_form_class()
		form_class.user = request.user
		form = self.get_form(form_class)
		cruiseday_form = CruiseDayFormSet(self.request.POST)
		participant_form = ParticipantFormSet(self.request.POST)
		document_form = DocumentFormSet(self.request.POST, self.request.FILES)
		equipment_form = EquipmentFormSet(self.request.POST)
		invoice_form = InvoiceFormSet(self.request.POST)

		if not self.request.user.userdata.email_confirmed and self.request.user.userdata.role == "":
			messages.add_message(self.request, messages.WARNING, mark_safe("You have not yet confirmed your email address. Your account will not be eligible for approval or submitting cruises before this is done. If you typed the wrong email address while signing up, correct it in your profile and we'll send you a new one. You may have to add no-reply@rvgunnerus.no to your contact list if our messages go to spam."+"<br><br><a class='btn btn-primary' href='"+reverse('resend-activation-mail')+"'>Resend activation email</a>"))
		elif self.request.user.userdata.email_confirmed and self.request.user.userdata.role == "":
			messages.add_message(self.request, messages.WARNING, "Your user account has not been approved by an administrator yet. You may save cruise drafts and edit them, but you may not submit cruises for approval before your account is approved.")

		# check if all our forms are valid, handle outcome
		if (form.is_valid() and cruiseday_form.is_valid() and participant_form.is_valid() and document_form.is_valid() and equipment_form.is_valid() and invoice_form.is_valid()):
			return self.form_valid(form, cruiseday_form, participant_form, document_form, equipment_form, invoice_form)
		else:
			return self.form_invalid(form, cruiseday_form, participant_form, document_form, equipment_form, invoice_form)

	def form_valid(self, form, cruiseday_form, participant_form, document_form, equipment_form, invoice_form):
		"""Called when all our forms are valid. Creates a Cruise with Participants and CruiseDays."""
		Cruise = form.save(commit=False)
		Cruise.leader = self.request.user
		try:
			Cruise.organization = Cruise.leader.userdata.organization
		except:
			pass
		form.cleaned_data["leader"] = self.request.user
		if hasattr(self, "request"):
			# check whether we're saving or submitting the form
			if self.request.POST.get("save_cruise"):
				Cruise.is_submitted = False
				messages.add_message(self.request, messages.SUCCESS, mark_safe('Cruise successfully saved. You may edit and submit it under "<a href="#draftsTop">Saved Cruise Drafts</a>".'))
			elif self.request.POST.get("submit_cruise"):
				cruiseday_form = CruiseDayFormSet(self.request.POST)
				participant_form = ParticipantFormSet(self.request.POST)
				cruise_days = cruiseday_form.cleaned_data
				cruise_participants = participant_form.cleaned_data
				cruise_invoice = invoice_form.cleaned_data
				if (Cruise.is_submittable(user=self.request.user, cleaned_data=form.cleaned_data, cruise_invoice=cruise_invoice, cruise_days=cruise_days, cruise_participants=cruise_participants)):
					Cruise.is_submitted = True
					Cruise.submit_date = timezone.now()
					messages.add_message(self.request, messages.SUCCESS, mark_safe('Cruise successfully submitted. You may track its approval status under "<a href="#cruiseTop">Your Cruises</a>".'))
				else:
					Cruise.is_submitted = False
					messages.add_message(self.request, messages.ERROR, mark_safe('Cruise could not be submitted:' + str(Cruise.get_missing_information_string(cleaned_data=form.cleaned_data, cruise_invoice=cruise_invoice, cruise_days=cruise_days, cruise_participants=cruise_participants)) + '<br>You may review and add any missing or invalid information under its entry in your saved cruise drafts below.'))
			else:
				Cruise.is_submitted = False
				messages.add_message(self.request, messages.ERROR, mark_safe('Cruise could not be submitted: We were unable to determine the action you wished to take on submit. Please try to submit again below.'))
		Cruise.save()
		self.object = form.save()
		cruiseday_form.instance = self.object
		cruiseday_form.save()
		participant_form.instance = self.object
		participant_form.save()
		document_form.instance = self.object
		document_form.save()
		equipment_form.instance = self.object
		equipment_form.save()
		invoice_form.instance = self.object
		invoice_form.save()
		return HttpResponseRedirect(self.get_success_url())

	def form_invalid(self, form, cruiseday_form, participant_form, document_form, equipment_form, invoice_form):
		"""Throw form back at user."""
		print(cruiseday_form)
		print(document_form)
		print(equipment_form)
		print(invoice_form)
		return self.render_to_response(
			self.get_context_data(
				form=form,
				cruiseday_form=cruiseday_form,
				participant_form=participant_form,
				document_form=document_form,
				equipment_form=equipment_form,
				invoice_form=invoice_form,
				is_NTNU=self.request.user.userdata.organization.is_NTNU,
				is_invalid=True,
			)
		)

class CruiseEditView(UpdateView):
	template_name = 'reserver/cruise_edit_form.html'
	model = Cruise
	form_class = CruiseForm

	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "edited cruise"
		action.save()
		return reverse_lazy('user-page')

	def get_form_kwargs(self):
		kwargs = super(CruiseEditView, self).get_form_kwargs()
		kwargs.update({'request': self.request})
		return kwargs

	def get(self, request, *args, **kwargs):
		"""Handles creation of new blank form/formset objects."""
		self.object = get_object_or_404(Cruise, pk=self.kwargs.get('pk'))
		if not self.object.is_editable_by(request.user):
			raise PermissionDenied
		form_class = self.get_form_class()
		form_class.user = request.user
		form = self.get_form(form_class)
		cruiseday_form = CruiseDayFormSet(instance=self.object)
		participant_form = ParticipantFormSet(instance=self.object)
		document_form = DocumentFormSet(instance=self.object)
		equipment_form = EquipmentFormSet(instance=self.object)
		invoice_form = InvoiceFormSet(instance=self.object)

		return self.render_to_response(
			self.get_context_data(
				form=form,
				cruiseday_form=cruiseday_form,
				participant_form=participant_form,
				document_form=document_form,
				equipment_form=equipment_form,
				invoice_form=invoice_form,
				is_NTNU=self.object.leader.userdata.organization.is_NTNU
			)
		)

	def post(self, request, *args, **kwargs):
		"""Handles receiving submitted form and formset data and checking their validity."""
		self.object = get_object_or_404(Cruise, pk=self.kwargs.get('pk'))
		if not self.object.is_editable_by(request.user):
			raise PermissionDenied
		form_class = self.get_form_class()
		form_class.user = request.user
		form = self.get_form(form_class)
		cruiseday_form = CruiseDayFormSet(self.request.POST, instance=self.object)
		participant_form = ParticipantFormSet(self.request.POST, instance=self.object)
		document_form = DocumentFormSet(data=request.POST, files=request.FILES, instance=self.object)
		equipment_form = EquipmentFormSet(self.request.POST, instance=self.object)
		invoice_form = InvoiceFormSet(self.request.POST, instance=self.object)

		# check if all our forms are valid, handle outcome
		if (form.is_valid() and cruiseday_form.is_valid() and participant_form.is_valid() and document_form.is_valid() and equipment_form.is_valid() and invoice_form.is_valid()):
			return self.form_valid(form, cruiseday_form, participant_form, document_form, equipment_form, invoice_form)
		else:
			return self.form_invalid(form, cruiseday_form, participant_form, document_form, equipment_form, invoice_form)

	def form_valid(self, form, cruiseday_form, participant_form, document_form, equipment_form, invoice_form):
		"""Called when all our forms are valid. Creates a Cruise with Participants and CruiseDays."""
		old_cruise = get_object_or_404(Cruise, pk=self.kwargs.get('pk'))
		old_cruise_days_string = str(old_cruise.get_cruise_days())
		new_cruise = form.save(commit=False)
		new_cruise.information_approved = False
		new_cruise.save()
		self.object = form.save()
		cruiseday_form.instance = self.object
		cruiseday_form.save()
		participant_form.instance = self.object
		participant_form.save()
		document_form.instance = self.object
		document_form.save()
		equipment_form.instance = self.object
		equipment_form.save()
		invoice_form.instance = self.object
		invoice_form.save()

		new_cruise.outdate_missing_information()

		if old_cruise_days_string != str(new_cruise.get_cruise_days()):
			new_cruise.is_approved = False
			new_cruise.information_approved = False
			new_cruise.save()
			if (new_cruise.is_submitted):
				messages.add_message(self.request, messages.SUCCESS, mark_safe('Cruise ' + str(Cruise) + ' updated. Your cruise days were modified, so your cruise is now pending approval.'))
				delete_cruise_deadline_and_departure_notifications(new_cruise)
				set_date_dict_outdated()
			else:
				messages.add_message(self.request, messages.SUCCESS, mark_safe('Cruise ' + str(Cruise) + ' updated.'))
		else:
			if (old_cruise.information_approved):
				messages.add_message(self.request, messages.SUCCESS, mark_safe('Cruise ' + str(Cruise) + ' updated. Your cruise information was modified, so your cruise\'s information is now pending approval.'))
				delete_cruise_departure_notifications(new_cruise)
			else:
				messages.add_message(self.request, messages.SUCCESS, mark_safe('Cruise ' + str(Cruise) + ' updated.'))
		if (old_cruise.information_approved):
			admin_user_emails = [admin_user.email for admin_user in list(User.objects.filter(userdata__role='admin'))]
			send_template_only_email(admin_user_emails, EmailTemplate.objects.get(title='Approved cruise updated'), cruise=old_cruise)
		return HttpResponseRedirect(self.get_success_url())

	def form_invalid(self, form, cruiseday_form, participant_form, document_form, equipment_form, invoice_form):
		"""Throw form back at user."""
		return self.render_to_response(
			self.get_context_data(
				form=form,
				cruiseday_form=cruiseday_form,
				participant_form=participant_form,
				document_form=document_form,
				equipment_form=equipment_form,
				invoice_form=invoice_form,
				is_NTNU=self.object.leader.userdata.organization.is_NTNU
			)
		)
