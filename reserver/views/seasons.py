from django.shortcuts import get_object_or_404, render
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.utils import timezone

from reserver.utils import create_season_notifications, delete_season_notifications
from reserver.models import Season, Event, EventCategory, Action
from reserver.forms import SeasonForm

def admin_season_view(request):
	seasons = Season.objects.all().order_by('-season_event__start_time')
	return render(request, 'reserver/seasons/admin_seasons.html', {'seasons': seasons})

class CreateSeason(CreateView):
	model = Season
	template_name = 'reserver/seasons/season_edit_form.html'
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
	template_name = 'reserver/seasons/season_edit_form.html'
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
	template_name = 'reserver/seasons/season_delete_form.html'

	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "deleted season"
		action.save()
		return reverse_lazy('seasons')