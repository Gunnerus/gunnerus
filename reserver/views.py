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

def remove_dups_keep_order(lst):
	without_dups = []
	for item in lst:
		if (item not in without_dups):
			without_dups.append(item)
	return without_dups
	
def backup_view(request):
	"""																		 
	Create a ZIP file on disk and transmit it in chunks of 8KB,				 
	without loading the whole file into memory. A similar approach can		  
	be used for large dynamic PDF files.										
	"""
	temp = tempfile.TemporaryFile()
	archive = zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED)
	archive.write(settings.DATABASES["default"]["NAME"], 'db.sqlite3')
	for filename in os.listdir(settings.MEDIA_ROOT):
		filepath = os.path.join(settings.MEDIA_ROOT, filename)
		if os.path.isdir(filepath):
			# skip directories
			continue
		archive.write(filepath, "uploads\\"+filename)
	for filename in os.listdir(os.path.join(settings.BASE_DIR, "reserver/migrations")):
		filepath = os.path.join(os.path.join(settings.BASE_DIR, "reserver/migrations"), filename)
		if os.path.isdir(filepath):
			# skip directories
			continue
		archive.write(filepath, "migrations\\"+filename)
	archive.close()
	length = temp.tell()
	wrapper = FileWrapper(temp)
	temp.seek(0)
	response = HttpResponse(wrapper, content_type='application/zip')
	response['Content-Disposition'] = 'attachment; filename=reserver-backup-'+timezone.now().strftime('%Y-%m-%d-%H%M%S')+'.zip'
	response['Content-Length'] = length
	return response

def get_cruises_need_attention():
	return remove_dups_keep_order(list(Cruise.objects.filter(is_submitted=True, is_approved=True, information_approved=False, cruise_end__gte=timezone.now())))
	
def get_upcoming_cruises():
	return remove_dups_keep_order(list(Cruise.objects.filter(is_submitted=True, is_approved=True, information_approved=True, cruise_end__gte=timezone.now())))

def get_unapproved_cruises():
	return remove_dups_keep_order(Cruise.objects.filter(is_submitted=True, is_approved=False, cruise_end__gte=timezone.now()).order_by('submit_date'))
	
def get_users_not_approved():
	check_for_and_fix_users_without_userdata()
	return list(UserData.objects.filter(role="", email_confirmed=True, user__is_active=True))
	
def get_organizationless_users():
	check_for_and_fix_users_without_userdata()
	return list(UserData.objects.filter(organization__isnull=True))
	
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
				is_NTNU=request.user.userdata.organization.is_NTNU
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
				messages.add_message(self.request, messages.SUCCESS, mark_safe('Cruise successfully saved. You may edit and submit under "<a href="#draftsTop">Saved Cruise Drafts</a>".'))
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
					messages.add_message(self.request, messages.ERROR, mark_safe('Cruise could not be submitted:' + str(Cruise.get_missing_information_string(cleaned_data=form.cleaned_data, cruise_days=cruise_days, cruise_participants=cruise_participants)) + '<br>You may review and add any missing or invalid information under its entry in your saved cruise drafts below.'))
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
		return self.render_to_response(
			self.get_context_data(
				form=form,
				cruiseday_form=cruiseday_form,
				participant_form=participant_form,
				document_form=document_form,
				equipment_form=equipment_form,
				invoice_form=invoice_form,
				is_NTNU=request.user.userdata.organization.is_NTNU
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
				set_date_dict_outdated()
			else:
				messages.add_message(self.request, messages.SUCCESS, mark_safe('Cruise ' + str(Cruise) + ' updated.'))
		else:
			if (old_cruise.information_approved):
				messages.add_message(self.request, messages.SUCCESS, mark_safe('Cruise ' + str(Cruise) + ' updated. Your cruise information was modified, so your cruise\'s information is now pending approval.'))
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
		
class CruiseView(CruiseEditView):
	template_name = 'reserver/cruise_view_form.html'
	
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
				is_NTNU=self.object.leader.userdata.organization.is_NTNU
			)
		)
	
	def post(self, request, *args, **kwargs):
		# uncallable, unsupported and useless, but just in case anybody wants to send a post request
		return self.form_invalid(form, cruiseday_form, participant_form, document_form, equipment_form, invoice_form)
			
	def form_valid(self, form, cruiseday_form, participant_form, document_form, equipment_form, invoice_form):
		# uncallable, unsupported and useless, but just in case anybody wants to send a post request
		return HttpResponseRedirect(self.get_success_url())
		
	def form_invalid(self, form, cruiseday_form, participant_form, document_form, equipment_form, invoice_form):
		# uncallable, unsupported and useless, but just in case anybody wants to send a post request
		"""Throw form back at user."""
		return self.render_to_response(
			self.get_context_data(
				form=form,
				cruiseday_form=cruiseday_form,
				participant_form=participant_form,
				document_form=document_form,
				equipment_form=equipment_form,
				invoice_form=invoice_form,
				is_NTNU=request.user.userdata.organization.is_NTNU
			)
		)

class CruiseDeleteView(DeleteView):
	model = Cruise
	template_name = 'reserver/cruise_delete_form.html'
	
	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "deleted cruise"
		action.save()
		return reverse_lazy('user-page')
	
def index_view(request):
	if request.user.is_authenticated():
		if not request.user.userdata.email_confirmed and request.user.userdata.role == "":
			messages.add_message(request, messages.WARNING, mark_safe("You have not yet confirmed your email address. Your account will not be eligible for approval or submitting cruises before this is done. If you typed the wrong email address while signing up, correct it in your profile and we'll send you a new one. You may have to add no-reply@rvgunnerus.no to your contact list if our messages go to spam."+"<br><br><a class='btn btn-primary' href='"+reverse('resend-activation-mail')+"'>Resend activation email</a>"))
		elif request.user.userdata.email_confirmed and request.user.userdata.role == "":
			messages.add_message(request, messages.WARNING, "Your user account has not been approved by an administrator yet. You may save cruise drafts and edit them, but you may not submit cruises for approval before your account is approved.")
	return render(request, 'reserver/index.html')

def submit_cruise(request, pk):
	cruise = get_object_or_404(Cruise, pk=pk)
	if request.user == cruise.leader or request.user in cruise.owner.all():
		if not cruise.is_submittable(user=request.user):
			messages.add_message(request, messages.ERROR, mark_safe('Cruise could not be submitted: ' + str(cruise.get_missing_information_string()) + '<br>You may review and add any missing or invalid information under its entry in your saved cruise drafts below.'))
		else:
			cruise.is_submitted = True
			cruise.information_approved = False
			cruise.is_approved = False
			cruise.submit_date = timezone.now()
			cruise.save()
			action = Action(user=request.user, target=str(cruise))
			action.action = "submitted cruise"
			action.timestamp = timezone.now()
			action.save()
			"""Sends notification email to admins about a new cruise being submitted."""
			admin_user_emails = [admin_user.email for admin_user in list(User.objects.filter(userdata__role='admin'))]
			send_template_only_email(admin_user_emails, EmailTemplate.objects.get(title='New cruise'), cruise=cruise)
			messages.add_message(request, messages.SUCCESS, mark_safe('Cruise successfully submitted. You may track its approval status under "<a href="#cruiseTop">Your Cruises</a>".'))
	else:
		raise PermissionDenied
	return redirect(request.META['HTTP_REFERER'])
	
def unsubmit_cruise(request, pk):
	cruise = get_object_or_404(Cruise, pk=pk)
	if (request.user.pk == cruise.leader.pk or request.user in cruise.owner.all()):
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
	else:
		raise PermissionDenied
	return redirect(request.META['HTTP_REFERER'])

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
	
#To be run when a cruise or its information is unapproved
def delete_cruise_notifications(cruise, template_group):
	cruise_event = CruiseDay.objects.filter(cruise=cruise).order_by('event__start_time').first().event
	all_notifications = EmailNotification.objects.filter(event=cruise_event)
	deadline_notifications = all_notifications.filter(template__group=template_group)
	for notif in deadline_notifications:
		notif.delete()
	jobs.restart_scheduler()
	
#To be run when a cruise is unapproved
def delete_cruise_deadline_notifications(cruise):
	delete_cruise_notifications(cruise, 'Cruise deadlines')

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
		now = timezone.now()
		
		if not self.request.user.userdata.email_confirmed and self.request.user.userdata.role == "":
			messages.add_message(self.request, messages.WARNING, mark_safe("You have not yet confirmed your email address. Your account will not be eligible for approval or submitting cruises before this is done. If you typed the wrong email address while signing up, correct it in the form below and we'll send you a new one. You may have to add no-reply@rvgunnerus.no to your contact list if our messages go to spam."+"<br><br><a class='btn btn-primary' href='"+reverse('resend-activation-mail')+"'>Resend activation email</a>"))
		elif self.request.user.userdata.email_confirmed and self.request.user.userdata.role == "":
			messages.add_message(self.request, messages.WARNING, "Your user account has not been approved by an administrator yet. You may save cruise drafts and edit them, but you may not submit cruises for approval before your account is approved.")
		
		# add submitted cruises to context
		submitted_cruises = list(set(list(Cruise.objects.filter(leader=self.request.user, is_submitted=True) | Cruise.objects.filter(owner=self.request.user, is_submitted=True))))
		context['my_submitted_cruises'] = sorted(list(submitted_cruises), key=lambda x: str(x.cruise_start), reverse=False)
		
		# add unsubmitted cruises to context
		unsubmitted_cruises = list(set(list(Cruise.objects.filter(leader=self.request.user, is_submitted=False) | Cruise.objects.filter(owner=self.request.user, is_submitted=False))))
		context['my_unsubmitted_cruises'] = sorted(list(unsubmitted_cruises), key=lambda x: str(x.cruise_start), reverse=False)
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
	cruises_badge = len(cruises_need_attention)
	users_badge = len(users_not_approved)
	overview_badge = cruises_badge + users_badge + len(get_unapproved_cruises())
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
	return render(request, 'reserver/admin_overview.html', {'overview_badge':overview_badge, 'cruises_badge':cruises_badge, 'users_badge':users_badge, 'unapproved_cruises':unapproved_cruises, 'upcoming_cruises':upcoming_cruises, 'cruises_need_attention':cruises_need_attention, 'users_not_verified':users_not_approved, 'internal_days_remaining':internal_days_remaining, 'external_days_remaining':external_days_remaining, 'internal_days_remaining_next_year':internal_days_remaining_next_year, 'external_days_remaining_next_year':external_days_remaining_next_year, 'current_year':current_year, 'next_year':next_year, 'last_actions':last_actions})

def admin_cruise_view(request):
	cruises = list(Cruise.objects.filter(is_approved=True))
	cruises_need_attention = get_cruises_need_attention()
	users_not_approved = get_users_not_approved()
	cruises_badge = len(get_cruises_need_attention())
	users_badge = len(users_not_approved)
	overview_badge = cruises_badge + users_badge + len(get_unapproved_cruises())
	if(len(cruises_need_attention) > 1):
		messages.add_message(request, messages.WARNING, mark_safe(('<i class="fa fa-exclamation-triangle" aria-hidden="true"></i> %s upcoming cruises have not had their information approved yet.' % str(len(cruises_need_attention)))+"<br><br><a class='btn btn-primary' href='"+reverse('admin')+"#approved-cruises-needing-attention'><i class='fa fa-arrow-right' aria-hidden='true'></i> Jump to cruises</a>"))
	elif(len(cruises_need_attention) == 1):
		messages.add_message(request, messages.WARNING, mark_safe('<i class="fa fa-exclamation-triangle" aria-hidden="true"></i> An upcoming cruise has not had its information approved yet.'+"<br><br><a class='btn btn-primary' href='"+reverse('admin')+"#approved-cruises-needing-attention'><i class='fa fa-arrow-right' aria-hidden='true'></i> Jump to cruise</a>"))
	return render(request, 'reserver/admin_cruises.html', {'overview_badge':overview_badge, 'overview_badge':overview_badge, 'cruises_badge':cruises_badge, 'users_badge':users_badge, 'cruises':cruises})
	
def admin_user_view(request):
	users = list(UserData.objects.exclude(role="").order_by('-role', 'user__last_name', 'user__first_name'))
	users_not_approved = get_users_not_approved()
	cruises_badge = len(get_cruises_need_attention())
	users_badge = len(users_not_approved)
	overview_badge = cruises_badge + users_badge + len(get_unapproved_cruises())
	if(len(users_not_approved) > 1):
		messages.add_message(request, messages.INFO, mark_safe(('<i class="fa fa-info-circle" aria-hidden="true"></i> %s users need attention.' % str(len(users_not_approved)))+"<br><br><a class='btn btn-primary' href='"+reverse('admin')+"#users-needing-attention'><i class='fa fa-arrow-right' aria-hidden='true'></i> Jump to users</a>"))
	elif(len(users_not_approved) == 1):
		messages.add_message(request, messages.INFO, mark_safe('<i class="fa fa-info-circle" aria-hidden="true"></i> A user needs attention.'+"<br><br><a class='btn btn-primary' href='"+reverse('admin')+"#users-needing-attention'><i class='fa fa-arrow-right' aria-hidden='true'></i> Jump to user</a>"))
	return render(request, 'reserver/admin_users.html', {'overview_badge':overview_badge, 'cruises_badge':cruises_badge, 'users_badge':users_badge, 'users':users})

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
	
def admin_event_view(request):
	off_day_event_category = EventCategory.objects.get(name="Red day")
	all_events = list(Event.objects.all().exclude(category=off_day_event_category))
	events = []
	for event in all_events:
		if event.is_scheduled_event():
			events.append(event)
	cruises_badge = len(get_cruises_need_attention())
	users_badge = len(get_users_not_approved())
	overview_badge = cruises_badge + users_badge + len(get_unapproved_cruises())
	return render(request, 'reserver/admin_events.html', {'overview_badge':overview_badge, 'cruises_badge':cruises_badge, 'users_badge':users_badge, 'events':events})

def admin_actions_view(request):
	last_actions = list(Action.objects.filter(timestamp__lte=timezone.now(), timestamp__gt=timezone.now()-datetime.timedelta(days=30)))

	#actions = Action.objects.all()
	#"paginator = Paginator(actions, 25) # Show 25 actions per page
	#page = request.GET.get('page')
	#page_actions = paginator.get_page(page)

	cruises_badge = len(get_cruises_need_attention())
	users_badge = len(get_users_not_approved())
	overview_badge = cruises_badge + users_badge + len(get_unapproved_cruises())
	last_actions.reverse()
	return render(request, 'reserver/admin_actions.html', {'overview_badge':overview_badge, 'cruises_badge':cruises_badge, 'users_badge':users_badge, 'actions':last_actions})

def admin_statistics_view(request):
	last_statistics = list(Statistics.objects.filter(timestamp__lte=timezone.now(), timestamp__gt=timezone.now()-datetime.timedelta(days=30)))
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
		
	cruises_badge = len(get_cruises_need_attention())
	users_badge = len(get_users_not_approved())
	overview_badge = cruises_badge + users_badge + len(get_unapproved_cruises())
	unique_statistics.reverse()
	return render(request, 'reserver/admin_statistics.html', {'overview_badge':overview_badge, 'cruises_badge':cruises_badge, 'users_badge':users_badge, 'statistics':unique_statistics})
	
def admin_season_view(request):
	seasons = Season.objects.all().order_by('-season_event__start_time')
	cruises_badge = len(get_cruises_need_attention())
	users_badge = len(get_users_not_approved())
	overview_badge = cruises_badge + users_badge + len(get_unapproved_cruises())
	return render(request, 'reserver/admin_seasons.html', {'overview_badge':overview_badge, 'cruises_badge':cruises_badge, 'users_badge':users_badge, 'seasons':seasons})
	
def food_view(request, pk):
	cruises_badge = len(get_cruises_need_attention())
	users_badge = len(get_users_not_approved())
	cruise = Cruise.objects.get(pk=pk)
	days = list(CruiseDay.objects.filter(cruise=cruise.pk))
	overview_badge = cruises_badge + users_badge + len(get_unapproved_cruises())
	return render(request, 'reserver/food.html', {'overview_badge':overview_badge, 'cruises_badge':cruises_badge, 'users_badge':users_badge, 'cruise':cruise, 'days':days})
	
def login_view(request):
	return render(request, 'reserver/login.html')
	
# user registration views

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
	return render(request, 'reserver/register.html', {'userdata_form':userdata_form, 'user_form':user_form})
	
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
		"""Sends notification mail to admins about a new user."""
		admin_user_emails = [admin_user.email for admin_user in list(User.objects.filter(userdata__role='admin'))]
		send_template_only_email(admin_user_emails, EmailTemplate.objects.get(title='New user'), user=user)
		return redirect('home')
	else:
		raise PermissionDenied
		
# season views
		
class CreateSeason(CreateView):
	model = Season
	template_name = 'reserver/season_edit_form.html'
	form_class = SeasonForm
	
	def get_form_kwargs(self):
		kwargs = super(CreateSeason, self).get_form_kwargs()
		kwargs.update({'request': self.request})
		return kwargs
		
	def get_success_url(self):
		return reverse_lazy('seasons')
	
	def get(self, request, *args, **kwargs):
		"""Handles creation of new blank form/formset objects."""
		self.object = None
		form_class = self.get_form_class()
		form = self.get_form(form_class)

		return self.render_to_response(
			self.get_context_data(
				form=form
			)
		)
		
	def post(self, request, *args, **kwargs):
		self.object = None
		form_class = self.get_form_class()
		form = self.get_form(form_class)
		# check if form is valid, handle outcome
		if form.is_valid():
			return self.form_valid(form)
		else:
			return self.form_invalid(form)
			
	def form_valid(self, form):
		"""Called when all our forms are valid. Creates a Cruise with Participants and CruiseDays."""
		season = form.save(commit=False)
		season_event = Event()
		season_event.category = EventCategory.objects.get(name="Season")
		season_event.name = 'Event for ' + form.cleaned_data.get("name")
		season_event.start_time = form.cleaned_data.get("season_event_start_date")
		season_event.end_time = form.cleaned_data.get("season_event_end_date").replace(hour=23, minute=59)
		season_event.save()
		internal_order_event = Event()
		internal_order_event.category = EventCategory.objects.get(name="Internal season opening")
		internal_order_event.name = 'Internal opening of ' + form.cleaned_data.get("name")
		internal_order_event.start_time = form.cleaned_data.get("internal_order_event_date")
		internal_order_event.save()
		external_order_event = Event()
		external_order_event.category = EventCategory.objects.get(name="External season opening")
		external_order_event.name = 'External opening of ' + form.cleaned_data.get("name")
		external_order_event.start_time = form.cleaned_data.get("external_order_event_date")
		external_order_event.save()
		season.season_event = season_event
		season.internal_order_event = internal_order_event
		season.external_order_event = external_order_event
		season.save()
		self.object = form.save()
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(season))
		action.action = "created season"
		action.save()
		create_season_notifications(season)
		return HttpResponseRedirect(self.get_success_url())
		
	def form_invalid(self, form):
		"""Throw form back at user."""
		return self.render_to_response(
			self.get_context_data(
				form=form
			)
		)
		
class SeasonEditView(UpdateView):
	model = Season
	template_name = 'reserver/season_edit_form.html'
	form_class = SeasonForm
	
	def get_form_kwargs(self):
		kwargs = super(SeasonEditView, self).get_form_kwargs()
		kwargs.update({'request': self.request})
		return kwargs
		
	def get_success_url(self):
		return reverse_lazy('seasons')
	
	def get(self, request, *args, **kwargs):
		"""Handles creation of new blank form/formset objects."""
		self.object = get_object_or_404(Season, pk=self.kwargs.get('pk'))
		form_class = self.get_form_class()
		form = self.get_form(form_class)
			
		form.initial={
			
			'name':self.object.name,
			'long_education_price':self.object.long_education_price,
			'long_research_price':self.object.long_research_price,
			'long_boa_price':self.object.long_boa_price,
			'long_external_price':self.object.long_external_price,
			'short_education_price':self.object.short_education_price,
			'short_research_price':self.object.short_research_price,
			'short_boa_price':self.object.short_boa_price,
			'short_external_price':self.object.short_external_price,
			'breakfast_price':self.object.breakfast_price,
			'lunch_price':self.object.lunch_price,
			'dinner_price':self.object.dinner_price,
			'season_event_start_date':self.object.season_event.start_time,
			'season_event_end_date':self.object.season_event.end_time,
			'internal_order_event_date':self.object.internal_order_event.start_time,
			'external_order_event_date':self.object.external_order_event.start_time
			
		}

		return self.render_to_response(
			self.get_context_data(
				form=form
			)
		)
		
	def post(self, request, *args, **kwargs):
		self.object = get_object_or_404(Season, pk=self.kwargs.get('pk'))
		form_class = self.get_form_class()
		form = self.get_form(form_class)
		# check if form is valid, handle outcome
		if form.is_valid():
			return self.form_valid(form)
		else:
			return self.form_invalid(form)
			
	def form_valid(self, form):
		"""Called when all our forms are valid. Creates a Cruise with Participants and CruiseDays."""
		season = form.save(commit=False)
		season.season_event.start_time = form.cleaned_data.get("season_event_start_date")
		season.season_event.end_time = form.cleaned_data.get("season_event_end_date").replace(hour=23, minute=59)
		season.season_event.save()
		season.internal_order_event.start_time = form.cleaned_data.get("internal_order_event_date")
		season.internal_order_event.save()
		season.external_order_event.start_time = form.cleaned_data.get("external_order_event_date")
		season.external_order_event.save()
		season.save()
		self.object = form.save()
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(season))
		action.action = "updated season"
		action.save()
		delete_season_notifications(season)
		create_season_notifications(season)
		return HttpResponseRedirect(self.get_success_url())
		
	def form_invalid(self, form):
		"""Throw form back at user."""
		return self.render_to_response(
			self.get_context_data(
				form=form
			)
		)

class SeasonDeleteView(DeleteView):
	model = Season
	template_name = 'reserver/season_delete_form.html'
	
	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "deleted season"
		action.save()
		return reverse_lazy('seasons')
	
# cruise invoice views

class CreateListPrice(CreateView):
	model = ListPrice
	template_name = 'reserver/listprice_create_form.html'
	form_class = ListPriceForm
	
	def get_success_url(self):
		return reverse_lazy('cruise-invoices', kwargs={'pk': InvoiceInformation.objects.get(pk=self.kwargs['pk']).cruise.pk})
		
	def form_valid(self, form):
		form.instance.invoice = InvoiceInformation.objects.get(pk=self.kwargs['pk'])
		action = Action(user=self.request.user, timestamp=timezone.now(), target=form.instance.invoice)
		action.action = "added list price " + str(form.instance) + " (" + str(form.instance.price) + " NOK)"
		action.save()
		return super(CreateListPrice, self).form_valid(form)
		
class UpdateListPrice(UpdateView):
	model = ListPrice
	template_name = 'reserver/listprice_edit_form.html'
	form_class = ListPriceForm
	
	def get_success_url(self):
		return reverse_lazy('cruise-invoices', kwargs={'pk': self.object.invoice.cruise.pk})

	def form_valid(self, form):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=form.instance.invoice)
		action.action = "updated list price " + str(form.instance) + " (" + str(form.instance.price) + " NOK)"
		action.save()
		return super(UpdateListPrice, self).form_valid(form)
		
class DeleteListPrice(DeleteView):
	model = ListPrice
	template_name = 'reserver/listprice_delete_form.html'
	
	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=self.object.invoice)
		action.action = "deleted list price " + str(self.object) + " (" + str(self.object.price) + " NOK)"
		action.save()
		return reverse_lazy('cruise-invoices', kwargs={'pk': self.object.invoice.cruise.pk})

def view_cruise_invoices(request, pk):
	cruise = get_object_or_404(Cruise, pk=pk)
	if (request.user.pk == cruise.leader.pk or request.user in cruise.owner.all() or request.user.is_superuser):
		invoices = InvoiceInformation.objects.filter(cruise=pk)
	else:
		raise PermissionDenied
	return render(request, 'reserver/cruise_invoices.html', {'cruise': cruise, 'invoices': invoices})

def admin_invoice_view(request):
	if (request.user.is_superuser):
		unsent_invoices = InvoiceInformation.objects.filter(is_sent=False, cruise__is_approved=True, cruise__cruise_end__lte=timezone.now())
		sent_invoices = InvoiceInformation.objects.filter(is_sent=True, cruise__is_approved=True, cruise__cruise_end__lte=timezone.now())
		
		cruises_badge = len(get_cruises_need_attention())
		users_badge = len(get_users_not_approved())
		overview_badge = cruises_badge + users_badge + len(get_unapproved_cruises())

	else:
		raise PermissionDenied
		
	return render(request, 'reserver/admin_invoices.html', {'overview_badge':overview_badge, 'cruises_badge':cruises_badge, 'users_badge':users_badge, 'unsent_invoices': unsent_invoices, 'sent_invoices': sent_invoices})

def mark_invoice_as_sent(request, pk):
	invoice = get_object_or_404(InvoiceInformation, pk=pk)
	if (request.user.is_superuser):
		invoice.is_sent = True
		invoice.save()
		action = Action(user=request.user, target=str(invoice))
		action.action = "marked as sent"
		action.timestamp = timezone.now()
		action.save()
		messages.add_message(request, messages.SUCCESS, mark_safe('Invoice "' + str(invoice) + '" marked as sent.'))
	else:
		raise PermissionDenied
	return redirect(request.META['HTTP_REFERER'])

def mark_invoice_as_unsent(request, pk):
	invoice = get_object_or_404(InvoiceInformation, pk=pk)
	if (request.user.is_superuser):
		invoice.is_sent = False
		invoice.save()
		action = Action(user=request.user, target=str(invoice))
		action.action = "marked as unsent"
		action.timestamp = timezone.now()
		action.save()
		messages.add_message(request, messages.SUCCESS, mark_safe('Invoice "' + str(invoice) + '" marked as unsent.'))
	else:
		raise PermissionDenied
	return redirect(request.META['HTTP_REFERER'])
	
# organization views

def admin_organization_view(request):
	organizations = list(Organization.objects.all())
	cruises_badge = len(get_cruises_need_attention())
	users_badge = len(get_users_not_approved())
	overview_badge = cruises_badge + users_badge + len(get_unapproved_cruises())
	return render(request, 'reserver/admin_organizations.html', {'overview_badge':overview_badge, 'cruises_badge':cruises_badge, 'users_badge':users_badge, 'organizations':organizations})	
		
class CreateOrganization(CreateView):
	model = Organization
	template_name = 'reserver/organization_create_form.html'
	form_class = OrganizationForm
	
	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "created organization"
		action.save()
		return reverse_lazy('organizations')
		
class OrganizationEditView(UpdateView):
	model = Organization
	template_name = 'reserver/organization_edit_form.html'
	form_class = OrganizationForm
	
	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "edited organization"
		action.save()
		return reverse_lazy('organizations')

class OrganizationDeleteView(DeleteView):
	model = Organization
	template_name = 'reserver/organization_delete_form.html'
	
	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "deleted organization"
		action.save()
		return reverse_lazy('organizations')
	
# category views

def admin_eventcategory_view(request):
	from reserver.utils import check_default_models
	check_default_models()
	eventcategories = list(EventCategory.objects.all())
	cruises_badge = len(get_cruises_need_attention())
	users_badge = len(get_users_not_approved())
	overview_badge = cruises_badge + users_badge + len(get_unapproved_cruises())
	return render(request, 'reserver/admin_eventcategories.html', {'overview_badge':overview_badge, 'cruises_badge':cruises_badge, 'users_badge':users_badge, 'eventcategories':eventcategories})	

class CreateEventCategory(CreateView):
	model = EventCategory
	template_name = 'reserver/eventcategory_create_form.html'
	form_class = EventCategoryForm
	
	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "created event category"
		action.save()
		return reverse_lazy('eventcategories')
		
class EventCategoryEditView(UpdateView):
	model = EventCategory
	template_name = 'reserver/eventcategory_edit_form.html'
	form_class = EventCategoryForm
	
	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "edited event category"
		action.save()
		return reverse_lazy('eventcategories')

class EventCategoryDeleteView(DeleteView):
	model = EventCategory
	template_name = 'reserver/eventcategory_delete_form.html'
	
	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "deleted event category"
		action.save()
		return reverse_lazy('eventcategories')
	
# event views
		
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
	
# notification views

def view_email_logs(request):
	import os.path
	email_logs = []
	email_log_files = os.listdir(settings.EMAIL_FILE_PATH)
	email_log_files.sort()
	for file in email_log_files:
		email_logs.append({
			"title": file,
			"url": "/uploads/debug-emails/"+file
		})

	cruises_badge = len(get_cruises_need_attention())
	users_badge = len(get_users_not_approved())
	overview_badge = cruises_badge + users_badge + len(get_unapproved_cruises())
	return render(request, 'reserver/admin_sent_emails.html', {'overview_badge':overview_badge, 'cruises_badge':cruises_badge, 'users_badge':users_badge, 'email_logs':email_logs})

def test_email_view(request):
	send_email('test@test.no', 'a message', EmailNotification())
	return HttpResponseRedirect(reverse_lazy('email_list_view'))
	
def purge_email_logs(request):
	import os
	import glob

	files = glob.glob(settings.EMAIL_FILE_PATH+'*')
	for file in files:
		if ".log" in file and "debug-emails" in file:
			os.remove(file)
		
	return HttpResponseRedirect(reverse_lazy('email_list_view'))

def admin_notification_view(request):
	from reserver.utils import check_default_models, default_email_templates
	default_template_titles = [sublist[0] for sublist in default_email_templates]
	check_default_models()
	notifications = EmailNotification.objects.filter(is_special=True)
	email_templates = EmailTemplate.objects.all()
	cruises_badge = len(get_cruises_need_attention())
	users_badge = len(get_users_not_approved())
	overview_badge = cruises_badge + users_badge + len(get_unapproved_cruises())
	return render(request, 'reserver/admin_notifications.html', {'overview_badge':overview_badge, 'cruises_badge':cruises_badge, 'users_badge':users_badge, 'notifications':notifications, 'email_templates':email_templates, 'default_templates':default_template_titles})
	
class CreateNotification(CreateView):
	model = EmailNotification
	template_name = 'reserver/notification_create_form.html'
	form_class = NotificationForm
	
	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "created notification"
		action.save()
		return reverse_lazy('notifications')
		
	def get_form_kwargs(self):
		kwargs = super(CreateNotification, self).get_form_kwargs()
		kwargs.update({'request': self.request})
		return kwargs
	
	def get(self, request, *args, **kwargs):
		"""Handles creation of new blank form/formset objects."""
		self.object = None
		form_class = self.get_form_class()
		form = self.get_form(form_class)

		return self.render_to_response(
			self.get_context_data(
				form=form
			)
		)
		
	def post(self, request, *args, **kwargs):
		self.object = None
		form_class = self.get_form_class()
		form = self.get_form(form_class)
		# check if form is valid, handle outcome
		if form.is_valid():
			return self.form_valid(form)
		else:
			return self.form_invalid(form)
			
	def form_valid(self, form):
		notification = form.save(commit=False)
		notification.is_special = True
		notification.save()
		self.object = form.save()
		return HttpResponseRedirect(self.get_success_url())
		
	def form_invalid(self, form):
		"""Throw form back at user."""
		return self.render_to_response(
			self.get_context_data(
				form=form
			)
		)
		
class NotificationEditView(UpdateView):
	model = EmailNotification
	template_name = 'reserver/notification_edit_form.html'
	form_class = NotificationForm
	
	def get_form_kwargs(self):
		kwargs = super(NotificationEditView, self).get_form_kwargs()
		kwargs.update({'request': self.request})
		return kwargs
	
	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "edited notification"
		action.save()
		return reverse_lazy('notifications')
	
	def get(self, request, *args, **kwargs):
		self.object = get_object_or_404(EmailNotification, pk=self.kwargs.get('pk'))
		form_class = self.get_form_class()
		form = self.get_form(form_class)
			
		form.initial={
		
			'recips':self.object.recipients.all(),
			'event':self.object.event,
			'template':self.object.template,
			
		}

		return self.render_to_response(
			self.get_context_data(
				form=form
			)
		)
		
	def post(self, request, *args, **kwargs):
		self.object = get_object_or_404(EmailNotification, pk=self.kwargs.get('pk'))
		form_class = self.get_form_class()
		form = self.get_form(form_class)
		# check if form is valid, handle outcome
		if form.is_valid():
			return self.form_valid(form)
		else:
			return self.form_invalid(form)
			
	def form_valid(self, form):
		notification = form.save(commit=False)
		notification.is_special = True
		notification.save()
		self.object = form.save()
		return HttpResponseRedirect(self.get_success_url())
		
	def form_invalid(self, form):
		"""Throw form back at user."""
		return self.render_to_response(
			self.get_context_data(
				form=form
			)
		)

class NotificationDeleteView(DeleteView):
	model = EmailNotification
	template_name = 'reserver/notification_delete_form.html'
	success_url = reverse_lazy('notifications')
	
	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "deleted notification"
		action.save()
		return reverse_lazy('notifications')
	
class CreateEmailTemplate(CreateView):
	model = EmailTemplate
	template_name = 'reserver/email_template_create_form.html'
	form_class = EmailTemplateForm
	
	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "created email template"
		action.save()
		return reverse_lazy('notifications')
		
	def get_form_kwargs(self):
		kwargs = super(CreateEmailTemplate, self).get_form_kwargs()
		kwargs.update({'request': self.request})
		return kwargs
	
	def get(self, request, *args, **kwargs):
		self.object = None
		form_class = self.get_form_class()
		form = self.get_form(form_class)

		return self.render_to_response(
			self.get_context_data(
				form=form
			)
		)
		
	def post(self, request, *args, **kwargs):
		self.object = None
		form_class = self.get_form_class()
		form = self.get_form(form_class)
		# check if form is valid, handle outcome
		if form.is_valid():
			return self.form_valid(form)
		else:
			return self.form_invalid(form)
			
	def form_valid(self, form):
		template = form.save(commit=False)
		if form.cleaned_data.get("time_before_hours") is not None:
			hours = form.cleaned_data.get("time_before_hours")
		else:
			hours = 0
		if form.cleaned_data.get("time_before_days") is not None:
			days = form.cleaned_data.get("time_before_days")
		else:
			days = 0
		if form.cleaned_data.get("time_before_weeks") is not None:
			weeks = form.cleaned_data.get("time_before_weeks")
		else:
			weeks = 0
		if hours == days == weeks == 0:
			template.time_before = None
		else:
			template.time_before = datetime.timedelta(hours=hours, days=days, weeks=weeks)
		template.save()
		self.object = form.save()
		return HttpResponseRedirect(self.get_success_url())
		
	def form_invalid(self, form):
		"""Throw form back at user."""
		return self.render_to_response(
			self.get_context_data(
				form=form
			)
		)
		
class EmailTemplateEditView(UpdateView):
	model = EmailTemplate
	template_name = 'reserver/email_template_edit_form.html'
	form_class = EmailTemplateForm
	
	def get_form_kwargs(self):
		kwargs = super(EmailTemplateEditView, self).get_form_kwargs()
		kwargs.update({'request': self.request})
		return kwargs
	
	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "edited email template"
		action.save()
		return reverse_lazy('notifications')
	
	def get(self, request, *args, **kwargs):
		"""Handles creation of new blank form/formset objects."""
		self.object = get_object_or_404(EmailTemplate, pk=self.kwargs.get('pk'))
		form_class = self.get_form_class()
		form = self.get_form(form_class)
		
		hours = days = weeks = None
		if self.object.time_before is not None and self.object.time_before.total_seconds() > 0:
			time = self.object.time_before
			weeks = int(time.days / 7)
			time -= datetime.timedelta(days=weeks * 7)
			days = time.days
			time -= datetime.timedelta(days=days)
			hours = int(time.seconds / 3600)
		
		form.initial={
		
			'title':self.object.title, 
			'group':self.object.group,
			'message':self.object.message, 
			'is_active':self.object.is_active, 
			'is_muteable':self.object.is_muteable,
			'date':self.object.date, 
			'time_before_hours':hours, 
			'time_before_days':days, 
			'time_before_weeks':weeks,
			
		}

		return self.render_to_response(
			self.get_context_data(
				form=form
			)
		)
		
	def post(self, request, *args, **kwargs):
		self.object = get_object_or_404(EmailTemplate, pk=self.kwargs.get('pk'))
		form_class = self.get_form_class()
		form = self.get_form(form_class)
		# check if form is valid, handle outcome
		if form.is_valid():
			return self.form_valid(form)
		else:
			return self.form_invalid(form)
			
	def form_valid(self, form):
		template = form.save(commit=False)
		if form.cleaned_data.get("time_before_hours") is not None:
			hours = form.cleaned_data.get("time_before_hours")
		else:
			hours = 0
		if form.cleaned_data.get("time_before_days") is not None:
			days = form.cleaned_data.get("time_before_days")
		else:
			days = 0
		if form.cleaned_data.get("time_before_weeks") is not None:
			weeks = form.cleaned_data.get("time_before_weeks")
		else:
			weeks = 0
		if hours == days == weeks == 0:
			template.time_before = None
		else:
			template.time_before = datetime.timedelta(hours=hours, days=days, weeks=weeks)
		template.save()
		self.object = form.save()
		return HttpResponseRedirect(self.get_success_url())
		
	def form_invalid(self, form):
		"""Throw form back at user."""
		return self.render_to_response(
			self.get_context_data(
				form=form
			)
		)
		
class EmailTemplateDefaultEditView(UpdateView):
	model = EmailTemplate
	template_name = 'reserver/email_template_default_edit_form.html'
	form_class = EmailTemplateDefaultForm
	
	def get_form_kwargs(self):
		kwargs = super(EmailTemplateDefaultEditView, self).get_form_kwargs()
		kwargs.update({'request': self.request})
		return kwargs
	
	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "edited built-in email template"
		action.save()
		return reverse_lazy('notifications')
	
	def get(self, request, *args, **kwargs):
		"""Handles creation of new blank form/formset objects."""
		self.object = get_object_or_404(EmailTemplate, pk=self.kwargs.get('pk'))
		form_class = self.get_form_class()
		form = self.get_form(form_class)
		
		hours = days = weeks = None
		if self.object.time_before is not None and self.object.time_before.total_seconds() > 0:
			time = self.object.time_before
			weeks = int(time.days / 7)
			time -= datetime.timedelta(days=weeks * 7)
			days = time.days
			time -= datetime.timedelta(days=days)
			hours = int(time.seconds / 3600)
		
		form.initial={
		
			'title':self.object.title, 
			'group':self.object.group,
			'message':self.object.message, 
			'is_active':self.object.is_active, 
			'is_muteable':self.object.is_muteable,
			'date':self.object.date, 
			'time_before_hours':hours, 
			'time_before_days':days, 
			'time_before_weeks':weeks,
			
		}

		return self.render_to_response(
			self.get_context_data(
				form=form
			)
		)
		
	def post(self, request, *args, **kwargs):
		self.object = get_object_or_404(EmailTemplate, pk=self.kwargs.get('pk'))
		form_class = self.get_form_class()
		form = self.get_form(form_class)
		# check if form is valid, handle outcome
		if form.is_valid():
			return self.form_valid(form)
		else:
			return self.form_invalid(form)
			
	def form_valid(self, form):
		template = form.save(commit=False)
		template.save()
		self.object = form.save()
		return HttpResponseRedirect(self.get_success_url())
		
	def form_invalid(self, form):
		"""Throw form back at user."""
		return self.render_to_response(
			self.get_context_data(
				form=form
			)
		)
		
class EmailTemplateDeleteView(DeleteView):
	model = EmailTemplate
	template_name = 'reserver/email_template_delete_form.html'
	
	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "deleted email template"
		action.save()
		return reverse_lazy('notifications')
	
# cruise receipt JSON view

@csrf_exempt
def cruise_receipt_source(request):
	json_data = json.loads(request.body.decode("utf-8"))
	try:
		json_data["season"] = get_season_containing_time(datetime.datetime.strptime(json_data["dates"][0], '%Y-%m-%d'))
	except:
		pass
	if request.user.is_authenticated:
		return JsonResponse(json.dumps(get_cruise_receipt(**json_data), ensure_ascii=True), safe=False)
	
# calendar views
	
def calendar_event_source(request):
	events = list(Event.objects.filter(start_time__isnull=False).distinct())
	calendar_events = {"success": 1, "result": []}
	for event in events:
		if not (event.is_cruise_day() and not event.cruiseday.cruise.is_approved):
			if event.start_time is not None and event.end_time is not None:
				day_is_in_season = False
				
				colour = "undefined"
				icon = "undefined"
				category = "undefined"
					
				try:
					colour = event.category.colour
				except:
					pass
				
				try:
					icon = event.category.icon
				except:
					pass
					
				try:
					category = str(event.category)
				except:
					pass
					
				if event.is_cruise_day():
					event_class = "event-info"
					css_class = "cruise-day"
					
					if category == "undefined" or not category:
						category = "Cruise day"
				elif event.is_season():
					event_class = "event-success"
					css_class = "season"
					day_is_in_season = True
					
					if category == "undefined" or not category:
						category = "Season"
				else:
					event_class = "event-warning"
					css_class = "generic-event"
					
				if category == "undefined" or not category:
					category = "Other"
					
				calendar_event = {
					"id": event.pk,
					"title": "Event",
					"url": "test",
					"class": event_class,
					"cssClass": css_class,
					"category": category,
					"icon": icon,
					"colour": colour,
					"day_is_in_season": day_is_in_season,
					"start": event.start_time.timestamp()*1000, # Milliseconds
					"end": event.end_time.timestamp()*1000, # Milliseconds
				}
				
				if request.user.is_authenticated:
					if event.name is not "":
						if event.is_cruise_day():
							if event.cruiseday.cruise.is_viewable_by(request.user):
								calendar_event["title"] = event.cruiseday.cruise.get_short_name()
							else:
								calendar_event["title"] = "Cruise"
						else:
							calendar_event["title"] = event.name
							
					if event.description is not "":
						calendar_event["description"] = event.description
					elif event.is_cruise_day() and event.cruiseday.cruise.is_viewable_by(request.user):
						calendar_event["cruise_pk"] = event.cruiseday.cruise.pk
						if event.cruiseday.description is not "":
							calendar_event["description"] = event.cruiseday.description
						else:
							calendar_event["description"] = "This cruise day has no description."
					else: 
						calendar_event["description"] = "This event has no description."
				
					calendar_event["calButton"] = render_add_cal_button(event.name, event.description, event.start_time, event.end_time)
			
				calendar_events["result"].append(calendar_event)
	return JsonResponse(json.dumps(calendar_events, ensure_ascii=True), safe=False)