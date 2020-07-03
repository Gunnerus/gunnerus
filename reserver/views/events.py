import datetime

from django.shortcuts import render
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from easy_pdf.rendering import render_to_pdf_response

from reserver.utils import get_days_with_events, event_filter, event_unapproved_cruise_filter
from reserver.models import EventCategory, Event, Action, get_events_in_period
from reserver.forms import EventForm

def admin_event_view(request):
	off_day_event_category = EventCategory.objects.get(name="Red day")
	cruise_day_event_category = EventCategory.objects.get(name="Cruise day")
	all_events = list(Event.objects.all().exclude(category=cruise_day_event_category).exclude(category=off_day_event_category))
	events = []
	for event in all_events:
		if event.is_scheduled_event():
			events.append(event)

	return render(request, 'reserver/events/admin_events.html', {'events':events})

def event_overview(request, **kwargs):
	if request.user.is_superuser:
		has_dates_selected = False
		events = []

		current_day = timezone.now()

		week_start = current_day - datetime.timedelta(days=current_day.weekday())
		week_end = week_start + datetime.timedelta(days=6)

		next_week_start = week_end + datetime.timedelta(days=1)
		next_week_end = next_week_start + datetime.timedelta(days=6)

		start_date_string = week_start.strftime('%Y-%m-%d')
		end_date_string = week_end.strftime('%Y-%m-%d')

		if kwargs.get("start_date") and kwargs.get("end_date"):
			has_dates_selected = True
			start_date_string = kwargs.get("start_date")
			end_date_string = kwargs.get("end_date")

		start_date = timezone.make_aware(datetime.datetime.strptime(start_date_string, '%Y-%m-%d'))
		end_date = timezone.make_aware(datetime.datetime.strptime(end_date_string, '%Y-%m-%d'))

		if start_date > end_date:
			# swap dates
			temp_date = start_date
			start_date = end_date
			end_date = temp_date

			temp_date_string = start_date_string
			start_date_string = end_date_string
			end_date_string = temp_date_string

		events = get_events_in_period(start_date, end_date)
		events = filter(event_filter, events)
		events = filter(event_unapproved_cruise_filter, events)
	else:
		raise PermissionDenied

	return render(request,
		"reserver/events/admin_event_overview.html",
		{
			'days': get_days_with_events(events),
			'has_dates_selected': has_dates_selected,
			'current_week_period_string': week_start.strftime('%Y-%m-%d') + "-to-" + week_end.strftime('%Y-%m-%d'),
			'next_week_period_string': next_week_start.strftime('%Y-%m-%d') + "-to-" + next_week_end.strftime('%Y-%m-%d'),
			'start_date': start_date_string,
			'end_date': end_date_string,
		}
	)

def event_overview_pdf(request, **kwargs):
	if request.user.is_superuser:
		events = []

		current_day = timezone.now()

		week_start = current_day - datetime.timedelta(days=current_day.weekday())
		week_end = week_start + datetime.timedelta(days=6)

		start_date_string = week_start.strftime('%Y-%m-%d')
		end_date_string = week_end.strftime('%Y-%m-%d')

		if kwargs.get("start_date") and kwargs.get("end_date"):
			start_date_string = kwargs.get("start_date")
			end_date_string = kwargs.get("end_date")

		start_date = timezone.make_aware(datetime.datetime.strptime(start_date_string, '%Y-%m-%d'))
		end_date = timezone.make_aware(datetime.datetime.strptime(end_date_string, '%Y-%m-%d'))

		if start_date > end_date:
			# swap dates
			temp_date = start_date
			start_date = end_date
			end_date = temp_date

			temp_date_string = start_date_string
			start_date_string = end_date_string
			end_date_string = temp_date_string

		events = get_events_in_period(start_date, end_date)
		events = filter(event_filter, events)
		events = filter(event_unapproved_cruise_filter, events)
	else:
		raise PermissionDenied

	context = {
		'pagesize': 'A4',
		'title': 'Period summary for ' + start_date.strftime('%d.%m.%Y') + ' to ' + end_date.strftime('%d.%m.%Y'),
		'days': get_days_with_events(events),
		'start_date': start_date,
		'end_date': end_date,
		'http_host': request.META['HTTP_HOST']
	}

	return render_to_pdf_response(
		request,
		'reserver/pdfs/event_overview_pdf.html',
		context,
		download_filename='event_summary_for_' + str(start_date_string) + '_to_' + str(end_date_string) + '.pdf'
	)

class CreateEvent(CreateView):
	model = Event
	template_name = 'reserver/events/event_create_form.html'
	form_class = EventForm

	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "created event"
		action.save()
		return reverse_lazy('events')

class EventEditView(UpdateView):
	model = Event
	template_name = 'reserver/events/event_edit_form.html'
	form_class = EventForm

	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "edited event"
		action.save()
		return reverse_lazy('events')

class EventDeleteView(DeleteView):
	model = Event
	template_name = 'reserver/events/event_delete_form.html'

	def get_success_url(self):
		action = Action(user=self.request.user, timestamp=timezone.now(), target=str(self.object))
		action.action = "deleted event"
		action.save()
		return reverse_lazy('events')
