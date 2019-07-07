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
	file_backend = get_connection('django.core.mail.backends.filebased.EmailBackend')
	smtp_backend = get_connection(settings.EMAIL_BACKEND)

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
		fail_silently=False,
		connection=file_backend,
		html_message=template.render(context)
	)

	try:
		send_mail(
			subject,
			message,
			settings.DEFAULT_FROM_EMAIL,
			[user.email],
			fail_silently=False,
			connection=smtp_backend,
			html_message=template.render(context)
		)
	except SMTPException as e:
		print('There was an error sending an email: ', e)

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

# Fetch-functions

def remove_dups_keep_order(lst):
	without_dups = []
	for item in lst:
		if (item not in without_dups):
			without_dups.append(item)
	return without_dups

def get_cruises_need_attention():
	from reserver.models import Cruise
	return remove_dups_keep_order(list(Cruise.objects.filter(is_submitted=True, is_approved=True, information_approved=False, cruise_end__gte=timezone.now())))

def get_upcoming_cruises():
	from reserver.models import Cruise
	return remove_dups_keep_order(list(Cruise.objects.filter(is_submitted=True, is_approved=True, information_approved=True, cruise_end__gte=timezone.now())))

def get_unapproved_cruises():
	from reserver.models import Cruise
	return remove_dups_keep_order(Cruise.objects.filter(is_submitted=True, is_approved=False, cruise_end__gte=timezone.now()).order_by('submit_date'))

def get_users_not_approved():
	from reserver.models import UserData
	check_for_and_fix_users_without_userdata()
	return list(UserData.objects.filter(role="", email_confirmed=True, user__is_active=True))

def get_organizationless_users():
	from reserver.models import UserData
	check_for_and_fix_users_without_userdata()
	return list(UserData.objects.filter(organization__isnull=True))

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
	safe_start_time = urllib.parse.quote(str(start_time.strftime("%Y-%m-%d %H:%M:%S")))
	safe_end_time = urllib.parse.quote(str(end_time.strftime("%Y-%m-%d %H:%M:%S")))
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
	['Cruise dates approved', 'Cruise administration', '{% if cruise_name %}The cruise dates for your cruise {{ cruise_name }} has been approved.{% else %}The cruise dates for a cruise you are administrating has been approved.{% endif %} You may still update and alter the cruise information until three weeks before the cruise starts.{% if extra_message and extra_message.strip %}<br><br><b>Administration message</b><br><span style="white-space:pre;">{{ extra_message }}</span>{% endif %}', None, None, True, False],
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
	['Confirm email address', 'User administration', "Hi, {{ user.username }}! Please click on this link to verify your email address: <a href='https://{{ domain }}{% url 'activate' uidb64=uid token=token %}'>Activate Now</a>", None, None, True, False],
	['Account approved', 'User administration', "Hi, {{ user.username }}! Your account has been approved, and you may now submit your cruises.", None, None, True, False],
	['Reset password', 'User administration', 'Somebody - hopefully you - has requested a password reset for the user associated with this address. Please click the link below to enter a new password. No further action is required if you did not submit this request; your password has not been changed.', None, None, True, False],
	['New user', 'Admin notices', 'A new user, {{ user.username }}, has registered and is awaiting approval.', None, None, True, False],
	['New cruise', 'Admin notices', 'The cruise, {{ cruise }}, has just been submitted.', None, None, True, False],
	['Approved cruise updated', 'Admin notices', 'The information of the cruise, {{ cruise }}, has just been updated and is awaiting approval.', None, None, True, False],
	['Info update deadline exceeded', 'Admin deadline notice', 'The cruise, {{ cruise }}, has exceeded the three week deadline for filling in missing information.', timedelta(days=21), None, True, False],
	['Cruise cancelled', 'Admin notices', 'The approved cruise, {{ cruise }}, has just been cancelled.', None, None, True, False],
	['Invoice rejected', 'Admin notices', 'The invoice "{{ invoice }}" has been rejected.{% if extra_message and extra_message.strip %}<br><br><b>Invoicer message</b><br><span style="white-space:pre;">{{ extra_message }}</span>{% endif %}', None, None, True, False],
	['New invoice ready', 'Admin notices', 'The invoice "{{ invoice }}" has been marked as ready for sending by an administrator.', None, None, True, False]
]

default_event_categories = [
	['Internal season opening', 'calendar-check-o', 'blue', ''],
	['External season opening', 'calendar-plus-o', 'blue', ''],
	['Season', 'calendar', 'green', ''],
	['Cruise day', 'ship', '#1e90ff', ''],
	['Off day', 'calendar-minus-o', 'teal', ''],
	['Red day', 'calendar-times-o', 'red', ''],
	['Scheduled downtime', 'anchor', 'orange', ''],
	['Other', 'clock-o', 'brown', '']
]

def check_default_models():
	""" Prevents system from exploding if anybody deletes or renames the default models. """
	from django.db import models
	from django.core.exceptions import ObjectDoesNotExist
	from reserver.models import EventCategory, Organization, EmailTemplate

	# Check default organization
	try:
		gunnerus_org = Organization.objects.get(name="R/V Gunnerus")
	except Organization.DoesNotExist:
		gunnerus_org = Organization(name="R/V Gunnerus", is_NTNU=True)
		gunnerus_org.save()

	# Check event categories
	for ec in default_event_categories:
		try:
			event_category = EventCategory.objects.get(name=ec[0])
			if not event_category.is_default:
				event_category.is_default = True
				event_category.save()
		except EventCategory.DoesNotExist:
			event_category = EventCategory(name=ec[0], icon=[1], colour=[2], is_default=True)
			event_category.save()

	# Check email templates
	for df in default_email_templates:
		try:
			template = EmailTemplate.objects.get(title=df[0])
			if not template.is_default:
				template.is_default = True
				template.save()
		except EmailTemplate.DoesNotExist:
			template = EmailTemplate(title=df[0], group=df[1], message=df[2], time_before=df[3], date=df[4], is_active=df[5], is_muteable=df[6], is_default=True)
			template.save()

#Methods for automatically creating and deleting notifications related to cruises and seasons when they are created

cruise_deadline_email_templates = {
	'16 days missing info',
	'Last cancellation date',
}

cruise_administration_email_templates = {
	'Cruise dates approved',
	'Cruise information approved',
	'Cruise rejected',
	'Cruise unapproved',
	'Cruise information unapproved',
}

cruise_departure_email_templates = {
	'1 week until departure',
	'2 weeks until departure',
	'Departure tomorrow',
}

season_email_templates = {
	'Internal season opening',
	'External season opening'
}

#To be run when a cruise is submitted, and the cruise and/or its information is approved. Takes cruise and template group as arguments to decide which cruise to make which notifications for
def create_cruise_notifications(cruise, template_group):
	templates = list(EmailTemplate.objects.filter(group=template_group))
	cruise_day_event = CruiseDay.objects.filter(cruise=cruise).order_by('event__start_time').first().event
	notifs = []
	delete_cruise_notifications(cruise, template_group)
	for template in templates:
		notif = EmailNotification()
		notif.event = cruise_day_event
		notif.template = template
		notif.save()
		notifs.append(notif)
	jobs.create_jobs(jobs.scheduler, notifs)
	jobs.scheduler.print_jobs()

#To be run when a cruise is approved
def create_cruise_administration_notification(cruise, template, **kwargs):
	cruise_day_event = CruiseDay.objects.filter(cruise=cruise).order_by('event__start_time').first().event
	notif = EmailNotification()
	if kwargs.get("message"):
		notif.extra_message = kwargs.get("message")
	else:
		notif.extra_message = ""
	notif.event = cruise_day_event
	notif.template = EmailTemplate.objects.get(title=template)
	notif.save()
	jobs.create_jobs(jobs.scheduler, [notif])

#To be run when a cruise's information is approved, and the cruise goes from being unapproved to approved
def create_cruise_deadline_and_departure_notifications(cruise):
	create_cruise_notifications(cruise, 'Cruise deadlines')
	create_cruise_notifications(cruise, 'Cruise departure')
	create_cruise_notifications(cruise, 'Admin deadline notice') #Does not match existing template group, so does nothing

#To be run when a cruise or its information is unapproved
def delete_cruise_notifications(cruise, template_group): #See models.py for Email_Template groups
	cruise_event = CruiseDay.objects.filter(cruise=cruise).order_by('event__start_time').first().event
	all_notifications = EmailNotification.objects.filter(event=cruise_event)
	deadline_notifications = all_notifications.filter(template__group=template_group)
	for notif in deadline_notifications:
		notif.delete()
	jobs.restart_scheduler()

#To be run when a cruise is unapproved
def delete_cruise_deadline_notifications(cruise):
	delete_cruise_notifications(cruise, 'Cruise deadlines')
	delete_cruise_notifications(cruise, 'Admin deadline notice')

#To be run when a cruise's information is unapproved or the cruise is unapproved
def delete_cruise_departure_notifications(cruise,  template_group='Cruise departure'):
	delete_cruise_notifications(cruise, template_group)

#To be run when a cruise is unapproved while its information is approved
def delete_cruise_deadline_and_departure_notifications(cruise):
	delete_cruise_notifications(cruise, 'Cruise deadlines')
	delete_cruise_notifications(cruise, 'Cruise departure')

#To be run when a new season is made
def create_season_notifications(season):
	season_event = season.season_event

	internal_opening_event = season.internal_order_event
	if (internal_opening_event.start_time > timezone.now()):
		internal_notification = EmailNotification()
		internal_notification.event = internal_opening_event
		internal_notification.template = EmailTemplate.objects.get(title="Internal season opening")
		internal_notification.save()
		jobs.create_jobs(jobs.scheduler, [internal_notification])

	external_opening_event = season.external_order_event
	if (external_opening_event.start_time > timezone.now()):
		external_notification = EmailNotification()
		external_notification.event = external_opening_event
		external_notification.template = EmailTemplate.objects.get(title="External season opening")
		external_notification.save()
		jobs.create_jobs(jobs.scheduler, [external_notification])

#To be run when a season is changed/deleted
def delete_season_notifications(season):
	internal_opening_event = season.internal_order_event
	external_opening_event = season.external_order_event
	internal_notifications = EmailNotification.objects.filter(event=internal_opening_event, template__title="Internal season opening")
	external_notifications = EmailNotification.objects.filter(event=external_opening_event, template__title="External season opening")
	for notif in internal_notifications:
		notif.delete()
	for notif in external_notifications:
		notif.delete()
	jobs.restart_scheduler()