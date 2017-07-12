from django.shortcuts import get_list_or_404, get_object_or_404, render, redirect
from django.db.models import Q
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.views.generic import ListView
from django.contrib.auth.decorators import login_required
from django.views.generic.detail import SingleObjectMixin
from django.contrib import messages

from reserver.models import Cruise, CruiseDay, Participant, UserData, Event
from reserver.forms import CruiseForm, CruiseDayFormSet, ParticipantFormSet, UserForm
from reserver.test_models import create_test_models
#from reserver.admin import CruiseAdmin
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm

from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.template import loader
import datetime
import json
	
class CruiseList(ListView):
	model = Cruise
	template_name = 'reserver/cruise_list.html'
		
class CruiseCreateView(CreateView):
	template_name = 'reserver/cruise_form.html'
	model = Cruise
	form_class = CruiseForm
	success_url = 'user-page'
	
	def get(self, request, *args, **kwargs):
		"""Handles creation of new blank form/formset objects."""
		self.object = None
		form_class = self.get_form_class()
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
	template_name = 'reserver/cruise_form.html'
	model = Cruise
	form_class = CruiseForm
	success_url = 'user-page'
	
	def get(self, request, *args, **kwargs):
		"""Handles creation of new blank form/formset objects."""
		self.object = Cruise.objects.get(pk=self.kwargs.get('pk'))
		form_class = self.get_form_class()
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
		self.object = Cruise.objects.get(pk=self.kwargs.get('pk'))
		form_class = self.get_form_class()
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

class CruiseDeleteView(DeleteView):
	model = Cruise
	template_name = 'reserver/cruise_form.html'
	success_url = reverse_lazy('cruise-list')
	
def index_view(request):
	return render(request, 'reserver/index.html')
	
class UserView(UpdateView):
	template_name = 'reserver/user.html'
	model = User
	form_class = UserForm
	slug_field = "username"
	success_url = reverse_lazy('user-page')
		
	def get_context_data(self, **kwargs):
		context = super(UserView, self).get_context_data(**kwargs)
		now = datetime.datetime.now()
		cruises = list(Cruise.objects.filter(leader=self.request.user))
		cruise_start = []
		for cruise in cruises:
			try:
				cruise_start.append(CruiseDay.objects.filter(cruise=cruise.pk).first().event.start_time)
			except AttributeError:
				cruise_start.append('No cruise days')
		my_cruises = [{'item1': t[0], 'item2': t[1]} for t in zip(cruises, cruise_start)]
#		my_submitted_cruises = list(set(list(Cruise.objects.filter(is_submitted=True, information_approved=False, cruiseday__event__end_time__gte=now))))
#		cruises_need_attention = list(set(list(Cruise.objects.filter(is_submitted=True, information_approved=False, cruiseday__event__end_time__gte=now))))
#		cruise_drafts = list(set(list(Cruise.objects.filter(is_submitted=False, information_approved=False, cruiseday__event__end_time__gte=now))))
#		if(len(cruises_need_attention) > 1):
#			messages.add_message(request, messages.WARNING, 'Warning: %s upcoming cruises are missing information.' % str(len(cruises_need_attention)))
#		elif(len(cruises_need_attention) == 1):
#			messages.add_message(request, messages.WARNING, 'Warning: %s upcoming cruise is missing information.' % str(len(cruises_need_attention)))
		context['my_submitted_cruises'] = my_cruises
		return context
	
class CurrentUserView(UserView):
	def get_object(self):
		return self.request.user
	
def admin_view(request):
	now = datetime.datetime.now()
	#two_weeks = datetime.timedelta(days=14)
	#three_weeks = datetime.timedelta(days=21)
	#cruises_need_attention = list(set(list(Cruise.objects.filter(is_submitted=True, information_approved=False, cruiseday__event__end_time__gte=now).filter(Q(description='') | Q(cruiseday__breakfast_count=None) | Q(cruiseday__lunch_count=None) | Q(cruiseday__dinner_count=None) | Q(cruiseday__overnight_count=None)))))
	cruises = list(Cruise.objects.all())
	cruise_start = []
	for c in cruises:
		try:
			cruise_start.append(CruiseDay.objects.filter(cruise=c.pk).first().event.start_time)
		except AttributeError:
			cruise_start.append('No cruise days')
	lst = [{'item1': t[0], 'item2': t[1]} for t in zip(cruises, cruise_start)]
	cruises_need_attention = list(set(list(Cruise.objects.filter(is_submitted=True, information_approved=False, cruiseday__event__end_time__gte=now))))
	upcoming_cruises = list(set(list(Cruise.objects.filter(information_approved=True, cruiseday__event__end_time__gte=now))))
	users_not_verified = list(UserData.objects.filter(role='not approved'))
	if(len(cruises_need_attention) > 1):
		messages.add_message(request, messages.WARNING, 'Warning: %s upcoming cruises are missing information.' % str(len(cruises_need_attention)))
	elif(len(cruises_need_attention) == 1):
		messages.add_message(request, messages.WARNING, 'Warning: %s upcoming cruise is missing information.' % str(len(cruises_need_attention)))
	if(len(users_not_verified) > 1):
		messages.add_message(request, messages.INFO, 'Info: %s users need attention.' % str(len(users_not_verified)))
	elif(len(users_not_verified) == 1):
		messages.add_message(request, messages.INFO, 'Info: %s user needs attention.' % str(len(users_not_verified)))
	return render(request, 'reserver/admin.html', {'lst':lst, 'upcoming_cruises':upcoming_cruises, 'cruises_need_attention':cruises_need_attention, 'users_not_verified':users_not_verified})

def login_view(request):
	return render(request, 'reserver/login.html')
	
def signup_view(request):
	if request.method == 'POST':
		form = UserCreationForm(request.POST)
		if form.is_valid():
			form.save()
			username = form.cleaned_data.get('username')
			raw_password = form.cleaned_data.get('password1')
			user = authenticate(username=username, password=raw_password)
			login(request, user)
			return redirect('home')
	else:
		form = UserCreationForm()
	return render(request, 'reserver/authform.html', {'form': form})
	
def register_view(request):
	return render(request, 'reserver/register.html')
	
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