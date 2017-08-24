from django.shortcuts import get_list_or_404, get_object_or_404, render, redirect
from django.db.models import Q
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.views.generic import ListView
from django.contrib.auth.decorators import login_required
from django.views.generic.detail import SingleObjectMixin
from django.contrib import messages
from django.utils.safestring import mark_safe
from reserver.utils import render_add_cal_button

from reserver.utils import check_for_and_fix_users_without_userdata
from reserver.models import Cruise, CruiseDay, Participant, UserData, Event, Organization, Season, EmailNotification, EmailTemplate, EventCategory, Document, Equipment, InvoiceInformation
from reserver.forms import CruiseForm, CruiseDayFormSet, ParticipantFormSet, UserForm, UserRegistrationForm, UserDataForm, EventCategoryForm
from reserver.forms import SeasonForm, EventForm, NotificationForm, EmailTemplateForm, DocumentFormSet, EquipmentFormSet, OrganizationForm, InvoiceInformationForm, InvoiceFormSet
from reserver.test_models import create_test_models
from reserver import jobs
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm

from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.template import loader
from django.utils import timezone
from reserver.utils import init
import datetime
import json

def remove_dups_keep_order(lst):
	without_dups = []
	for item in lst:
		if (item not in without_dups):
			without_dups.append(item)
	return without_dups

def get_cruises_need_attention():
	return remove_dups_keep_order(list(Cruise.objects.filter(is_submitted=True, is_approved=True, information_approved=False, cruise_end__gte=timezone.now())))
	
def get_upcoming_cruises():
	return remove_dups_keep_order(list(Cruise.objects.filter(is_submitted=True, is_approved=True, information_approved=True, cruise_end__gte=timezone.now())))

def get_unapproved_cruises():
	return remove_dups_keep_order(Cruise.objects.filter(is_submitted=True, is_approved=False, cruise_end__gte=timezone.now()).order_by('submit_date'))
	
def get_users_not_approved():
	check_for_and_fix_users_without_userdata()
	return list(UserData.objects.filter(role=""))
	
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
	success_url = reverse_lazy('user-page')
	
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
		return self.render_to_response(
			self.get_context_data(
				form=form,
				cruiseday_form=cruiseday_form,
				participant_form=participant_form,
				document_form=document_form,
				equipment_form=equipment_form,
				invoice_form=invoice_form
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
			Cruise.organization = Cruise.leader.organization
		except:
			pass
		form.cleaned_data["leader"] = self.request.user
		if hasattr(self, "request"):
			print("ok, we have a request")
			# check whether we're saving or submitting the form
			if self.request.POST.get("save_cruise"):
				Cruise.is_submitted = False
			elif self.request.POST.get("submit_cruise"):
				print("ok, we're submitting")
				cruiseday_form = CruiseDayFormSet(self.request.POST)
				participant_form = ParticipantFormSet(self.request.POST)
				cruise_days = cruiseday_form.cleaned_data
				cruise_participants = participant_form.cleaned_data
				if (Cruise.is_submittable(user=self.request.user, cleaned_data=form.cleaned_data, cruise_days=cruise_days, cruise_participants=cruise_participants)):
					print("ok, it's valid")
					Cruise.is_submitted = True
					Cruise.submit_date = timezone.now()
					messages.add_message(self.request, messages.INFO, mark_safe('Cruise successfully submitted. You may track its approval status under "<a href="#cruiseTop">Your Cruises</a>".'))
				else:
					print("nope, it's invalid")
					Cruise.is_submitted = False
					messages.add_message(self.request, messages.ERROR, mark_safe('Cruise could not be submitted:' + str(Cruise.get_missing_information_string(cleaned_data=form.cleaned_data, cruise_days=cruise_days, cruise_participants=cruise_participants)) + 'You may review and add any missing or invalid information under its entry in your saved cruise drafts below.'))
		print(Cruise.is_submitted)
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
				invoice_form=invoice_form
			)
		)
	
class CruiseEditView(UpdateView):
	template_name = 'reserver/cruise_edit_form.html'
	model = Cruise
	form_class = CruiseForm
	success_url = reverse_lazy('user-page')
	
	def get_form_kwargs(self):
		kwargs = super(CruiseEditView, self).get_form_kwargs()
		kwargs.update({'request': self.request})
		return kwargs
	
	def get(self, request, *args, **kwargs):
		"""Handles creation of new blank form/formset objects."""
		self.object = get_object_or_404(Cruise, pk=self.kwargs.get('pk'))
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
				invoice_form=invoice_form
			)
		)
	
	def post(self, request, *args, **kwargs):
		"""Handles receiving submitted form and formset data and checking their validity."""
		self.object = get_object_or_404(Cruise, pk=self.kwargs.get('pk'))
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
		Cruise = form.save(commit=False)
		Cruise.leader = self.request.user
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
		messages.add_message(self.request, messages.INFO, mark_safe('Cruise ' + str(Cruise) + ' updated.'))
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
				invoice_form=invoice_form
			)
		)
		
class CruiseView(CruiseEditView):
	template_name = 'reserver/cruise_view_form.html'
	
	def get(self, request, *args, **kwargs):
		self.object = get_object_or_404(Cruise, pk=self.kwargs.get('pk'))
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
				invoice_form=invoice_form
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
				invoice_form=invoice_form
			)
		)

class CruiseDeleteView(DeleteView):
	model = Cruise
	template_name = 'reserver/cruise_delete_form.html'
	success_url = reverse_lazy('user-page')
	
def index_view(request):
	init()
	return render(request, 'reserver/index.html')

def submit_cruise(request, pk):
	cruise = get_object_or_404(Cruise, pk=pk)
	if request.user == cruise.leader or request.user.is_superuser:
		if not cruise.is_submittable(user=request.user):
			messages.add_message(request, messages.ERROR, mark_safe('Cruise could not be submitted: ' + str(cruise.get_missing_information_string()) + 'You may review and add any missing or invalid information under its entry in your saved cruise drafts below.'))
		else:
			cruise.is_submitted = True
			cruise.is_approved = False
			cruise.save()
			cruise.submit_date = timezone.now()
			messages.add_message(request, messages.INFO, mark_safe('Cruise successfully submitted. You may track its approval status under "<a href="#cruiseTop">Your Cruises</a>".'))
	else:
		raise PermissionDenied
	return redirect(request.META['HTTP_REFERER'])
	
def unsubmit_cruise(request, pk):
	cruise = get_object_or_404(Cruise, pk=pk)
	if (request.user.pk == cruise.leader.pk) or request.user.is_superuser:
		cruise.is_submitted = False
		cruise.is_approved = False
		cruise.save()
		messages.add_message(request, messages.WARNING, mark_safe('Cruise ' + str(cruise) + ' cancelled.'))
	else:
		raise PermissionDenied
	return redirect(request.META['HTTP_REFERER'])

# admin-only
	
def approve_cruise(request, pk):
	cruise = get_object_or_404(Cruise, pk=pk)
	if request.user.is_superuser:
		cruise.is_approved = True
		cruise.save()
		if cruise.information_approved:
			create_upcoming_cruise_and_deadline_notifications(cruise)
		else:
			create_cruise_notifications(cruise, 'Cruise deadlines')
			create_cruise_administration_notification(cruise, 'Cruise approved')
	else:
		raise PermissionDenied
	return redirect(request.META['HTTP_REFERER'])
	
def unapprove_cruise(request, pk):
	cruise = get_object_or_404(Cruise, pk=pk)
	if request.user.is_superuser:
		cruise.is_approved = False
		cruise.save()
		delete_cruise_deadline_notifications(cruise)
		create_cruise_administration_notification(cruise, 'Cruise unapproved')
	else:
		raise PermissionDenied
	return redirect(request.META['HTTP_REFERER'])
	
def approve_cruise_information(request, pk):
	cruise = get_object_or_404(Cruise, pk=pk)
	if request.user.is_superuser:
		cruise.information_approved = True
		cruise.save()
		if cruise.is_approved:
			create_cruise_notifications(cruise, 'Cruise departure')
			create_cruise_administration_notification(cruise, 'Cruise information approved')
	else:
		raise PermissionDenied
	return redirect(request.META['HTTP_REFERER'])
	
def unapprove_cruise_information(request, pk):
	cruise = get_object_or_404(Cruise, pk=pk)
	if request.user.is_superuser:
		cruise.information_approved = False
		cruise.save()
		delete_upcoming_cruise_notifications(cruise)
		create_cruise_administration_notification(cruise, 'Cruise information unapproved')
	else:
		raise PermissionDenied
	return redirect(request.META['HTTP_REFERER'])
	
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
		user_data.role = "admin"
		user_data.save()
		user.save()
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
		user_data.role = "internal"
		user_data.save()
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
		user_data.role = "external"
		user_data.save()
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
	else:
		raise PermissionDenied
	return redirect(request.META['HTTP_REFERER'])

#Methods for automatically creating and deleting notifications related to cruises and seasons when they are created

cruise_deadline_email_templates = {

	'16 days missing info',
	'Last cancellation date',
	
}

cruise_administration_email_templates = {

	'Cruise approved',
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
	#jobs.create_jobs(jobs.scheduler, notifs)
	
#To be run when a cruise is approved
def create_cruise_administration_notification(cruise, template):
	cruise_day_event = CruiseDay.objects.filter(cruise=cruise).order_by('event__start_time').first().event
	notif = EmailNotification()
	notif.event = cruise_day_event
	notif.template = EmailTemplate.objects.get(title=template)
	notif.save()
	#jobs.create_jobs(jobs.scheduler, [notif])
	
#To be run when a cruise's information is approved, and the cruise goes from being unapproved to approved
def create_upcoming_cruise_and_deadline_notifications(cruise):
	create_cruise_notifications(cruise, 'Cruise deadlines')
	create_cruise_notifications(cruise, 'Cruise departure')
	
#To be run when a cruise is unapproved
def delete_cruise_deadline_notifications(cruise):
	delete_upcoming_cruise_notifications(cruise)

#To be run when a cruise's information is unapproved or the cruise is unapproved
def delete_cruise_departure_notifications(cruise):
	pass
	
#To be run when a new season is made
def create_season_notifications(season):
	pass
	
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
		messages.add_message(request, messages.INFO, "Profile updated.")
		return super(UserView, self).post(request, *args, **kwargs)
		
	def get_context_data(self, **kwargs):
		context = super(UserView, self).get_context_data(**kwargs)
		now = timezone.now()
		
		# add submitted cruises to context
		cruises = list(Cruise.objects.filter(leader=self.request.user, is_submitted=True))
		cruise_start = []
		for cruise in cruises:
			try:
				cruise_start.append(CruiseDay.objects.filter(cruise=cruise.pk).first().event.start_time)
			except AttributeError:
				cruise_start.append('No cruise days')
		submitted_cruises = [{'item1': t[0], 'item2': t[1]} for t in zip(cruises, cruise_start)]
		context['my_submitted_cruises'] = list(reversed(submitted_cruises))
		
		# add unsubmitted cruises to context
		cruises = list(Cruise.objects.filter(leader=self.request.user, is_submitted=False))
		cruise_start = []
		for cruise in cruises:
			try:
				cruise_start.append(CruiseDay.objects.filter(cruise=cruise.pk).first().event.start_time)
			except AttributeError:
				cruise_start.append('No cruise days')
		unsubmitted_cruises = [{'item1': t[0], 'item2': t[1]} for t in zip(cruises, cruise_start)]
		context['my_unsubmitted_cruises'] = list(reversed(unsubmitted_cruises))
		return context
	
class CurrentUserView(UserView):
	def get_object(self):
		return self.request.user
	
def admin_view(request):
	cruises_need_attention = get_cruises_need_attention()
	upcoming_cruises = get_upcoming_cruises()
	unapproved_cruises = get_unapproved_cruises()
	print(unapproved_cruises)
	users_not_approved = get_users_not_approved()
	cruises_badge = len(cruises_need_attention)
	users_badge = len(users_not_approved)
	overview_badge = cruises_badge + users_badge + len(get_unapproved_cruises())
	if(len(cruises_need_attention) > 1):
		messages.add_message(request, messages.WARNING, 'Warning: %s upcoming cruises are missing information.' % str(len(cruises_need_attention)))
	elif(len(cruises_need_attention) == 1):
		messages.add_message(request, messages.WARNING, 'Warning: %s upcoming cruise is missing information.' % str(len(cruises_need_attention)))
	if(len(users_not_approved) > 1):
		messages.add_message(request, messages.INFO, 'Info: %s users need attention.' % str(len(users_not_approved)))
	elif(len(users_not_approved) == 1):
		messages.add_message(request, messages.INFO, 'Info: %s user needs attention.' % str(len(users_not_approved)))
	if(len(unapproved_cruises) > 1):
		messages.add_message(request, messages.INFO, 'Info: %s cruises are awaiting approval.' % str(len(unapproved_cruises)))
	elif(len(unapproved_cruises) == 1):
		messages.add_message(request, messages.INFO, 'Info: %s cruise is awaiting approval.' % str(len(unapproved_cruises)))
	return render(request, 'reserver/admin_overview.html', {'overview_badge':overview_badge, 'cruises_badge':cruises_badge, 'users_badge':users_badge, 'unapproved_cruises':unapproved_cruises, 'upcoming_cruises':upcoming_cruises, 'cruises_need_attention':cruises_need_attention, 'users_not_verified':users_not_approved})

def admin_cruise_view(request):
	cruises = list(Cruise.objects.filter(is_approved=True))
	cruises_need_attention = get_cruises_need_attention()
	users_not_approved = get_users_not_approved()
	cruises_badge = len(get_cruises_need_attention())
	users_badge = len(users_not_approved)
	overview_badge = cruises_badge + users_badge + len(get_unapproved_cruises())
	if(len(cruises_need_attention) > 1):
		messages.add_message(request, messages.WARNING, 'Warning: %s upcoming cruises are missing information.' % str(len(cruises_need_attention)))
	elif(len(cruises_need_attention) == 1):
		messages.add_message(request, messages.WARNING, 'Warning: %s upcoming cruise is missing information.' % str(len(cruises_need_attention)))
	return render(request, 'reserver/admin_cruises.html', {'overview_badge':overview_badge, 'overview_badge':overview_badge, 'cruises_badge':cruises_badge, 'users_badge':users_badge, 'cruises':cruises})
	
def admin_user_view(request):
	users = list(UserData.objects.exclude(role="").order_by('-role', 'user__last_name', 'user__first_name'))
	users_not_approved = get_users_not_approved()
	cruises_badge = len(get_cruises_need_attention())
	users_badge = len(users_not_approved)
	overview_badge = cruises_badge + users_badge + len(get_unapproved_cruises())
	if(len(users_not_approved) > 1):
		messages.add_message(request, messages.INFO, 'Info: %s users need attention.' % str(len(users_not_approved)))
	elif(len(users_not_approved) == 1):
		messages.add_message(request, messages.INFO, 'Info: %s user needs attention.' % str(len(users_not_approved)))
	return render(request, 'reserver/admin_users.html', {'overview_badge':overview_badge, 'cruises_badge':cruises_badge, 'users_badge':users_badge, 'users':users})
	
def admin_event_view(request):
	all_events = list(Event.objects.all())
	events = []
	for event in all_events:
		if event.is_scheduled_event():
			events.append(event)
	cruises_badge = len(get_cruises_need_attention())
	users_badge = len(get_users_not_approved())
	overview_badge = cruises_badge + users_badge + len(get_unapproved_cruises())
	return render(request, 'reserver/admin_events.html', {'overview_badge':overview_badge, 'cruises_badge':cruises_badge, 'users_badge':users_badge, 'events':events})

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
	
def register_view(request):
		if request.method == 'POST':
			user_form = UserRegistrationForm(request.POST)
			userdata_form = UserDataForm(request.POST)
			if (userdata_form.is_valid() and user_form.is_valid()):
				user = user_form.save()
				ud = userdata_form.save(commit=False)
				ud.user = user
				ud.save()
				login(request, user)
				return HttpResponseRedirect(reverse_lazy('home'))
		else:
			user_form = UserRegistrationForm()
			userdata_form = UserDataForm()
		return render(request, 'reserver/register.html', {'userdata_form':userdata_form, 'user_form':user_form})

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
	success_url = reverse_lazy('seasons')
	
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
		return reverse_lazy('organizations')
		
class OrganizationEditView(UpdateView):
	model = Organization
	template_name = 'reserver/organization_edit_form.html'
	form_class = OrganizationForm
	
	def get_success_url(self):
		return reverse_lazy('organizations')

class OrganizationDeleteView(DeleteView):
	model = Organization
	template_name = 'reserver/organization_delete_form.html'
	success_url = reverse_lazy('organizations')
	
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
		return reverse_lazy('eventcategories')
		
class EventCategoryEditView(UpdateView):
	model = EventCategory
	template_name = 'reserver/eventcategory_edit_form.html'
	form_class = EventCategoryForm
	
	def get_success_url(self):
		return reverse_lazy('eventcategories')

class EventCategoryDeleteView(DeleteView):
	model = EventCategory
	template_name = 'reserver/eventcategory_delete_form.html'
	success_url = reverse_lazy('eventcategories')
	
# event views
		
class CreateEvent(CreateView):
	model = Event
	template_name = 'reserver/event_create_form.html'
	form_class = EventForm
	
	def get_success_url(self):
		return reverse_lazy('events')
		
class EventEditView(UpdateView):
	model = Event
	template_name = 'reserver/event_edit_form.html'
	form_class = EventForm

	def get_success_url(self):
		return reverse_lazy('events')

class EventDeleteView(DeleteView):
	model = Event
	template_name = 'reserver/event_delete_form.html'
	success_url = reverse_lazy('events')
	
# notification views

def admin_notification_view(request):
	notifications = EmailNotification.objects.filter(is_special=True)
	email_templates = EmailTemplate.objects.all()
	cruises_badge = len(get_cruises_need_attention())
	users_badge = len(get_users_not_approved())
	overview_badge = cruises_badge + users_badge + len(get_unapproved_cruises())
	return render(request, 'reserver/admin_notifications.html', {'overview_badge':overview_badge, 'cruises_badge':cruises_badge, 'users_badge':users_badge, 'notifications':notifications, 'email_templates':email_templates})
	
class CreateNotification(CreateView):
	model = EmailNotification
	template_name = 'reserver/notification_create_form.html'
	form_class = NotificationForm
	
	def get_success_url(self):
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
	
class CreateEmailTemplate(CreateView):
	model = EmailTemplate
	template_name = 'reserver/email_template_create_form.html'
	form_class = EmailTemplateForm
	
	def get_success_url(self):
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
		return reverse_lazy('notifications')
	
	def get(self, request, *args, **kwargs):
		"""Handles creation of new blank form/formset objects."""
		self.object = get_object_or_404(EmailTemplate, pk=self.kwargs.get('pk'))
		form_class = self.get_form_class()
		form = self.get_form(form_class)
		
		hours = days = weeks = None
		if self.object.time_before is not None and self.object.time_before.total_seconds() > 0:
			print("Initializing values")
			time = self.object.time_before
			weeks = int(time.days / 7)
			time -= datetime.timedelta(days=weeks * 7)
			days = time.days
			time -= datetime.timedelta(days=days)
			hours = int(time.seconds / 3600)
			print(weeks, days, hours)
		
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
		
class EmailTemplateDeleteView(DeleteView):
	model = EmailTemplate
	template_name = 'reserver/email_template_delete_form.html'
	success_url = reverse_lazy('notifications')
	
# calendar views
	
def calendar_event_source(request):
	events = list(Event.objects.filter(start_time__isnull=False).distinct())
	calendar_events = {"success": 1, "result": []}
	for event in events:
		if not (event.is_cruise_day() and not event.cruiseday.cruise.is_approved):
			if event.start_time is not None and event.end_time is not None:
				day_is_in_season = False
				if event.is_cruise_day():
					event_class = "event-info"
					css_class = "cruise-day"
				elif event.is_season():
					event_class = "event-success"
					css_class = "season"
					day_is_in_season = True
				else:
					event_class = "event-warning"
					css_class = "generic-event"
					
				calendar_event = {
					"id": event.pk,
					"title": "Event",
					"url": "test",
					"class": event_class,
					"cssClass": css_class,
					"day_is_in_season": day_is_in_season,
					"start": event.start_time.timestamp()*1000, # Milliseconds
					"end": event.end_time.timestamp()*1000, # Milliseconds
				}
				
				if request.user.is_authenticated:
					if event.name is not "":
						if event.is_cruise_day():
							calendar_event["title"] = event.cruiseday.cruise.get_short_name()
						else:
							calendar_event["title"] = event.name
							
					if event.description is not "":
						calendar_event["description"] = event.description
					elif event.is_cruise_day():
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