import urllib.parse

def init():
	check_for_and_fix_users_without_userdata()
	check_default_models()

def check_for_and_fix_users_without_userdata():
	from django.contrib.auth.models import User
	from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
	from reserver.models import UserData
	for user in User.objects.all():
		# check for users without user data, and add them to unapproved users if they're not admins
		# these may be legacy accounts or accounts created using manage.py's adduser
		try:
			user.userdata
		except ObjectDoesNotExist:
			user_data = UserData()
			if user.is_superuser:
				user_data.role = "admin"
			else:
				user_data.role = ""
			user_data.user = user
			user_data.save()

def render_add_cal_button(event_name, event_description, start_time, end_time):
	safe_name = urllib.parse.quote(str(event_name))
	safe_description = urllib.parse.quote(str(event_description))
	safe_start_time = urllib.parse.quote(str(start_time))
	safe_end_time = urllib.parse.quote(str(end_time))
	cal_button = "<div class='btn-group calendar-dropdown-container'><button type='button' class='dropdown-toggle list-group-item list-group-item-info calendar-export-button' data-toggle='dropdown' aria-haspopup='true' aria-expanded='false'> Add to calendar <span class='caret'></span></button><ul class='dropdown-menu'>"
	cal_button += "<li><a id='fl_ical' href='http://addtocalendar.com/atc/ical?f=m&e[0][date_start]=" + safe_start_time + "&e[0][date_end]=" + safe_end_time + "&e[0][timezone]=Europe%2FOslo&e[0][title]=" + safe_name + "&e[0][description]=" + safe_description + "&e[0][location]=R%2FV%20Gunnerus&e[0][organizer]=R%2FV%20Gunnerus&e[0][organizer_email]=contact%40reserver.471.no&e[0][privacy]=public' target='_blank'>iCalendar</a></li>"
	cal_button += "<li><a id='fl_google' href='http://addtocalendar.com/atc/google?f=m&e[0][date_start]=" + safe_start_time + "&e[0][date_end]=" + safe_end_time + "&e[0][timezone]=Europe%2FOslo&e[0][title]=" + safe_name + "&e[0][description]=" + safe_description + "&e[0][location]=R%2FV%20Gunnerus&e[0][organizer]=R%2FV%20Gunnerus&e[0][organizer_email]=contact%40reserver.471.no&e[0][privacy]=public' target='_blank'>Google Calendar</a></li>"
	cal_button += "<li><a id='fl_outlook' href='http://addtocalendar.com/atc/outlook?f=m&e[0][date_start]=" + safe_start_time + "&e[0][date_end]=" + safe_end_time + "&e[0][timezone]=Europe%2FOslo&e[0][title]=" + safe_name + "&e[0][description]=" + safe_description + "&e[0][location]=R%2FV%20Gunnerus&e[0][organizer]=R%2FV%20Gunnerus&e[0][organizer_email]=contact%40reserver.471.no&e[0][privacy]=public' target='_blank'>Outlook</a></li>"
	cal_button += "<li><a id='fl_outlookonline' href='http://addtocalendar.com/atc/outlookonline?f=m&e[0][date_start]=" + safe_start_time + "&e[0][date_end]=" + safe_end_time + "&e[0][timezone]=Europe%2FOslo&e[0][title]=" + safe_name + "&e[0][description]=" + safe_description + "&e[0][location]=R%2FV%20Gunnerus&e[0][organizer]=R%2FV%20Gunnerus&e[0][organizer_email]=contact%40reserver.471.no&e[0][privacy]=public' target='_blank'>Outlook Online</a></li>"
	cal_button += "<li><a id='fl_yahoo' href='http://addtocalendar.com/atc/yahoo?f=m&e[0][date_start]=" + safe_start_time + "&e[0][date_end]=" + safe_end_time + "&e[0][timezone]=Europe%2FOslo&e[0][title]=" + safe_name + "&e[0][description]=" + safe_description + "&e[0][location]=R%2FV%20Gunnerus&e[0][organizer]=R%2FV%20Gunnerus&e[0][organizer_email]=contact%40reserver.471.no&e[0][privacy]=public' target='_blank'>Yahoo! Calendar</a></li>"
	cal_button += "</ul></div>"
	return cal_button
	
def check_default_models():
	""" Prevents system from exploding if anybody deletes or renames the default models. """
	from django.db import models
	from django.core.exceptions import ObjectDoesNotExist
	from reserver.models import EventCategory
	
	# check int. season opening
	try:
		internal_season_opening = EventCategory.objects.get(name="Internal season opening")
	except EventCategory.DoesNotExist:
		internal_season_opening = EventCategory(name="Internal season opening", icon="calendar-check-o")
		internal_season_opening.save()
	
	# check ext. season opening
	try:
		external_season_opening = EventCategory.objects.get(name="External season opening")
	except EventCategory.DoesNotExist:
		external_season_opening = EventCategory(name="External season opening", icon="calendar-plus-o")
		external_season_opening.save()
		
	# check cruise day
	try:
		cruise_day = EventCategory.objects.get(name="Cruise day")
	except EventCategory.DoesNotExist:
		cruise_day = EventCategory(name="Cruise day", icon="ship")
		cruise_day.save()
		
	# check other
	try:
		other = EventCategory.objects.get(name="Other")
	except EventCategory.DoesNotExist:
		other = EventCategory(name="Other")
		other.save()