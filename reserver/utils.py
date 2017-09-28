import urllib.parse
from datetime import timedelta
from django.utils.encoding import force_text
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes
from django.utils import six
from django.core.mail import send_mail, get_connection
from django.contrib import messages

class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return (
            six.text_type(user.pk) + six.text_type(timestamp)
        )

account_activation_token = AccountActivationTokenGenerator()

def send_activation_email(request, user):
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
		'no-reply@reserver.471.no',
		[user.email],
		fail_silently = False,
		html_message = template.render(context)
	)
	messages.add_message(request, messages.INFO, 'Email confirmation link sent to %s.' % str(user.email))
	
def send_user_approval_email(request, user):
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
		'no-reply@reserver.471.no',
		[user.email],
		fail_silently = False,
		html_message = template.render(context)
	)

def server_starting():
	import sys
	return ('runserver' in sys.argv)

def init():
	check_for_and_fix_users_without_userdata()
	check_for_and_fix_cruises_without_organizations()
	check_if_upload_folders_exist()
	check_default_models()
	from reserver import jobs
	jobs.main()
	
def check_if_upload_folders_exist():
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
	['External season opening', 'Season', 'A new season has just opened up.', None, None, True, False],
	['Internal season opening', 'Season', 'A new season has just opened up.', None, None, True, False],
	['Confirm email address', 'Other', "Hi, {{ user.username }}! Please click on this link to confirm your registration: <a href='http://{{ domain }}{% url 'activate' uidb64=uid token=token %}'>Activate Now</a>", None, None, True, False],
	['Account approved', 'Other', "Hi, {{ user.username }}! Your account has been approved, and you may now submit your cruises.", None, None, True, False],
	['Reset password', 'Other', 'Somebody - hopefully you - has requested a password reset for the user associated with this address. Please click the link below to enter a new password. No further action is required if you did not submit this request; your password has not been changed.', None, None, True, False]
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
		cruise_day = EventCategory(name="Cruise day", icon="ship", colour="#1e90ff")
		cruise_day.save()
		
	# check off day
	try:
		season = EventCategory.objects.get(name="Off day")
	except EventCategory.DoesNotExist:
		season = EventCategory(name="Off day", icon="calendar", colour="teal")
		season.save()
		
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