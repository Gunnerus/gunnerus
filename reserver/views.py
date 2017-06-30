from django.shortcuts import get_list_or_404, get_object_or_404, render
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.views.generic import ListView

from reserver.models import Cruise, UserData
from reserver.forms import CruiseForm
from django.contrib.auth.models import User

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
	cruises = get_list_or_404(Cruise)
	users_not_verified = get_list_or_404(UserData, role='not_approved')
	return render(request, 'reserver/admin.html', {'cruises':cruises})
def login_view(request):
	return render(request, 'reserver/login.html')
	
def register_view(request):
	return render(request, 'reserver/register.html')
	
def calendar_event_source(request):
	if request.user.is_authenticated:
		calendar_events = {'key': "value"}
	else:
		json_object = {'key': "value"}
	return JsonResponse(json_object)