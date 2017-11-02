import urllib.parse
from datetime import timedelta
import datetime
import pytz
from django.utils import timezone
from django.utils.encoding import force_text
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes
from django.utils import six
from django.core.mail import send_mail, get_connection
from django.contrib import messages
from dateutil.easter import *

class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return (
            six.text_type(user.pk) + six.text_type(timestamp)
        )

account_activation_token = AccountActivationTokenGenerator()

def send_activation_email(request, user):
	from django.conf import settings
	from django.contrib.auth.models import User
	from reserver.models import UserData, EmailTemplate
	user.userdata.email_confirmed = False
	user.userdata.save()
	current_site = get_current_site(request)
	template = EmailTemplate.objects.get(title="Confirm email address")
	subject = template.title
	context = {
		'user': user,
		'domain': current_site.domain,
		'uid': urlsafe_base64_encode(force_bytes(user.pk)),
		'token': account_activation_token.make_token(user),
	}
	message = template.render_message_body(context)
	send_mail(
		subject,
		message,
		settings.DEFAULT_FROM_EMAIL,
		[user.email],
		fail_silently = False,
		html_message = template.render(context)
	)
	messages.add_message(request, messages.INFO, 'Email confirmation link sent to %s.' % str(user.email))
	
def send_user_approval_email(request, user):
	from django.conf import settings
	from django.contrib.auth.models import User
	from reserver.models import EmailTemplate
	current_site = get_current_site(request)
	template = EmailTemplate.objects.get(title="Account approved")
	subject = template.title
	context = {
		'user': user,
	}
	message = template.render_message_body(context)
	send_mail(
		subject,
		message,
		settings.DEFAULT_FROM_EMAIL,
		[user.email],
		fail_silently = False,
		html_message = template.render(context)
	)

def server_starting():
	import sys
	return ('runserver' in sys.argv)

def init():
	check_default_models()
	check_for_and_fix_users_without_userdata()
	check_for_and_fix_cruises_without_organizations()
	check_if_upload_folders_exist()
	remove_orphaned_cruisedays()
	invalidate_cruise_info_caches()
	update_cruise_main_invoices()
	
	current_year = datetime.datetime.now().year
	for year in range(current_year,current_year+5):
		print("Creating red day events for " + str(year))
		create_events_from_list(get_red_days_for_year(year))
	
	from reserver import jobs
	jobs.main()
	
def update_cruise_main_invoices():
	from reserver.models import Cruise, InvoiceInformation
	for cruise in Cruise.objects.all():
		if InvoiceInformation.objects.filter(cruise=cruise).exists():
			cruise.generate_main_invoice()

def invalidate_cruise_info_caches():
	from reserver.models import Cruise
	Cruise.objects.all().update(missing_information_cache_outdated=True)
	
def get_red_days_for_year(year):
	# first: generate list of red day objects with dates and names for the year
	# then iterate over them, and check whether they already exist for that year
	# if they don't already exist, save them as new Event objects of the "Off day" type.
	red_days = []
	red_day = {
		"date": "1980-01-01",
		"name": "Unnamed holiday",
	}
	
	# fixed red days
	red_days.append({"date": str(year)+"-01-01", "name": "New Year's Day"})
	red_days.append({"date": str(year)+"-12-25", "name": "First day of Christmas"})
	red_days.append({"date": str(year)+"-12-26", "name": "Second day of Christmas"})
	red_days.append({"date": str(year)+"-05-01", "name": "International Workers' Day"})
	red_days.append({"date": str(year)+"-05-17", "name": "Constitution Day"})
	
	# non-fixed red days, these are a bit more involved

	easter_day = easter(year)
	red_days.append({"date": easter_day.strftime('%Y-%m-%d'), "name": "First day of Easter"})
	
	second_easter_day = easter(year) + timedelta(days=1)
	red_days.append({"date": second_easter_day.strftime('%Y-%m-%d'), "name": "Second day of Easter"})

	ascension_of_jesus_day = easter_day + timedelta(days=39)
	red_days.append({"date": ascension_of_jesus_day.strftime('%Y-%m-%d'), "name": "Ascension of Jesus Day"})

	first_day_of_pentecost = easter_day + timedelta(days=49)
	red_days.append({"date": first_day_of_pentecost.strftime('%Y-%m-%d'), "name": "First day of Pentecost"})

	second_day_of_pentecost = easter_day + timedelta(days=50)
	red_days.append({"date": second_day_of_pentecost.strftime('%Y-%m-%d'), "name": "Second day of Pentecost"})

	long_friday = easter_day - timedelta(days=2)
	red_days.append({"date": long_friday.strftime('%Y-%m-%d'), "name": "Long Friday"})

	sheer_thursday = easter_day - timedelta(days=3)
	red_days.append({"date": sheer_thursday.strftime('%Y-%m-%d'), "name": "Sheer Thursday"})
	
	return(red_days)
	
def create_events_from_list(days):
	"""Takes a list of objects with 'date' (string, YYYY-MM-DD) and 'name' (string) attributes,
	and creates (0800 to 1600) Event objects from them unless an object
	with that name already exists on that date."""
	from reserver.models import Event, EventCategory
	added_events_count = 0
	off_day_event_category = EventCategory.objects.get(name="Red day")
	for day in days:
		year = day["date"].split("-")[0]
		if not Event.objects.filter(start_time__year=year, name=day["name"]).exists():
			event = Event(
				start_time = timezone.make_aware(datetime.datetime.strptime(day["date"], '%Y-%m-%d').replace(hour=8)),
				end_time = timezone.make_aware(datetime.datetime.strptime(day["date"], '%Y-%m-%d').replace(hour=16)),
				name = day["name"],
				category = off_day_event_category,
				description = "This day is a Norwegian national holiday."
			)
			event.save()
			added_events_count += 1
		elif not Event.objects.filter(start_time__year=year, name=day["name"], category=off_day_event_category).exists():
			event = Event.objects.get(start_time__year=year, name=day["name"])
			event.category = off_day_event_category
			event.save()
			print("Corrected an event category")
			
	print("Added " + str(added_events_count) + " new event(s)")
	
def check_if_upload_folders_exist():
	""" This should be renamed; it's misleading since this also creates
	them if they don't exist. This sounds like a function that returns
	a boolean indicating whether the upload folders exist."""
	import os
	from django.conf import settings
	
	if not os.path.exists(settings.MEDIA_ROOT):
		os.makedirs(settings.MEDIA_ROOT)
		print("Created folder " + settings.MEDIA_ROOT)
		
	if not os.path.exists(settings.EMAIL_FILE_PATH):
		os.makedirs(settings.EMAIL_FILE_PATH)
		print("Created folder " + settings.EMAIL_FILE_PATH)

def check_for_and_fix_users_without_userdata():
	from django.contrib.auth.models import User
	from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
	from reserver.models import UserData, Organization
	for user in User.objects.all():
		# check for users without user data, and add them to unapproved users if they're not admins
		# these may be legacy accounts or accounts created using manage.py's adduser
		try:
			user.userdata
		except ObjectDoesNotExist:
			user_data = UserData()
			if user.is_superuser:
				user_data.role = "admin"
				user_data.organization = Organization.objects.get(name="R/V Gunnerus")
			else:
				user_data.role = ""
			user_data.user = user
			user_data.save()
			
def check_for_and_fix_cruises_without_organizations():
	from django.contrib.auth.models import User
	from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
	from reserver.models import UserData, Cruise
	for cruise in Cruise.objects.all():
		# check for cruises without an organization, and try to update them from leader's org
		# these are old cruises created while we had a bug in saving cruise orgs
		if cruise.organization is None:
			try:
				cruise.organization = cruise.leader.userdata.organization
				cruise.save()
				print("Corrected cruise org for " + str(cruise) + " to " + str(cruise.leader.userdata.organization))
			except ObjectDoesNotExist:
				print("Found cruise missing organization, but leader has no organization")
				
def remove_orphaned_cruisedays():
	from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
	from reserver.models import Event, CruiseDay, EventCategory
	cruise_day_category = EventCategory.objects.get(name="Cruise day")
	for cruise_day_event in Event.objects.filter(category=cruise_day_category):
		if not CruiseDay.objects.filter(event=cruise_day_event).exists():
			print("Deleted orphaned cruise day "+str(cruise_day_event))
			cruise_day_event.delete()

def render_add_cal_button(event_name, event_description, start_time, end_time):
	safe_name = urllib.parse.quote(str(event_name))
	safe_description = urllib.parse.quote(str(event_description))
	safe_start_time = urllib.parse.quote(str(start_time))
	safe_end_time = urllib.parse.quote(str(end_time))
	cal_button = "<div class='btn-group calendar-dropdown-container'><button type='button' class='dropdown-toggle list-group-item list-group-item-info calendar-export-button' data-toggle='dropdown' aria-haspopup='true' aria-expanded='false'> Add to calendar <span class='caret'></span></button><ul class='dropdown-menu'>"
	cal_button += "<li><a id='fl_ical' href='http://addtocalendar.com/atc/ical?f=m&e[0][date_start]=" + safe_start_time + "&e[0][date_end]=" + safe_end_time + "&e[0][timezone]=Europe%2FOslo&e[0][title]=" + safe_name + "&e[0][description]=" + safe_description + "&e[0][location]=R%2FV%20Gunnerus&e[0][organizer]=R%2FV%20Gunnerus&e[0][organizer_email]=contact%40rvgunnerus.no&e[0][privacy]=public' target='_blank'>iCalendar</a></li>"
	cal_button += "<li><a id='fl_google' href='http://addtocalendar.com/atc/google?f=m&e[0][date_start]=" + safe_start_time + "&e[0][date_end]=" + safe_end_time + "&e[0][timezone]=Europe%2FOslo&e[0][title]=" + safe_name + "&e[0][description]=" + safe_description + "&e[0][location]=R%2FV%20Gunnerus&e[0][organizer]=R%2FV%20Gunnerus&e[0][organizer_email]=contact%40rvgunnerus.no&e[0][privacy]=public' target='_blank'>Google Calendar</a></li>"
	cal_button += "<li><a id='fl_outlook' href='http://addtocalendar.com/atc/outlook?f=m&e[0][date_start]=" + safe_start_time + "&e[0][date_end]=" + safe_end_time + "&e[0][timezone]=Europe%2FOslo&e[0][title]=" + safe_name + "&e[0][description]=" + safe_description + "&e[0][location]=R%2FV%20Gunnerus&e[0][organizer]=R%2FV%20Gunnerus&e[0][organizer_email]=contact%40rvgunnerus.no&e[0][privacy]=public' target='_blank'>Outlook</a></li>"
	cal_button += "<li><a id='fl_outlookonline' href='http://addtocalendar.com/atc/outlookonline?f=m&e[0][date_start]=" + safe_start_time + "&e[0][date_end]=" + safe_end_time + "&e[0][timezone]=Europe%2FOslo&e[0][title]=" + safe_name + "&e[0][description]=" + safe_description + "&e[0][location]=R%2FV%20Gunnerus&e[0][organizer]=R%2FV%20Gunnerus&e[0][organizer_email]=contact%40rvgunnerus.no&e[0][privacy]=public' target='_blank'>Outlook Online</a></li>"
	cal_button += "<li><a id='fl_yahoo' href='http://addtocalendar.com/atc/yahoo?f=m&e[0][date_start]=" + safe_start_time + "&e[0][date_end]=" + safe_end_time + "&e[0][timezone]=Europe%2FOslo&e[0][title]=" + safe_name + "&e[0][description]=" + safe_description + "&e[0][location]=R%2FV%20Gunnerus&e[0][organizer]=R%2FV%20Gunnerus&e[0][organizer_email]=contact%40rvgunnerus.no&e[0][privacy]=public' target='_blank'>Yahoo! Calendar</a></li>"
	cal_button += "</ul></div>"
	return cal_button
	
default_email_templates = [
	['Cruise message', 'Cruise administration', '{% if cruise_name %}Your cruise {{ cruise_name }} has received a message from an administrator.{% else %}A cruise your are administrating has received a message from an administrator.{% endif %}{% if extra_message and extra_message.strip %}<br><br><b>Administration message</b><br><span style="white-space:pre;">{{ extra_message }}</span>{% endif %}', None, None, True, False],
	['Cruise approved', 'Cruise administration', '{% if cruise_name %}Your cruise {{ cruise_name }} has been approved.{% else %}A cruise you are administrating has been approved.{% endif %}{% if extra_message and extra_message.strip %}<br><br><b>Administration message</b><br><span style="white-space:pre;">{{ extra_message }}</span>{% endif %}', None, None, True, False],
	['Cruise information approved', 'Cruise administration', '{% if cruise_name %}Your cruise {{ cruise_name }} has had its information approved.{% else %}The information of a cruise you are administrating has been approved.{% endif %}{% if extra_message and extra_message.strip %}<br><br><b>Administration message</b><br><span style="white-space:pre;">{{ extra_message }}</span>{% endif %}', None, None, True, False],
	['Cruise information unapproved', 'Cruise administration', '{% if cruise_name %}Your cruise {{ cruise_name }} has had its information unapproved.{% else %}A cruise you are administrating has had its information unapproved.{% endif %}{% if extra_message and extra_message.strip %}<br><br><b>Administration message</b><br><span style="white-space:pre;">{{ extra_message }}</span>{% endif %}', None, None, True, False],
	['Cruise rejected', 'Cruise administration', '{% if cruise_name %}Your cruise {{ cruise_name }} has been rejected.{% else %}A cruise you are administrating has been rejected.{% endif %}{% if extra_message and extra_message.strip %}<br><br><b>Administration message</b><br><span style="white-space:pre;">{{ extra_message }}</span>{% endif %}', None, None, True, False],
	['Cruise unapproved', 'Cruise administration', '{% if cruise_name %}Your cruise {{ cruise_name }} has been unapproved.{% else %}A cruise you are administrating has been unapproved.{% endif %}{% if extra_message and extra_message.strip %}<br><br><b>Administration message</b><br><span style="white-space:pre;">{{ extra_message }}</span>{% endif %}', None, None, True, False],
	['16 days missing info', 'Cruise deadlines', '{% if cruise_name %}Your cruise {{ cruise_name }} is in 16 days and is missing important information. Leaving these fields blank will result in the default values being chosen, which may be different from what you want.{% else %}A cruise you are administrating is in 16 days and is missing important information. Leaving these fields blank will result in the default values being chosen, which may be different from what you want.{% endif %}', timedelta(days=16), None, True, False],
	['Last cancellation chance', 'Cruise deadlines', '{% if cruise_name %}Today is the last day you can cancel your cruise {{ cruise_name }} and avoid being billed in full.{% else %}Today is the last day you can cancel your cruise and avoid being billed in full.{% endif %}', timedelta(days=22), None, True, False],
	['1 week until departure', 'Cruise departure', '{% if cruise_name %}Your cruise {{ cruise_name }} is departing in one week.{% else %}A cruise you are participating in is departing in one week.{% endif %}', timedelta(days=7), None, True, False],
	['2 weeks until departure', 'Cruise departure', '{% if cruise_name %}Your cruise {{ cruise_name }} is departing in two weeks.{% else %}A cruise you are participating in is departing in two weeks.{% endif %}', timedelta(days=14), None, True, False],
	['Departure tomorrow', 'Cruise departure', '{% if cruise_name %}Your cruise {{ cruise_name }} is departing tomorrow.{% else %}A cruise you are participating in is departing tomorrow.{% endif %}', timedelta(days=1), None, True, False],
	['External season opening', 'Season', 'The season {{ season_name }} has just opened up and you are welcome to book your cruises with R/V Gunnerus.<br><br>Read more on R/V Gunnerus here: <a target="_BLANK" href="www.ntnu.edu/oceans/gunnerus">www.ntnu.edu/oceans/gunnerus</a><br><br>Contact the ship by email: <a href="mailto:tokt@gunnerus.ntnu.edu">tokt@gunnerus.ntnu.edu</a>', None, None, True, False],
	['Internal season opening', 'Season', 'The season {{ season_name }} has just opened up and you are welcome to book your cruises with R/V Gunnerus. As an internal NTNU user you are given a two week head-start on external users of R/V Gunnerus. <br><br>Read more on R/V Gunnerus here: <a target="_BLANK" href="www.ntnu.edu/oceans/gunnerus">www.ntnu.edu/oceans/gunnerus</a><br><br>Contact the ship by email: <a href="mailto:tokt@gunnerus.ntnu.edu">tokt@gunnerus.ntnu.edu</a>', None, None, True, False],
	['Confirm email address', 'User administration', "Hi, {{ user.username }}! Please click on this link to confirm your registration: <a href='http://{{ domain }}{% url 'activate' uidb64=uid token=token %}'>Activate Now</a>", None, None, True, False],
	['Account approved', 'User administration', "Hi, {{ user.username }}! Your account has been approved, and you may now submit your cruises.", None, None, True, False],
	['Reset password', 'User administration', 'Somebody - hopefully you - has requested a password reset for the user associated with this address. Please click the link below to enter a new password. No further action is required if you did not submit this request; your password has not been changed.', None, None, True, False],
	['New user', 'Admin notices', 'A new user, {{ user.username }}, has registered and is awaiting approval.', None, None, True, False],
	['New cruise', 'Admin notices', 'The cruise, {{ cruise }}, has just been submitted.', None, None, True, False],
	['Approved cruise updated', 'Admin notices', 'The information of the cruise, {{ cruise }}, has just been updated and is awaiting approval.', None, None, True, False],
	['Info update deadline exceeded', 'Admin notices', 'The cruise, {{ cruise }}, has exceeded the three week deadline for filling in missing information.', None, None, True, False],
	['Cruise cancelled', 'Admin notices', 'The approved cruise, {{ cruise }}, has just been cancelled.', None, None, True, False]
]
	
def check_default_models():
	""" Prevents system from exploding if anybody deletes or renames the default models. """
	from django.db import models
	from django.core.exceptions import ObjectDoesNotExist
	from reserver.models import EventCategory, Organization
	
	# Check default organization
	try:
		gunnerus_org = Organization.objects.get(name="R/V Gunnerus")
	except Organization.DoesNotExist:
		gunnerus_org = Organization(name="R/V Gunnerus", is_NTNU=True)
		gunnerus_org.save()
	
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
		cruise_day = EventCategory(name="Cruise day", icon="ship", colour="#1e90ff")
		cruise_day.save()
		
	# check off day
	try:
		off_day = EventCategory.objects.get(name="Off day")
	except EventCategory.DoesNotExist:
		off_day = EventCategory(name="Off day", icon="calendar-minus-o", colour="teal")
		off_day.save()
		
	# check red day
	try:
		red_day = EventCategory.objects.get(name="Red day")
	except EventCategory.DoesNotExist:
		red_day = EventCategory(name="Red day", icon="calendar-times-o", colour="red")
		red_day.save()
		
	# check scheduled downtime
	try:
		red_day = EventCategory.objects.get(name="Scheduled downtime")
	except EventCategory.DoesNotExist:
		red_day = EventCategory(name="Scheduled downtime", icon="anchor", colour="orange")
		red_day.save()
		
	# check other
	try:
		other = EventCategory.objects.get(name="Other")
	except EventCategory.DoesNotExist:
		other = EventCategory(name="Other", colour="brown")
		other.save()
	
	# Check email templates
	from reserver.models import EmailTemplate
	for df in default_email_templates:
		try:
			template = EmailTemplate.objects.get(title=df[0])
		except EmailTemplate.DoesNotExist:
			template = EmailTemplate(title=df[0], group=df[1], message=df[2], time_before=df[3], date=df[4], is_active=df[5], is_muteable=df[6])
			template.save()