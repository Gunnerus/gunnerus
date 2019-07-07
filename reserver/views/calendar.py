import re
import datetime
import json

from django.http import JsonResponse
from django.utils import timezone

from reserver.models import Event
from reserver.utils import render_add_cal_button

def calendar_event_source(request):
	try:
		path = request.get_full_path()
		start_timestamp = float(re.search('\Wfrom=(\d*)', path).group(1))/1000
		start_time = datetime.datetime.fromtimestamp(start_timestamp)
		start_time = timezone.make_aware(start_time)
		end_timestamp = float(re.search('\Wto=(\d*)', path).group(1))/1000
		end_time = datetime.datetime.fromtimestamp(end_timestamp)
		end_time = timezone.make_aware(end_time)
		events = list(Event.objects.filter(start_time__isnull=False, start_time__lte=end_time+datetime.timedelta(days=1), end_time__gte=start_time-datetime.timedelta(days=1)).distinct())
	except Exception as e:
		print("Calendar event parsing exploded: " + str(e))
		events = list(Event.objects.filter(start_time__isnull=False).distinct())
	calendar_events = {"success": 1, "result": []}
	for event in events:
		if (event.is_hidden_from_users and not request.user.is_superuser):
			continue
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
					if event.name != "":
						if event.is_cruise_day():
							if event.cruiseday.cruise.is_viewable_by(request.user):
								calendar_event["title"] = event.cruiseday.cruise.get_short_name()
							else:
								calendar_event["title"] = "Cruise"
						else:
							calendar_event["title"] = event.name
							
					if event.description != "":
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
