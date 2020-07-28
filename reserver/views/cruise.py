import pyqrcode
import io
import base64
import datetime
import json
import os, tempfile, zipfile

from django.conf import settings

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

from django.utils.encoding import force_text
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes
from django.utils import six

from django.http import HttpResponse
from wsgiref.util import FileWrapper
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from easy_pdf.views import PDFTemplateView
from easy_pdf.rendering import html_to_pdf, make_response, render_to_pdf_response
from django.utils.decorators import method_decorator
from django import template
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail, get_connection

from django.http import JsonResponse, HttpResponseRedirect
from django.template import loader
from django.utils import timezone

from reserver.utils import render_add_cal_button
from reserver.utils import check_for_and_fix_users_without_userdata
from reserver.utils import create_cruise_notifications, create_cruise_administration_notification
from reserver.utils import create_cruise_deadline_and_departure_notifications, delete_cruise_notifications
from reserver.utils import delete_cruise_departure_notifications, delete_cruise_deadline_and_departure_notifications
from reserver.utils import create_season_notifications, delete_season_notifications
from reserver.utils import init
from reserver.emails import account_activation_token, send_activation_email, send_user_approval_email

from reserver.emails import send_email, send_template_only_email
from reserver import jobs

from reserver.models import *
from reserver.forms import *

def cruise_pdf_view(request, pk):
	cruise = get_object_or_404(Cruise, pk=pk)
	if not cruise.is_viewable_by(request.user):
		raise PermissionDenied

	context = {
		'pagesize': 'A4',
		'title': 'Cruise summary for ' + str(cruise),
		'cruise': cruise,
		'http_host': request.META['HTTP_HOST']
	}

	return render_to_pdf_response(
		request,
		'reserver/pdfs/cruise_pdf.html',
		context,
		download_filename='cruise.pdf'
	)

class CruiseDeleteView(DeleteView):
	model = Cruise
	template_name = 'reserver/cruises/cruise_delete_form.html'

	def dispatch(self, request, *args, **kwargs):
		object = get_object_or_404(self.model, pk=self.kwargs.get('pk'))
		if not object.is_cancellable_by(request.user):
			raise PermissionDenied
		return super().dispatch(request, *args, **kwargs)

	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "deleted cruise"
		action.save()
		return reverse_lazy('user-page')

class CruiseList(ListView):
	model = Cruise
	template_name = 'reserver/cruises/cruise_list.html'

class CruiseCreateView(CreateView):
	template_name = 'reserver/cruises/cruise_create_form.html'
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
				billing_type="auto",
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
				messages.add_message(self.request, messages.SUCCESS, mark_safe('Cruise successfully saved. You may edit and submit it on the "<a href="/user/cruises/unsubmitted/">Unsubmitted Cruises</a>" page.'))
			elif self.request.POST.get("submit_cruise"):
				cruiseday_form = CruiseDayFormSet(self.request.POST)
				participant_form = ParticipantFormSet(self.request.POST)
				cruise_days = cruiseday_form.cleaned_data
				cruise_participants = participant_form.cleaned_data
				cruise_invoice = invoice_form.cleaned_data
				if (Cruise.is_submittable(user=self.request.user, cleaned_data=form.cleaned_data, cruise_invoice=cruise_invoice, cruise_days=cruise_days, cruise_participants=cruise_participants)):
					Cruise.is_submitted = True
					Cruise.submit_date = timezone.now()
					messages.add_message(self.request, messages.SUCCESS, mark_safe('Cruise successfully submitted. You may track its approval status on the "<a href="/user/cruises/submitted/">Submitted Cruises</a>" page.'))
				else:
					Cruise.is_submitted = False
					messages.add_message(self.request, messages.ERROR, mark_safe('Cruise could not be submitted:' + str(Cruise.get_missing_information_string(cleaned_data=form.cleaned_data, cruise_invoice=cruise_invoice, cruise_days=cruise_days, cruise_participants=cruise_participants)) + '<br>You may review and add any missing or invalid information on the "<a href="/user/cruises/unsubmitted/">Unsubmitted Cruises</a>" page.'))
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
				billing_type="auto",
				is_invalid=True,
			)
		)

class CruiseEditView(UpdateView):
	template_name = 'reserver/cruises/cruise_edit_form.html'
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
				billing_type=self.object.billing_type,
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
				messages.add_message(self.request, messages.SUCCESS, mark_safe('Cruise ' + str(Cruise) + ' updated. Your cruise days were modified, so your cruise is now pending approval. You may track its approval status on the "<a href="/user/cruises/submitted/">Submitted Cruises</a>" page.'))
				delete_cruise_deadline_and_departure_notifications(new_cruise)
				set_date_dict_outdated()
			else:
				messages.add_message(self.request, messages.SUCCESS, mark_safe('Cruise ' + str(Cruise) + ' updated.'))
		else:
			if (old_cruise.information_approved):
				messages.add_message(self.request, messages.SUCCESS, mark_safe('Cruise ' + str(Cruise) + ' updated. Your cruise information was modified, so your cruise\'s information is now pending approval. You may track its approval status on the "<a href="/user/cruises/upcoming/">Upcoming Cruises</a>" page.'))
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
				billing_type=self.object.billing_type,
				is_NTNU=self.object.leader.userdata.organization.is_NTNU
			)
		)

class CruiseView(CruiseEditView):
	template_name = 'reserver/cruises/cruise_view_form.html'

	def get(self, request, *args, **kwargs):
		self.object = get_object_or_404(Cruise, pk=self.kwargs.get('pk'))
		if not self.object.is_viewable_by(request.user):
			raise PermissionDenied
		form_class = self.get_form_class()
		form = self.get_form(form_class)
		cruiseday_form = CruiseDayFormSet(instance=self.object)
		participant_form = ParticipantFormSet(instance=self.object)
		document_form = DocumentFormSet(instance=self.object)
		equipment_form = EquipmentFormSet(instance=self.object)
		invoice_form = InvoiceFormSet(instance=self.object)

		for key in form.fields.keys():
			form.fields[key].widget.attrs['readonly'] = True
			form.fields[key].widget.attrs['disabled'] = True

		for subform in cruiseday_form:
			for key in subform.fields.keys():
				subform.fields[key].widget.attrs['readonly'] = True
				subform.fields[key].widget.attrs['disabled'] = True

		for subform in participant_form:
			for key in subform.fields.keys():
				subform.fields[key].widget.attrs['readonly'] = True
				subform.fields[key].widget.attrs['disabled'] = True

		for subform in document_form:
			for key in subform.fields.keys():
				subform.fields[key].widget.attrs['readonly'] = True
				subform.fields[key].widget.attrs['disabled'] = True

		for subform in equipment_form:
			for key in subform.fields.keys():
				subform.fields[key].widget.attrs['readonly'] = True
				subform.fields[key].widget.attrs['disabled'] = True

		for subform in invoice_form:
			for key in subform.fields.keys():
				subform.fields[key].widget.attrs['readonly'] = True
				subform.fields[key].widget.attrs['disabled'] = True

		return self.render_to_response(
			self.get_context_data(
				form=form,
				cruiseday_form=cruiseday_form,
				participant_form=participant_form,
				document_form=document_form,
				equipment_form=equipment_form,
				invoice_form=invoice_form,
				billing_type=self.object.billing_type,
				is_NTNU=self.object.leader.userdata.organization.is_NTNU
			)
		)

def submit_cruise(request, pk):
	cruise = get_object_or_404(Cruise, pk=pk)
	if request.user == cruise.leader or request.user in cruise.owner.all():
		if not cruise.is_submittable(user=request.user):
			messages.add_message(request, messages.ERROR, mark_safe('Cruise could not be submitted: ' + str(cruise.get_missing_information_string()) + '<br>You may review and add any missing or invalid information on the "<a href="/user/cruises/unsubmitted/">Unsubmitted Cruises</a>" page.'))
		else:
			cruise.is_submitted = True
			cruise.information_approved = False
			cruise.is_approved = False
			cruise.is_cancelled = False
			cruise.submit_date = timezone.now()
			cruise.save()
			action = Action(user=request.user, target=str(cruise))
			action.action = "submitted cruise"
			action.timestamp = timezone.now()
			action.save()
			"""Sends notification email to admins about a new cruise being submitted."""
			admin_user_emails = [admin_user.email for admin_user in list(User.objects.filter(userdata__role='admin'))]
			send_template_only_email(admin_user_emails, EmailTemplate.objects.get(title='New cruise'), cruise=cruise)
			messages.add_message(request, messages.SUCCESS, mark_safe('Cruise successfully submitted. You may track its approval status on the "<a href="/user/cruises/submitted/">Submitted Cruises</a>" page.'))
	else:
		raise PermissionDenied
	return redirect(request.META['HTTP_REFERER'])

def unsubmit_cruise(request, pk):
	cruise = get_object_or_404(Cruise, pk=pk)
	if cruise.is_cancellable_by(request.user):
		cruise.is_submitted = False
		cruise.information_approved = False
		cruise.is_approved = False
		cruise.save()
		action = Action(user=request.user, target=str(cruise))
		action.action = "unsubmitted cruise"
		action.timestamp = timezone.now()
		action.save()
		set_date_dict_outdated()
		messages.add_message(request, messages.WARNING, mark_safe('Cruise ' + str(cruise) + ' cancelled.'))
		admin_user_emails = [admin_user.email for admin_user in list(User.objects.filter(userdata__role='admin'))]
		send_template_only_email(admin_user_emails, EmailTemplate.objects.get(title='Cruise cancelled'), cruise=cruise)
		delete_cruise_deadline_and_departure_notifications(cruise)
	else:
		raise PermissionDenied
	return redirect(request.META['HTTP_REFERER'])

def cancel_cruise(request, pk):
	cruise = get_object_or_404(Cruise, pk=pk)
	if request.method =='POST':
		if cruise.is_cancellable_by(request.user):
			cruise.is_submitted = False
			cruise.information_approved = False
			cruise.is_approved = False
			if cruise.editing_deadline_passed():
				cruise.is_cancelled = True
			cruise.save()
			action = Action(user=request.user, target=str(cruise))
			action.action = "cancelled cruise"
			action.timestamp = timezone.now()
			action.save()
			set_date_dict_outdated()
			messages.add_message(request, messages.WARNING, mark_safe('Cruise ' + str(cruise) + ' cancelled.'))
			admin_user_emails = [admin_user.email for admin_user in list(User.objects.filter(userdata__role='admin'))]
			send_template_only_email(admin_user_emails, EmailTemplate.objects.get(title='Cruise cancelled'), cruise=cruise)
			delete_cruise_deadline_and_departure_notifications(cruise)
		return redirect(reverse_lazy('user-unsubmitted-cruises'))
	return render(request, 'reserver/cruises/cruise_cancel.html', {'cruise':cruise, 'redirect':request.META['HTTP_REFERER']})

def archive_cruise(request, pk):
	cruise = get_object_or_404(Cruise, pk=pk)
	if request.method =='POST':
		cruise.is_archived = True
		cruise.save()
		action = Action(user=request.user, target=str(cruise))
		action.action = "archived cruise"
		action.timestamp = timezone.now()
		action.save()
		messages.add_message(request, messages.WARNING, mark_safe('Cruise ' + str(cruise) + ' archived.'))
		if cruise.is_cancelled:
			return redirect(reverse_lazy('user-finished-cruises'))
		else:
			return redirect(reverse_lazy('user-unsubmitted-cruises'))
	return render(request, 'reserver/cruises/cruise_archive.html', {'cruise':cruise, 'redirect':request.META['HTTP_REFERER']})

def unarchive_cruise(request, pk):
	cruise = get_object_or_404(Cruise, pk=pk)
	if request.user == cruise.leader or request.user in cruise.owner.all():
		if not cruise.is_cancellable():
			messages.add_message(request, messages.ERROR, mark_safe('Cruise could not be unarchived because the cruise has begun or is finished.'))
		else:
			cruise.is_archived = False
			cruise.save()
			action = Action(user=request.user, target=str(cruise))
			action.action = "unarchived cruise"
			action.timestamp = timezone.now()
			action.save()
			messages.add_message(request, messages.SUCCESS, mark_safe('Cruise moved to the "<a href="/user/cruises/unsubmitted/">Submitted Cruises</a>" page. You may continue to edit the cruise.'))
	else:
		raise PermissionDenied
	return redirect(request.META['HTTP_REFERER'])

def hide_cruise(request, pk):
	cruise = get_object_or_404(Cruise, pk=pk)
	if request.method =='POST':
		cruise.is_hidden = True
		cruise.save()
		action = Action(user=request.user, target=str(cruise))
		action.action = "cruise hidden from user"
		action.timestamp = timezone.now()
		action.save()
		messages.add_message(request, messages.WARNING, mark_safe('Cruise ' + str(cruise) + ' deleted.'))
		return redirect(reverse_lazy('user-unsubmitted-cruises'))
	return render(request, 'reserver/cruises/cruise_hide.html', {'cruise':cruise, 'redirect':request.META['HTTP_REFERER']})

# admin-only

@csrf_exempt
def reject_cruise(request, pk):
	cruise = get_object_or_404(Cruise, pk=pk)
	if request.user.is_superuser:
		#message
		try:
			json_data = json.loads(request.body.decode("utf-8"))
			message = json_data["message"]
		except:
			message = ""
		#end message
		cruise.is_approved = False
		cruise.information_approved = False
		cruise.is_submitted = False
		cruise.save()
		action = Action(user=request.user, target=str(cruise))
		action.action = "rejected cruise"
		action.timestamp = timezone.now()
		action.save()
		messages.add_message(request, messages.WARNING, mark_safe('Cruise ' + str(cruise) + ' rejected.'))
		create_cruise_administration_notification(cruise, 'Cruise rejected', message=message)
		if cruise.information_approved:
			delete_cruise_deadline_notifications(cruise)
		else:
			delete_cruise_deadline_and_departure_notifications(cruise)
	else:
		raise PermissionDenied
	return JsonResponse(json.dumps([], ensure_ascii=True), safe=False)

@csrf_exempt
def approve_cruise(request, pk):
	cruise = get_object_or_404(Cruise, pk=pk)
	if request.user.is_superuser:
		#message
		try:
			json_data = json.loads(request.body.decode("utf-8"))
			message = json_data["message"]
		except:
			message = ""
		#end message
		cruise.is_approved = True
		cruise.save()
		action = Action(user=request.user, target=str(cruise))
		action.action = "approved cruise days"
		action.timestamp = timezone.now()
		action.save()
		messages.add_message(request, messages.SUCCESS, mark_safe('Cruise ' + str(cruise) + ' approved.'))
		create_cruise_administration_notification(cruise, 'Cruise dates approved', message=message)
		set_date_dict_outdated()
		if cruise.information_approved:
			create_cruise_deadline_and_departure_notifications(cruise)
		else:
			create_cruise_notifications(cruise, 'Cruise deadlines')
	else:
		raise PermissionDenied
	return JsonResponse(json.dumps([], ensure_ascii=True), safe=False)

@csrf_exempt
def unapprove_cruise(request, pk):
	cruise = get_object_or_404(Cruise, pk=pk)
	if request.user.is_superuser:
		#message
		try:
			json_data = json.loads(request.body.decode("utf-8"))
			message = json_data["message"]
		except:
			message = ""
		#end message
		cruise.is_approved = False
		cruise.information_approved = False
		cruise.save()
		action = Action(user=request.user, target=str(cruise))
		action.action = "unapproved cruise days"
		action.timestamp = timezone.now()
		action.save()
		set_date_dict_outdated()
		messages.add_message(request, messages.WARNING, mark_safe('Cruise ' + str(cruise) + ' unapproved.'))
		create_cruise_administration_notification(cruise, 'Cruise unapproved', message=message)
		if cruise.information_approved:
			delete_cruise_deadline_notifications(cruise)
		else:
			delete_cruise_deadline_and_departure_notifications(cruise)
	else:
		raise PermissionDenied
	return JsonResponse(json.dumps([], ensure_ascii=True), safe=False)

@csrf_exempt
def approve_cruise_information(request, pk):
	cruise = get_object_or_404(Cruise, pk=pk)
	if request.user.is_superuser:
		#message
		try:
			json_data = json.loads(request.body.decode("utf-8"))
			message = json_data["message"]
		except:
			message = ""
		#end message
		cruise.information_approved = True
		cruise.save()
		action = Action(user=request.user, target=str(cruise))
		action.action = "approved cruise information"
		action.timestamp = timezone.now()
		action.save()
		messages.add_message(request, messages.SUCCESS, mark_safe('Cruise information for ' + str(cruise) + ' approved.'))
		if cruise.is_approved:
			create_cruise_notifications(cruise, 'Cruise departure')
			create_cruise_administration_notification(cruise, 'Cruise information approved', message=message)
	else:
		raise PermissionDenied
	return JsonResponse(json.dumps([], ensure_ascii=True), safe=False)

@csrf_exempt
def unapprove_cruise_information(request, pk):
	cruise = get_object_or_404(Cruise, pk=pk)
	if request.user.is_superuser:
		#message
		try:
			json_data = json.loads(request.body.decode("utf-8"))
			message = json_data["message"]
		except:
			message = ""
		#end message
		cruise.information_approved = False
		cruise.save()
		action = Action(user=request.user, target=str(cruise))
		action.action = "unapproved cruise information"
		action.timestamp = timezone.now()
		action.save()
		messages.add_message(request, messages.WARNING, mark_safe('Cruise information for ' + str(cruise) + ' unapproved.'))
		delete_cruise_departure_notifications(cruise)
		create_cruise_administration_notification(cruise, 'Cruise information unapproved', message=message)
	else:
		raise PermissionDenied
	return JsonResponse(json.dumps([], ensure_ascii=True), safe=False)

@csrf_exempt
def send_cruise_message(request, pk):
	cruise = get_object_or_404(Cruise, pk=pk)
	if request.user.is_superuser:
		#message
		try:
			json_data = json.loads(request.body.decode("utf-8"))
			message = json_data["message"]
		except:
			message = ""
		#end message
		action = Action(user=request.user, target=str(cruise))
		action.action = "sent message to cruise"
		action.timestamp = timezone.now()
		action.save()
		create_cruise_administration_notification(cruise, 'Cruise message', message=message)
		messages.add_message(request, messages.SUCCESS, mark_safe('Message sent to ' + str(cruise) + '.'))
	else:
		raise PermissionDenied
	return JsonResponse(json.dumps([], ensure_ascii=True), safe=False)
