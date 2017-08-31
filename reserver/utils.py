import urllib.parse
from datetime import timedelta

def init():
	check_for_and_fix_users_without_userdata()
	check_default_models()
	from reserver import jobs
	from reserver import utils
	utils.init()
	jobs.main()

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
	
default_email_templates = [
	['Cruise approved', 'Cruise administration', 'A cruise you are administrating has been approved', None, None, True, False],
	['Cruise information approved', 'Cruise administration', 'The information of a cruise you are administrating has been approved', None, None, True, False],
	['Cruise information unapproved', 'Cruise administration', 'A cruise you are administrating has had its information unapproved with the following message from an admin.', None, None, True, False],
	['Cruise rejected', 'Cruise administration', 'A cruise you are administrating has been rejected with the following message from an admin.', None, None, True, False],
	['Cruise unapproved', 'Cruise administration', 'A cruise you are administrating has been unapproved with the following message from an admin.', None, None, True, False],
	['16 days missing info', 'Cruise deadlines', 'A cruise you are administrating is in 16 days and is missing important information. Leaving these fields blank will result in the default values being chosen, which may be different from what you want.', timedelta(days=16), None, True, False],
	['Last cancellation chance', 'Cruise deadlines', 'Today is the last day you can cancel your cruise and avoid being billed in full.', timedelta(days=22), None, True, False],
	['1 week until departure', 'Cruise departure', 'A cruise you are participating in is departing in one week.', timedelta(days=7), None, True, False],
	['2 weeks until departure', 'Cruise departure', 'A cruise you are participating in is departing in two weeks.', timedelta(days=14), None, True, False],
	['Departure tomorrow', 'Cruise departure', 'A cruise you are participating in is departing tomorrow.', timedelta(days=1), None, True, False],
	['External season opening', 'Season', 'A new season has just opened up.', None, None, True, False],
	['Internal season opening', 'Season', 'A new season has just opened up.', None, None, True, False]
]
	
def check_default_models():
	""" Prevents system from exploding if anybody deletes or renames the default models. """
	from django.db import models
	from django.core.exceptions import ObjectDoesNotExist
	from reserver.models import EventCategory
	# Check event categories
	
	# check int. season opening
	try:
		internal_season_opening = EventCategory.objects.get(name="Internal season opening")
	except EventCategory.DoesNotExist:
		internal_season_opening = EventCategory(name="Internal season opening", icon="calendar-check-o", colour="blue")
		internal_season_opening.save()
	
	# check ext. season opening
	try:
		external_season_opening = EventCategory.objects.get(name="External season opening")
	except EventCategory.DoesNotExist:
		external_season_opening = EventCategory(name="External season opening", icon="calendar-plus-o", colour="blue")
		external_season_opening.save()
		
	# check season
	try:
		season = EventCategory.objects.get(name="Season")
	except EventCategory.DoesNotExist:
		season = EventCategory(name="Season", icon="calendar", colour="green")
		season.save()
		
	# check cruise day
	try:
		cruise_day = EventCategory.objects.get(name="Cruise day")
	except EventCategory.DoesNotExist:
		cruise_day = EventCategory(name="Cruise day", icon="ship", colour="teal")
		cruise_day.save()
		
	# check other
	try:
		other = EventCategory.objects.get(name="Other")
	except EventCategory.DoesNotExist:
		other = EventCategory(name="Other", colour="orange")
		other.save()
	
	# Check email templates
	from reserver.models import EmailTemplate
	for df in default_email_templates:
		try:
			template = EmailTemplate.objects.get(title=df[0])
		except EmailTemplate.DoesNotExist:
			template = EmailTemplate(title=df[0], group=df[1], message=df[2], time_before=df[3], date=df[4], is_active=df[5], is_muteable=df[6])
			template.save()