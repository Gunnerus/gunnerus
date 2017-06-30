from django.shortcuts import get_list_or_404, get_object_or_404, render, redirect
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.views.generic import ListView
from django.contrib.auth.decorators import login_required

from reserver.models import Cruise, UserData, TimeInterval, Event
from reserver.forms import CruiseForm
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm

from django.http import HttpResponse, JsonResponse
from django.template import loader
import datetime
import json

class CruiseList(ListView):
	model = Cruise
	template_name = 'reserver/cruise_list.html'

class CruiseCreateForm(CreateView):
	form_class = CruiseForm
	template_name = 'reserver/cruise_form.html'
	success_url = 'cruise-list'
	
	def form_valid(self, form):
		#form.instance.cruise_owner = self.request.user
		return super(CruiseCreateForm, self).form_valid(form)

class CruiseEditForm(UpdateView):
	model = Cruise
	fields = ('cruise_name',)
	template_name = 'reserver/cruise_form.html'

class CruiseDeleteForm(DeleteView):
	form = CruiseForm()
	template_name = 'reserver/cruise_form.html'
	success_url = reverse_lazy('cruise-list')
	
def index_view(request):
	return render(request, 'reserver/index.html')

def admin_view(request):
	cruises = list(Cruise.objects.all())
	users_not_verified = list(UserData.objects.filter(role='not_approved'))
	return render(request, 'reserver/admin.html', {'cruises':cruises})

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
	times = list(TimeInterval.objects.filter(event__isnull=False).distinct())
	calendar_events = {"success": 1, "result": []}
	for time in times:
		calendar_event = {
			"id": time.pk,
			"title": "Event",
			"url": "test",
			"class": "event-important",
			"start": time.start_time.timestamp()*1000, # Milliseconds
			"end": time.end_time.timestamp()*1000 # Milliseconds
		}
		if request.user.is_authenticated:
			if time.event.name is not "":
				calendar_event["title"] = time.event.name
		
		calendar_events["result"].append(calendar_event)
	return JsonResponse(json.dumps(calendar_events, ensure_ascii=True), safe=False)