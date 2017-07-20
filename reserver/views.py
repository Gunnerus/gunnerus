from django.shortcuts import get_list_or_404, get_object_or_404, render, redirect
from django.db.models import Q
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.core.exceptions import PermissionDenied
from django.views.generic import ListView
from django.contrib.auth.decorators import login_required
from django.views.generic.detail import SingleObjectMixin
from django.contrib import messages
from django.utils.safestring import mark_safe

from reserver.models import Cruise, CruiseDay, Participant, UserData, Event, Organization, Season
from reserver.forms import CruiseForm, CruiseDayFormSet, ParticipantFormSet, UserForm, UserRegistrationForm, UserDataForm
from reserver.test_models import create_test_models
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm

from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.template import loader
import datetime
import json

def remove_dups_keep_order(lst):
	without_dups = []
	for item in lst:
		if(item not in without_dups):
			without_dups.append(item)
	return without_dups
	
def get_cruises_need_attention():
	return remove_dups_keep_order(list(Cruise.objects.filter(is_submitted=True, is_approved=True, information_approved=False, cruiseday__event__end_time__gte=datetime.datetime.now())))
	
def get_upcoming_cruises():
	return remove_dups_keep_order(list(Cruise.objects.filter(is_submitted=True, is_approved=True, information_approved=True, cruiseday__event__end_time__gte=datetime.datetime.now())))

def get_unapproved_cruises():
	return remove_dups_keep_order(list(Cruise.objects.filter(is_submitted=True, is_approved=False, cruiseday__event__end_time__gte=datetime.datetime.now()).order_by('submit_date')))
	
def get_users_not_approved():
	return  list(UserData.objects.filter(role='not approved'))
	
class CruiseList(ListView):
	model = Cruise
	template_name = 'reserver/cruise_list.html'
		
class CruiseCreateView(CreateView):
	template_name = 'reserver/cruise_create_form.html'
	model = Cruise
	form_class = CruiseForm
	success_url = reverse_lazy('user-page')
	
	def get(self, request, *args, **kwargs):
		"""Handles creation of new blank form/formset objects."""
		self.object = None
		form_class = self.get_form_class()
		form_class.user = request.user
		form = self.get_form(form_class)
		cruiseday_form = CruiseDayFormSet()
		participant_form = ParticipantFormSet()
		return self.render_to_response(
			self.get_context_data(
				form=form,
			    cruiseday_form=cruiseday_form,
				participant_form=participant_form
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
		# check if all our forms are valid, handle outcome
		if (form.is_valid() and cruiseday_form.is_valid() and participant_form.is_valid()):
			return self.form_valid(form, cruiseday_form, participant_form)
		else:
			return self.form_invalid(form, cruiseday_form, participant_form)
			
	def form_valid(self, form, cruiseday_form, participant_form):
		"""Called when all our forms are valid. Creates a Cruise with Participants and CruiseDays."""
		Cruise = form.save(commit=False)
		Cruise.leader = self.request.user
		# check whether we're saving or submitting the form
		if self.request.POST.get("save_cruise"):
			Cruise.is_submitted = False
		elif self.request.POST.get("submit_cruise"):
			if Cruise.is_submittable() or self.request.user.is_superuser:
				Cruise.is_submitted = True
				Cruise.submit_date = datetime.datetime.now()
			else:
				Cruise.is_submitted = False
				messages.add_message(self.request, messages.ERROR, mark_safe('Cruise could not be submitted:' + str(Cruise.get_missing_information_string())))
				return self.form_invalid(form, cruiseday_form, participant_form)
		Cruise.save()
		self.object = form.save()
		cruiseday_form.instance = self.object
		cruiseday_form.save()
		participant_form.instance = self.object
		participant_form.save()
		return HttpResponseRedirect(self.get_success_url())
		
	def form_invalid(self, form, cruiseday_form, participant_form):
		"""Throw form back at user."""
		return self.render_to_response(
			self.get_context_data(
				form=form,
			    cruiseday_form=cruiseday_form,
				participant_form=participant_form
			)
		)
	
class CruiseEditView(UpdateView):
	template_name = 'reserver/cruise_edit_form.html'
	model = Cruise
	form_class = CruiseForm
	success_url = reverse_lazy('user-page')
	
	def get(self, request, *args, **kwargs):
		"""Handles creation of new blank form/formset objects."""
		self.object = get_object_or_404(Cruise, pk=self.kwargs.get('pk'))
		form_class = self.get_form_class()
		form_class.user = request.user
		form = self.get_form(form_class)
		cruiseday_form = CruiseDayFormSet(instance=self.object)
		participant_form = ParticipantFormSet(instance=self.object)
			
		return self.render_to_response(
			self.get_context_data(
				form=form,
			    cruiseday_form=cruiseday_form,
				participant_form=participant_form
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
		# check if all our forms are valid, handle outcome
		if (form.is_valid() and cruiseday_form.is_valid() and participant_form.is_valid()):
			return self.form_valid(form, cruiseday_form, participant_form)
		else:
			return self.form_invalid(form, cruiseday_form, participant_form)
			
	def form_valid(self, form, cruiseday_form, participant_form):
		"""Called when all our forms are valid. Creates a Cruise with Participants and CruiseDays."""
		self.object = form.save()
		cruiseday_form.instance = self.object
		cruiseday_form.save()
		participant_form.instance = self.object
		participant_form.save()
		return HttpResponseRedirect(self.get_success_url())
		
	def form_invalid(self, form, cruiseday_form, participant_form):
		"""Throw form back at user."""
		return self.render_to_response(
			self.get_context_data(
				form=form,
			    cruiseday_form=cruiseday_form,
				participant_form=participant_form
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
			
		return self.render_to_response(
			self.get_context_data(
				form=form,
			    cruiseday_form=cruiseday_form,
				participant_form=participant_form
			)
		)
	
	def post(self, request, *args, **kwargs):
		# uncallable, unsupported and useless, but just in case anybody wants to send a post request
		return self.form_invalid(form, cruiseday_form, participant_form)
			
	def form_valid(self, form, cruiseday_form, participant_form):
		# uncallable, unsupported and useless, but just in case anybody wants to send a post request
		return HttpResponseRedirect(self.get_success_url())
		
	def form_invalid(self, form, cruiseday_form, participant_form):
		# uncallable, unsupported and useless, but just in case anybody wants to send a post request
		"""Throw form back at user."""
		return self.render_to_response(
			self.get_context_data(
				form=form,
			    cruiseday_form=cruiseday_form,
				participant_form=participant_form
			)
		)

class CruiseDeleteView(DeleteView):
	model = Cruise
	template_name = 'reserver/cruise_delete_form.html'
	success_url = reverse_lazy('user-page')
	
def index_view(request):
	return render(request, 'reserver/index.html')

def submit_cruise(request, pk):
	cruise = get_object_or_404(Cruise, pk=pk)
	if request.user is cruise.leader or request.user.is_superuser:
		if not cruise.is_submittable() and not request.user.is_superuser:
			messages.add_message(request, messages.ERROR, 'Cruise could not be submitted: ' + str(cruise.get_missing_information()))
		else:
			cruise.is_submitted = True
			cruise.save()
			cruise.submit_date = datetime.datetime.now()
	else:
		raise PermissionDenied
	return redirect(request.META['HTTP_REFERER'])
	
def unsubmit_cruise(request, pk):
	cruise = get_object_or_404(Cruise, pk=pk)
	if request.user is cruise.leader or request.user.is_superuser:
		cruise.is_submitted = False
		cruise.save()
	else:
		raise PermissionDenied
	return redirect(request.META['HTTP_REFERER'])

# admin-only
	
def approve_cruise(request, pk):
	cruise = get_object_or_404(Cruise, pk=pk)
	if request.user.is_superuser:
		cruise.is_approved = True
		cruise.save()
	else:
		raise PermissionDenied
	return redirect(request.META['HTTP_REFERER'])
	
def unapprove_cruise(request, pk):
	cruise = get_object_or_404(Cruise, pk=pk)
	if request.user.is_superuser:
		cruise.is_approved = False
		cruise.save()
	else:
		raise PermissionDenied
	return redirect(request.META['HTTP_REFERER'])
	
def approve_cruise_information(request, pk):
	cruise = get_object_or_404(Cruise, pk=pk)
	if request.user.is_superuser:
		cruise.information_approved = True
		cruise.save()
	else:
		raise PermissionDenied
	return redirect(request.META['HTTP_REFERER'])
	
def unapprove_cruise_information(request, pk):
	cruise = get_object_or_404(Cruise, pk=pk)
	if request.user.is_superuser:
		cruise.information_approved = False
		cruise.save()
	else:
		raise PermissionDenied
	return redirect(request.META['HTTP_REFERER'])
	
def get_cruise_pdf(request, pk):
	return "Not implemented"
	
class UserView(UpdateView):
	template_name = 'reserver/user.html'
	model = User
	form_class = UserForm
	slug_field = "username"
	success_url = reverse_lazy('user-page')
		
	def get_context_data(self, **kwargs):
		context = super(UserView, self).get_context_data(**kwargs)
		now = datetime.datetime.now()
		
		# add submitted cruises to context
		cruises = list(Cruise.objects.filter(leader=self.request.user, is_submitted=True))
		cruise_start = []
		for cruise in cruises:
			try:
				cruise_start.append(CruiseDay.objects.filter(cruise=cruise.pk).first().event.start_time)
			except AttributeError:
				cruise_start.append('No cruise days')
		submitted_cruises = [{'item1': t[0], 'item2': t[1]} for t in zip(cruises, cruise_start)]
		context['my_submitted_cruises'] = submitted_cruises
		
		# add unsubmitted cruises to context
		cruises = list(Cruise.objects.filter(leader=self.request.user, is_submitted=False))
		cruise_start = []
		for cruise in cruises:
			try:
				cruise_start.append(CruiseDay.objects.filter(cruise=cruise.pk).first().event.start_time)
			except AttributeError:
				cruise_start.append('No cruise days')
		unsubmitted_cruises = [{'item1': t[0], 'item2': t[1]} for t in zip(cruises, cruise_start)]
		context['my_unsubmitted_cruises'] = unsubmitted_cruises
		
#		my_submitted_cruises = list(set(list(Cruise.objects.filter(is_submitted=True, information_approved=False, cruiseday__event__end_time__gte=now))))
#		cruises_need_attention = list(set(list(Cruise.objects.filter(is_submitted=True, information_approved=False, cruiseday__event__end_time__gte=now))))
#		cruise_drafts = list(set(list(Cruise.objects.filter(is_submitted=False, information_approved=False, cruiseday__event__end_time__gte=now))))
#		if(len(cruises_need_attention) > 1):
#			messages.add_message(request, messages.WARNING, 'Warning: %s upcoming cruises are missing information.' % str(len(cruises_need_attention)))
#		elif(len(cruises_need_attention) == 1):
#			messages.add_message(request, messages.WARNING, 'Warning: %s upcoming cruise is missing information.' % str(len(cruises_need_attention)))
		return context
	
class CurrentUserView(UserView):
	def get_object(self):
		return self.request.user
	
def admin_view(request):
	cruises_need_attention = get_cruises_need_attention()
	upcoming_cruises = get_upcoming_cruises()
	unapproved_cruises = get_unapproved_cruises()
	users_not_approved = get_users_not_approved()
	cruises_badge = len(cruises_need_attention) + len(unapproved_cruises)
	users_badge = len(users_not_approved)
	if(len(cruises_need_attention) > 1):
		messages.add_message(request, messages.WARNING, 'Warning: %s upcoming cruises are missing information.' % str(len(cruises_need_attention)))
	elif(len(cruises_need_attention) == 1):
		messages.add_message(request, messages.WARNING, 'Warning: %s upcoming cruise is missing information.' % str(len(cruises_need_attention)))
	if(len(users_not_approved) > 1):
		messages.add_message(request, messages.INFO, 'Info: %s users need attention.' % str(len(users_not_approved)))
	elif(len(users_not_approved) == 1):
		messages.add_message(request, messages.INFO, 'Info: %s user needs attention.' % str(len(users_not_approved)))
	if(len(unapproved_cruises) > 1):
		messages.add_message(request, messages.INFO, 'Info: %s cruises are avaiting approval.' % str(len(unapproved_cruises)))
	elif(len(unapproved_cruises) == 1):
		messages.add_message(request, messages.INFO, 'Info: %s cruise is avaiting approval.' % str(len(unapproved_cruises)))
	return render(request, 'reserver/admin.html', {'cruises_badge':cruises_badge, 'users_badge':users_badge, 'unapproved_cruises':unapproved_cruises, 'upcoming_cruises':upcoming_cruises, 'cruises_need_attention':cruises_need_attention, 'users_not_verified':users_not_approved})

def admin_cruise_view(request):
	cruises = list(Cruise.objects.filter(is_approved=True))
	cruises_need_attention = get_cruises_need_attention()
	users_not_approved = get_users_not_approved()
	cruises_badge = len(get_cruises_need_attention()) + len(get_unapproved_cruises())
	users_badge = len(users_not_approved)
	if(len(cruises_need_attention) > 1):
		messages.add_message(request, messages.WARNING, 'Warning: %s upcoming cruises are missing information.' % str(len(cruises_need_attention)))
	elif(len(cruises_need_attention) == 1):
		messages.add_message(request, messages.WARNING, 'Warning: %s upcoming cruise is missing information.' % str(len(cruises_need_attention)))
	if(len(get_unapproved_cruises()) > 1):
		messages.add_message(request, messages.INFO, 'Info: %s cruises are avaiting approval.' % str(len(get_unapproved_cruises())))
	elif(len(get_unapproved_cruises()) == 1):
		messages.add_message(request, messages.INFO, 'Info: %s cruise is avaiting approval.' % str(len(get_unapproved_cruises())))
	return render(request, 'reserver/admin_cruises.html', {'cruises_badge':cruises_badge, 'users_badge':users_badge, 'cruises':cruises})
	
def admin_user_view(request):
	users = list(UserData.objects.exclude(role="not approved").order_by('-role', 'user__last_name', 'user__first_name'))
	users_not_approved = get_users_not_approved()
	cruises_badge = len(get_cruises_need_attention()) + len(get_unapproved_cruises())
	users_badge = len(users_not_approved)
	if(len(users_not_approved) > 1):
		messages.add_message(request, messages.INFO, 'Info: %s users need attention.' % str(len(users_not_approved)))
	elif(len(users_not_approved) == 1):
		messages.add_message(request, messages.INFO, 'Info: %s user needs attention.' % str(len(users_not_approved)))
	return render(request, 'reserver/admin_users.html', {'cruises_badge':cruises_badge, 'users_badge':users_badge, 'users':users})
	
def admin_event_view(request):
	events = Event.objects.all()
	cruises_badge = len(get_cruises_need_attention()) + len(get_unapproved_cruises())
	users_badge = len(get_users_not_approved())
	return render(request, 'reserver/admin_events.html', {'cruises_badge':cruises_badge, 'users_badge':users_badge, 'events':events})
	
def admin_season_view(request):
	seasons = Season.objects.all().order_by('-season_event__start_time')
	cruises_badge = len(get_cruises_need_attention()) + len(get_unapproved_cruises())
	users_badge = len(get_users_not_approved())
	return render(request, 'reserver/admin_seasons.html', {'cruises_badge':cruises_badge, 'users_badge':users_badge, 'seasons':seasons})
	
def food_view(request, pk):
	cruises_badge = len(get_cruises_need_attention()) + len(get_unapproved_cruises())
	users_badge = len(get_users_not_approved())
	cruise = Cruise.objects.get(pk=pk)
	days = list(CruiseDay.objects.filter(cruise=cruise.pk))
	return render(request, 'reserver/food.html', {'cruises_badge':cruises_badge, 'users_badge':users_badge, 'cruise':cruise, 'days':days})
	
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

#def signup_view(request):
#	if request.method == 'POST':
#		form = UserRegistrationForm(request.POST)
#		if form.is_valid():
#			form.save()
#			username = form.cleaned_data.get('username')
#			raw_password = form.cleaned_data.get('password1')
#			user = authenticate(username=username, password=raw_password)
#			login(request, user)
#			return redirect('home')
#	else:
#		form = UserRegistrationForm()
#	return render(request, 'reserver/authform.html', {'form': form})
	
def calendar_event_source(request):
	events = list(Event.objects.filter(start_time__isnull=False).distinct())
	calendar_events = {"success": 1, "result": []}
	for event in events:
		if event.start_time is not None and event.end_time is not None:
			calendar_event = {
				"id": event.pk,
				"title": "Event",
				"url": "test",
				"class": "event-important",
				"start": event.start_time.timestamp()*1000, # Milliseconds
				"end": event.end_time.timestamp()*1000 # Milliseconds
			}
			if request.user.is_authenticated:
				if event.name is not "":
					calendar_event["title"] = event.name
		
			calendar_events["result"].append(calendar_event)
	return JsonResponse(json.dumps(calendar_events, ensure_ascii=True), safe=False)