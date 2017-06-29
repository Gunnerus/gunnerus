from django.shortcuts import render
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.views.generic import ListView

from reserver.models import Cruise
from reserver.forms import CruiseForm

from django.http import HttpResponse
import datetime

class CruiseList(ListView):
	model = Cruise
	template_name = 'reserver/cruise_list.html'
	
class CruiseCreateForm(CreateView):
	form_class = CruiseForm
	template_name = 'reserver/cruise_form.html'
	success_url = 'cruise-list'
	
	def form_valid(self, form):
		x = 1
		#form.instance.cruise_owner = self.request.user
		#return super(CruiseCreateForm, self).form_valid(form)
	
class CruiseEditForm(UpdateView):
	form = CruiseForm()
	template_name = 'reserver/cruise_form.html'
	
class CruiseDeleteForm(DeleteView):
	form = CruiseForm()
	template_name = 'reserver/cruise_form.html'
	success_url = reverse_lazy('cruise-list')
	
def current_datetime(request):
	return render(request, 'reserver/index.html')