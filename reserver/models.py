import datetime
import time
import base64
import pyqrcode
import random
import re

from decimal import *
from multiselectfield import MultiSelectField

from sanitizer.models import SanitizedCharField

from django import template
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.forms.models import model_to_dict
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models.signals import post_delete
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from reserver.utils import render_add_cal_button

internal_education_regex = re.compile("^ *[a-zA-Z]")
internal_research_regex = re.compile("^ *[78]")

PRICE_DECIMAL_PLACES = 2
MAX_PRICE_DIGITS = 10 + PRICE_DECIMAL_PLACES # stores numbers up to 10^10-1 with 2 digits of accuracy

# TABLE OF CONTENTS
# --------------------------------------------------------
# class EventCategory
# class Event
#	def get_events_in_period
#	def datetime_in_conflict_with_events
#	def datetime_in_conflict_with_future_events
#	def unapproved_datetime_in_conflict_with_events
#	def unapproved_datetime_in_conflict_with_future_events
# class Organization
# class UserData
# class EmailTemplate
# class EmailNotification
# class UserPreferences
# class Season
#	def season_is_open
#	def get_season_containing_time
#	def time_is_in_season
# class Cruise
#	def get_cruise_receipt
#	def get_missing_cruise_information
# class InvoiceInformation
# class Equipment
# class Announcement
#	def get_announcements
#	def render_announcements
# class Document
# class Participant
# class Settings
#	def get_settings_object
# class EventDictionary
#	def get_event_dict_instance
#	def set_date_dict_outdated
# class CruiseDay
# class WebPageText
# class Action
# class ListPrice
# class DebugData
# class Statistics
# Receiver functions

class EventCategory(models.Model):
	name = models.CharField(max_length=200)
	description = models.TextField(max_length=1000, blank=True, default='')
	# contains css-compatible colours stored as a string, such as rgb(0,0,0), #000 or "black"
	colour = models.CharField(max_length=50, default='blue')
	# contains a Font Awesome icon class: http://fontawesome.io/icons/
	icon = models.CharField(max_length=50, blank=True, default='clock-o')
	is_default = models.BooleanField(default=False)

	def __str__(self):
		return self.name

class Event(models.Model):
	name = models.CharField(max_length=200)
	start_time = models.DateTimeField(blank=True, null=True)
	end_time = models.DateTimeField(blank=True, null=True)
	description = models.TextField(max_length=1000, blank=True, default='')
	category = models.ForeignKey(EventCategory, on_delete=models.SET_NULL, null=True, blank=True)
	is_hidden_from_users = models.BooleanField(default=False)
	participants = models.ManyToManyField(User, blank=True)

	class Meta:
		ordering = ['name', 'start_time']

	def __str__(self):
		return self.name

	def is_cruise_day(self):
		try:
			if self.cruiseday != None:
				return True
		except ObjectDoesNotExist:
			return False

	def is_season(self):
		try:
			if self.season != None:
				return True
		except ObjectDoesNotExist:
			return False

	def is_internal_order(self):
		try:
			if self.internal_order != None:
				return True
		except ObjectDoesNotExist:
			return False

	def is_external_order(self):
		try:
			if self.external_order != None:
				return True
		except ObjectDoesNotExist:
			return False

	def get_description(self):
		if self.description != "":
			return self.description
		elif self.is_cruise_day():
			if self.cruiseday.description != "":
				return self.cruiseday.description
			else:
				return "This cruise day has no description."
		else:
			return "This event has no description."

	def is_scheduled_event(self):
		""" should return True for scheduled events such as holidays and planned downtimes. """
		return not (self.is_external_order() or self.is_season() or self.is_internal_order() or self.is_cruise_day())

def get_events_in_period(start_time, end_time):
	events_in_period = Event.objects.filter(start_time__gte=start_time, start_time__lte=end_time)
	events_in_period = events_in_period | Event.objects.filter(end_time__gte=start_time, end_time__lte=end_time)
	return events_in_period.distinct().order_by('start_time')

def datetime_in_conflict_with_events(datetime):
	""" Used with events that already are in the calendar, i.e. they're already in the date dict.
		Basically returns: Is there more than one scheduled thing happening on this date? True/False"""
	date_string = str(datetime.date())
	busy_days_dict = get_event_dict_instance().get_dict()
	if date_string in busy_days_dict:
		return (busy_days_dict[date_string] > 1)
	else:
		return False

def datetime_in_conflict_with_future_events(datetime):
	""" Saves time by not checking past events, which is uninteresting for new cruises.
		User will not be ordering cruises in the past, so we can skip checking for conflicts
		and just say it's invalid due to the cruise being in the past. """
	if datetime < timezone.now():
		return False
	else:
		return datetime_in_conflict_with_events(datetime)

def unapproved_datetime_in_conflict_with_events(datetime):
	""" Used with events that are not yet in the calendar.
		Basically returns: Would adding another event here create a conflict? True/False"""
	date_string = str(datetime.date())
	busy_days_dict = get_event_dict_instance().get_dict()
	if date_string in busy_days_dict:
		return True
	else:
		return False

def unapproved_datetime_in_conflict_with_future_events(datetime):
	""" Saves time by not checking past events, which is uninteresting for new cruises.
		User will not be ordering cruises in the past, so we can skip checking for conflicts
		and just say it's invalid due to the cruise being in the past. """
	if datetime < timezone.now():
		return False
	else:
		return unapproved_datetime_in_conflict_with_events(datetime)

class Organization(models.Model):
	name = models.CharField(max_length=200)
	is_NTNU = models.BooleanField()

	class Meta:
		ordering = ['name']

	def __str__(self):
		return self.name

class UserData(models.Model):
	created = models.DateTimeField(null=True, default=None)
	organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, blank=True, null=True)
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userdata')

	role = models.CharField(max_length=50, blank=True, default='')
	phone_number = models.CharField(max_length=50, blank=True, default='')
	nationality = models.CharField(max_length=50, blank=True, default='')
	is_crew = models.BooleanField(default=False)
	email_confirmed = models.BooleanField(default=True)
	date_of_birth = models.DateField(blank=True, null=True)
	delete_request_active = models.BooleanField(default=False)

	def __str__(self):
		return self.user.get_full_name()

	def save(self, *args, **kwargs):
		if not self.created:
			self.created = timezone.now()
		return super(UserData, self).save(*args, **kwargs)

	def get_announcements(self, *args, **kwargs):
		return get_announcements(userdata=self)

	def is_invoicer(self):
		return (self.role == "invoicer")

	def has_unpaid_invoices(self):
		unpaid_invoices = InvoiceInformation.objects.filter(is_paid=False).filter(cruise__is_submitted=True)
		return unpaid_invoices.filter(cruise__leader=self.user) or unpaid_invoices.filter(cruise__owner=self.user)

	def change_delete_request_status(self):
		if self.delete_request_active:
			self.delete_request_active = False
		else:
			self.delete_request_active = True
		self.save()

class EmailTemplate(models.Model):
	title = models.CharField(max_length=200, blank=True, default='')
	message = models.TextField(blank=True, default='')
	time_before = models.DurationField(blank=True, null=True)
	is_active = models.BooleanField(default=True)
	is_muteable = models.BooleanField(default=False)
	date = models.DateTimeField(blank=True, null=True)
	is_default = models.BooleanField(default=False)

	cruise_deadlines = 'Cruise deadlines'
	cruise_administration = 'Cruise administration'
	cruise_departure = 'Cruise departure'
	season = 'Season'
	admin_notices = 'Admin notices'
	user_administration = 'User administration'
	other = 'Other'
	group_choices = (
		(cruise_deadlines, 'Cruise deadlines'),
		(cruise_administration, 'Cruise administration'),
		(cruise_departure, 'Cruise departure'),
		(season, 'Season'),
		(admin_notices, 'Admin notices'),
		(user_administration, 'User administration'),
		(other, 'Other')
	)
	group = models.CharField(
		max_length=200,
		choices=group_choices,
		blank=True
	)

	class Meta:
		ordering = ['group', 'title']

	def render_message_body(self, context):
		from django.template import Context, Template
		if context:
			message_template = Template(self.message)
			message = message_template.render(Context(context))
		else:
			message = self.message
		return message

	def render(self, context):
		message = self.render_message_body(context)
		ctx = {
			"title": self.title,
			"message": message,
			"group": self.group
		}
		return render_to_string('reserver/emails/base.html', ctx)

	def __str__(self):
		return self.title

class EmailNotification(models.Model):
	event = models.ForeignKey(Event, on_delete=models.CASCADE, blank=True, null=True)
	template = models.ForeignKey(EmailTemplate, on_delete=models.CASCADE, blank=True, null=True)
	recipients = models.ManyToManyField(UserData, blank=True)
	extra_message = models.TextField(blank=True, default="")

	is_special = models.BooleanField(default=False)
	is_active = models.BooleanField(default=False)
	is_sent = models.BooleanField(default=False)

	def __str__(self):
		try:
			if self.event.is_cruise_day():
				return str(self.template.title) + ': ' + str(self.event.cruiseday.cruise)
			else:
				return str(self.template.title) + ': ' + str(self.event.name)
		except AttributeError:
			try:
				return self.template.title
			except AttributeError:
				return 'Event- and templateless notification'

	def get_send_time(self):
		notif = self
		if notif.template is None:
			return None
		template = notif.template
		event = notif.event
		if template.group == 'Cruise administration':
			send_time = timezone.now() - datetime.timedelta(days=365)
		elif event is not None:
			if template.date is None and template.time_before is not None:
				event_start = event.start_time
				send_time = event_start - template.time_before
			elif template.date is not None:
				send_time = template.date
			else:
				send_time = event.start_time
		else:
			if template.date is not None:
				send_time = template.date
			else:
				send_time = timezone.now()
		return send_time

class UserPreferences(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)

	def __str__(self):
		return self.user.get_full_name + ' preferences'

class Season(models.Model):
	name = models.CharField(max_length=100)

	season_event = models.OneToOneField(Event, on_delete=models.SET_NULL, null=True, related_name='season')
	external_order_event = models.OneToOneField(Event, on_delete=models.SET_NULL, null=True, related_name='external_order')
	internal_order_event = models.OneToOneField(Event, on_delete=models.SET_NULL, null=True, related_name='internal_order')

	is_winter = models.BooleanField(default=False)
	# either of these are optional. if winter_start is set, all days up until winter_end
	# OR the end of the season are winter. if winter_end but not winter_start is set, all
	# days from the start of the season until winter_end are winter.
	#winter_start_time = models.DateTimeField(null=True, default=None)
	#winter_end_time = models.DateTimeField(null=True, default=None)

	long_education_price = models.DecimalField(max_digits=MAX_PRICE_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)
	long_research_price = models.DecimalField(max_digits=MAX_PRICE_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)
	long_boa_price = models.DecimalField(max_digits=MAX_PRICE_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)
	long_external_price = models.DecimalField(max_digits=MAX_PRICE_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)

	short_education_price = models.DecimalField(max_digits=MAX_PRICE_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)
	short_research_price = models.DecimalField(max_digits=MAX_PRICE_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)
	short_boa_price = models.DecimalField(max_digits=MAX_PRICE_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)
	short_external_price = models.DecimalField(max_digits=MAX_PRICE_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)

	breakfast_price = models.DecimalField(max_digits=MAX_PRICE_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)
	lunch_price = models.DecimalField(max_digits=MAX_PRICE_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)
	dinner_price = models.DecimalField(max_digits=MAX_PRICE_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)

	def __str__(self):
		return self.name

	def get_start_date_string(self):
		return str(self.season_event.start_time.date())

	def get_end_date_string(self):
		return str(self.season_event.end_time.date())

	def contains_time(self, date):
		return (int(self.season_event.start_time.timestamp()) < int(date.timestamp()) < int(self.season_event.end_time.timestamp()))

	def delete(self, *args, **kwargs):
		from reserver.utils import delete_season_notifications
		delete_season_notifications(self)
		self.season_event.delete()
		self.external_order_event.delete()
		self.internal_order_event.delete()
		return super(self.__class__, self).delete(*args, **kwargs)

	def render_season_summary(self):
		season_html = ""
		return season_html

def season_is_open(user, date):
	for season in Season.objects.filter(season_event__end_time__gt=timezone.now()):
		if (season.season_event.start_time < date < season.season_event.end_time):
			if user.userdata.role == 'internal':
				if season.internal_order_event.start_time < timezone.now():
					return True
				else:
					return False
			elif user.userdata.role == 'external':
				if season.external_order_event.start_time < timezone.now():
					return True
				else:
					return False
			elif user.userdata.role == 'admin':
				return True
	return False

def get_season_containing_time(time):
	for season in Season.objects.all():
		if season.contains_time(time):
			return season

def time_is_in_season(time):
	for season in Season.objects.all():
		if season.contains_time(time):
			return True
	return False

class Cruise(models.Model):
	terms_accepted = models.BooleanField(default=False)
	leader = models.ForeignKey(User, related_name='leader')
	organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True)
	owner = models.ManyToManyField(User, blank=True)

	BILLING_TYPE_CHOICES = (
		('auto', 'Auto'),
		('education', 'Internal education'),
		('research', 'Internal research'),
		('boa', 'BOA'),
		('external', 'External'),
	)

	billing_type = models.CharField(
		max_length=15,
		choices=BILLING_TYPE_CHOICES,
		default='auto',
	)

	description = models.TextField(max_length=2000, blank=True, default='')
	is_submitted = models.BooleanField(default=False)
	is_deleted = models.BooleanField(default=False)
	information_approved = models.BooleanField(default=False)
	is_approved = models.BooleanField(default=False)
	last_edit_date = models.DateTimeField(blank=True, null=True)
	submit_date = models.DateTimeField(blank=True, null=True)
	student_participation_ok = models.BooleanField(default=True)
	no_student_reason = models.TextField(max_length=2000, blank=True, default='')
	management_of_change = models.TextField(max_length=2000, blank=True, default='')
	safety_analysis_required = models.BooleanField(default=False)
	safety_analysis_requirements = models.TextField(max_length=2000, blank=True, default='')
	safety_analysis_documents_uploaded = models.BooleanField(default=False)
	dangerous_substances_required = models.BooleanField(default=False)
	substance_datasheets_uploaded = models.BooleanField(default=False)
	safety_clothing_and_equipment = models.TextField(max_length=2000,  blank=True, default='')
	number_of_participants = models.PositiveSmallIntegerField(blank=True, null=True)
	cruise_start = models.DateTimeField(blank=True, null=True)
	cruise_end = models.DateTimeField(blank=True, null=True)

	missing_information_cache_outdated = models.BooleanField(default=True)
	missing_information_cache = models.TextField(blank=True, default='')

	def is_viewable_by(self, user):
		# if user is in cruise organization or user is superuser, leader or owner return true
		# else nope
		# unapproved users do not get to do anything at all, to prevent users from adding themselves to an org
		user_is_owner = (user in self.owner.all() or user.pk == self.leader.pk)
		user_is_in_cruise_organization = (user.userdata.organization.pk == self.organization.pk)
		user_and_cruise_is_internal = ((user.userdata.role == "internal" or user.userdata.role == "invoicer") and self.organization.is_NTNU)
		if user_is_owner or (not user.userdata.role == "" and (user_is_in_cruise_organization or user_and_cruise_is_internal or user.userdata.role == "admin")):
			return True
		else:
			return False

	def get_owners_minus_leader(self):
		return self.owner.exclude(pk=self.leader.pk)

	def is_editable_by(self, user):
		# if user is leader or owner return true
		# else return false
		return (user in self.owner.all() or user.pk == self.leader.pk) and self.is_editable()

	def is_cancellable_by(self, user):
		return (user in self.owner.all() or user.pk == self.leader.pk) and self.is_cancellable()

	def is_editable(self):
		return not (self.is_approved and self.cruise_start < timezone.now())

	def is_cancellable(self):
		return not (self.is_approved and self.cruise_start < timezone.now())

	def to_dict(self):
		cruise_dict = {}
		cruise_dict["terms_accepted"] = self.terms_accepted
		cruise_dict["leader"] = self.leader
		cruise_dict["organization"] = self.organization
		cruise_dict["owner"] = self.owner
		cruise_dict["description"] = self.description
		cruise_dict["is_submitted"] = self.is_submitted
		cruise_dict["is_deleted"] = self.is_deleted
		cruise_dict["information_approved"] = self.information_approved
		cruise_dict["is_approved"] = self.is_approved
		cruise_dict["last_edit_date"] = self.last_edit_date
		cruise_dict["submit_date"] = self.submit_date
		cruise_dict["student_participation_ok"] = self.student_participation_ok
		cruise_dict["no_student_reason"] = self.no_student_reason
		cruise_dict["management_of_change"] = self.management_of_change
		cruise_dict["safety_clothing_and_equipment"] = self.safety_clothing_and_equipment
		cruise_dict["safety_analysis_requirements"] = self.safety_analysis_requirements
		cruise_dict["safety_analysis_documents_uploaded"] = self.safety_analysis_documents_uploaded
		cruise_dict["number_of_participants"] = self.number_of_participants
		cruise_dict["safety_analysis_required"] = self.safety_analysis_required
		cruise_dict["dangerous_substances_required"] = self.dangerous_substances_required
		cruise_dict["substance_datasheets_uploaded"] = self.substance_datasheets_uploaded
		cruise_dict["cruise_start"] = self.cruise_start
		cruise_dict["cruise_end"] = self.cruise_end
		return cruise_dict

	def get_cal_button(self):
		return render_add_cal_button("Cruise with R/V Gunnerus", self.description, self.cruise_start, self.cruise_end)

	def get_cruise_days(self):
		return CruiseDay.objects.filter(cruise=self.pk)

	def get_cruise_equipment(self):
		return Equipment.objects.filter(cruise=self.pk)

	def get_cruise_documents(self):
		return Document.objects.filter(cruise=self.pk)

	def get_billing_type_string(self):
		billing_type = self.get_billing_type()
		if billing_type == "education":
			return "Internal education"
		elif billing_type == "research":
			return "Internal research"
		elif billing_type == "boa":
			return "BOA"
		elif billing_type == "external":
			return "External"
		return "Unknown billing type (\""+billing_type+"\")"

	def get_billing_type(self):
		if self.billing_type == "auto":
			try:
				if self.organization.is_NTNU:
					invoice = self.get_invoice_info()
					try:
						if len(invoice.project_number) > 1:
							if internal_research_regex.match(invoice.project_number):
								if internal_education_regex.match(invoice.course_code):
									return "education"
								return "research"
							elif internal_education_regex.match(invoice.course_code):
								return "education"
							else:
								return "boa"
					except Exception:
						pass
					return "research"
				else:
					return "external"
			except (ObjectDoesNotExist, AttributeError):
				return "external"
		else:
			return self.billing_type

	def get_contact_emails(self):
		return self.leader.email

	def get_cruise_sum(self):
		return self.get_receipt()["sum"]

	def get_receipt(self):
		cruise_data = {
			"type": "",
			"season": "",
			"short_days": 0,
			"long_days": 0,
			"breakfasts": 0,
			"lunches": 0,
			"dinners": 0
		}

		cruise_data["type"] = self.get_billing_type()

		for cruise_day in self.get_cruise_days():
			if (cruise_data["season"] == ""):
				cruise_data["season"] = cruise_day.season

			if cruise_day.is_long_day:
				cruise_data["long_days"] += 1
			else:
				cruise_data["short_days"] += 1

			try:
			   cruise_data["breakfasts"] += int(cruise_day.breakfast_count)
			except (ValueError, TypeError):
			   pass

			try:
			   cruise_data["lunches"] += int(cruise_day.lunch_count)
			except (ValueError, TypeError):
			   pass

			try:
			   cruise_data["dinners"] += int(cruise_day.dinner_count)
			except (ValueError, TypeError):
			   pass

		return get_cruise_receipt(**cruise_data)

	def get_cruise_description_string(self):
		cruise_string = "This cruise is done on the behalf of "
		if self.organization is not None:
			cruise_string += str(self.organization)
		else:
			cruise_string += "an invalid or deleted organization"
		cruise_string += ", has "
		if self.number_of_participants is not None:
			cruise_string += str(self.number_of_participants) + " participants"
		else:
			cruise_string += "an unknown amount of participants"
		cruise_string += ", and "
		if self.student_participation_ok:
			cruise_string += "accepts students"
		else:
			cruise_string += "does not accept students"
		cruise_string += "."
		extra_information_list = []
		if self.management_of_change != "":
			extra_information_list.append("management of change")
		if self.safety_clothing_and_equipment != "":
			extra_information_list.append("safety clothing and equipment")
		if self.safety_analysis_requirements != "":
			extra_information_list.append("safety analysis and requirements")
		if self.no_student_reason != "":
			extra_information_list.append("not accepting students")
		if len(extra_information_list) > 0:
			random.shuffle(extra_information_list)
			cruise_string += " It also has extra information filled in regarding "
			if len(extra_information_list) > 2:
				for index, item in enumerate(extra_information_list):
					if index == len(extra_information_list)-1:
						cruise_string += item
					elif index == len(extra_information_list)-2:
						cruise_string += item + " and "
					else:
						cruise_string += item + ", "

			elif len(extra_information_list) > 1:
				cruise_string += extra_information_list[0] + " and " + extra_information_list[1]
			else:
				cruise_string += extra_information_list[0]
			cruise_string += "."
		return cruise_string

	def get_missing_information_list(self, **kwargs):
		missing_info_list = []
		missing_information = self.get_missing_information(**kwargs)

		if missing_information["safety_analysis_info_missing"]:
			missing_info_list.append("Safety analysis info is missing.")
		if missing_information["datasheets_missing"]:
			missing_info_list.append("Dangerous substance datasheets are missing.")
		if missing_information["cruise_days_missing"]:
			missing_info_list.append("Cruise has no cruise days.")
		if missing_information["cruise_participants_missing"]:
			missing_info_list.append("Entering the maximum simultaneous number of cruise participants is required.")
		if missing_information["terms_not_accepted"]:
			missing_info_list.append("Terms and conditions not accepted.")
		if missing_information["no_student_reason_missing"]:
			missing_info_list.append("Entering a reason for not accepting students is required.")
		if missing_information["user_unapproved"]:
			missing_info_list.append("Your user account has not been approved yet, so you may not submit this cruise.")
		if missing_information["cruise_day_outside_season"]:
			missing_info_list.append("One or more cruise days are outside a season.")
		if missing_information["cruise_day_overlaps"]:
			missing_info_list.append("One or more cruise days are in conflict with another scheduled event or cruise in the calendar.")
		if missing_information["cruise_day_in_past"]:
			missing_info_list.append("One or more cruise days are in the past.")
		if missing_information["season_not_open_to_user"]:
			missing_info_list.append("One or more cruise days are in seasons not yet open to your account.")
		if missing_information["too_many_participants"]:
			missing_info_list.append("Cruise cannot have more than 20 simultaneous participants.")
		if missing_information["description_missing"]:
			missing_info_list.append("Entering a cruise description is required.")
		if missing_information["cruise_destination_missing"]:
			missing_info_list.append("A destination is required for every cruise day.")
		if missing_information["invoice_info_missing"]:
			missing_info_list.append("Filling in some invoice information is required.")
		if missing_information["invoice_info_missing_external_address"]:
			missing_info_list.append("Your billing address is missing.")
		if missing_information["invoice_info_missing_accounting_place"]:
			missing_info_list.append("Your accounting place is missing.")
		if missing_information["too_many_overnight_stays"]:
			missing_info_list.append("A cruise day has too many or an invalid amount of overnight stays. The maximum is three per night.")

		return missing_info_list

	def get_missing_information_string(self, **kwargs):
		missing_info_string = ""
		missing_information = self.get_missing_information_list(**kwargs)
		for item in missing_information:
			if item:
				missing_info_string += "<br><span>  - " + item + "</span>"
		return missing_info_string

	def get_invoice_info(self):
		invoice = InvoiceInformation.objects.filter(cruise=self.pk, is_cruise_invoice=True)
		try:
			if(invoice[0]):
				return invoice[0]
		except IndexError:
			pass
		return False

	def get_invoices(self):
		return InvoiceInformation.objects.filter(cruise=self.pk)

	def generate_main_invoice(self):
		try:
			invoice = self.get_invoice_info()

			# do not update finalized/sent/paid invoices after the fact
			if not (invoice.is_done()):
				receipt = self.get_receipt()
				invoice_items = ListPrice.objects.filter(invoice=invoice.pk, is_generated=True)

				# update invoice title without saving to avoid recursion
				InvoiceInformation.objects.filter(cruise=self.pk, is_cruise_invoice=True).update(title="Main invoice for cruise " + str(self))

				# remove old items
				invoice_items.delete()

				# generate new invoice items from receipt
				for item in receipt["items"]:
					if Decimal(item["list_cost"]) > 0:
						new_item = ListPrice(invoice=invoice, name=item["name"] + ", " + str(item["count"]), price=Decimal(item["list_cost"]), is_generated=True)
						new_item.save()
		except ObjectDoesNotExist:
			pass

	def get_sum_of_invoices(self):
		sum = Decimal(0)
		has_no_invoices = True
		for invoice in self.get_invoices():
			sum += invoice.get_sum()
			has_no_invoices = False
		if (has_no_invoices):
			sum = Decimal(self.get_cruise_sum())
		return sum

	def overlaps_with_unapproved_cruises(self):
		cruises = Cruise.objects.filter(is_submitted=True, cruise_end__gte=timezone.now()).exclude(pk=self.pk)
		start_timestamp = time.mktime(self.cruise_start.timetuple())
		end_timestamp = time.mktime(self.cruise_end.timetuple())
		for cruise in cruises:
			if (time.mktime(cruise.cruise_start.timetuple()) <= start_timestamp <= time.mktime(cruise.cruise_end.timetuple())) or (time.mktime(cruise.cruise_start.timetuple()) <= end_timestamp <= time.mktime(cruise.cruise_end.timetuple())):
				return True
		return False

	def get_missing_information(self, **kwargs):
		if not self.missing_information_cache_outdated:
			return eval(self.missing_information_cache)
		else:
			missing_information = get_missing_cruise_information(**kwargs, cruise=self)
			Cruise.objects.filter(pk=self.pk).update(missing_information_cache=str(missing_information))
			Cruise.objects.filter(pk=self.pk).update(missing_information_cache_outdated=False)
			return missing_information

	def outdate_missing_information(self):
		Cruise.objects.filter(pk=self.pk).update(missing_information_cache_outdated=True)

	def is_missing_information(self, **kwargs):
		return len(self.get_missing_information_list(**kwargs)) > 0

	def is_submittable(self, **kwargs):
		# will have more than this to check for eventually. kind of redundant right now.
		if kwargs.get("user"):
			return (not self.is_missing_information(**kwargs))
		else:
			return not self.is_missing_information(**kwargs)

	def update_cruise_start_end(self):
		try:
			self.cruise_start = CruiseDay.objects.filter(cruise=self).order_by('event__start_time').first().event.start_time
			self.cruise_end = CruiseDay.objects.filter(cruise=self).order_by('event__start_time').last().event.end_time
			self.save()
		except (IndexError, AttributeError) as error:
			pass

	class Meta:
		ordering = ['cruise_start']

	def get_short_name(self):
		try:
			name = self.leader.get_full_name()
			if name == "":
				name = self.leader.username
		except:
			name = "Temporary Cruise Name"
		return name

	def old_self_str(self):
		cruise_days = CruiseDay.objects.filter(cruise=self.pk)
		cruise_dates = []
		cruise_string = ""
		if cruise_days.count() != 0:
			for cruise_day in cruise_days:
				if cruise_day.event is not None:
					cruise_dates.append(cruise_day.event.start_time)
				else:
					cruise_dates.append(datetime.datetime(1980, 1, 1))
			cruise_string = " - "
			for index, cruise_date in enumerate(cruise_dates):
				if index != 0:
					cruise_string = cruise_string + ", "
				cruise_string = cruise_string + str(cruise_date.date())
		else:
			cruise_string = " - No cruise days"
		try:
			name = self.leader.get_full_name()
			if name == "":
				name = self.leader.username
		except:
			name = "Temporary Cruise Name"
		return name + cruise_string

	def __str__(self):
		weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday' , 'Saturday', 'Sunday']
		cruise_days = CruiseDay.objects.filter(cruise=self.pk)
		cruise_dates = []
		cruise_string = ""
		if cruise_days.count() != 0:
			for cruise_day in cruise_days:
				if cruise_day.event is not None:
					cruise_dates.append(cruise_day.event.start_time)
				else:
					cruise_dates.append(datetime.datetime(1980, 1, 1))
			cruise_string = " - "
			start_date = cruise_dates[0].date()
			start_string = weekdays[start_date.weekday()] + ' ' + str(start_date)
			end_date = cruise_dates[len(cruise_dates)-1].date()
			end_string = weekdays[end_date.weekday()] + ' ' + str(end_date)
			if start_string != end_string:
				cruise_string += start_string + " to " + end_string
			else:
				cruise_string += start_string
		else:
			cruise_string = " - No cruise days"
		try:
			name = self.leader.get_full_name()
			if name == "":
				name = self.leader.username
		except:
			name = "Temporary Cruise Name"
		return name + cruise_string

	def was_edited_recently(self):
		now = timezone.now()
		return now - datetime.timedelta(days=1) <= self.edit_date <= now

	was_edited_recently.admin_order_field = 'edit_date'
	was_edited_recently.boolean = True
	was_edited_recently.short_description = 'Edited recently?'

	def has_food(self):
		cruise_days = CruiseDay.objects.filter(cruise=self.pk)
		for day in cruise_days:
			try:
				if(day.breakfast_count>0):
					return True
			except TypeError:
				pass
			try:
				if(day.lunch_count>0):
					return True
			except TypeError:
				pass
			try:
				if(day.dinner_count>0):
					return True
			except TypeError:
				pass
		return False

	def has_overnight_stays(self):
		cruise_days = CruiseDay.objects.filter(cruise=self.pk)
		for day in cruise_days:
			try:
				if(day.breakfast_count>0):
					return True
			except TypeError:
				pass
			try:
				if(day.overnight_count>0):
					return True
			except TypeError:
				pass
		return False

	def needs_attention(self):
		cruise_days = CruiseDay.objects.filter(cruise=self.pk)
		if(self.description==""):
			return True
		for day in cruise_days:
			if(day.breakfast_count==0 or day.lunch_count==0 or day.dinner_count==0 or day.overnight_count==0):
				return True
		return False

	def invoice_status(self):
		invoice = InvoiceInformation.objects.filter(cruise=self.pk)
		try:
			if(invoice[0].is_sent):
				return True
		except IndexError:
			pass
		return False

def get_cruise_receipt(**kwargs):
	receipt = {"success": 0, "type": "unknown", "items": [], "sum": 0}

	if kwargs.get("season"):
		season = kwargs.get("season")
	else:
		receipt["error"] = "Season not found"
		return receipt

	short_day_cost = max([season.short_education_price, season.short_research_price, season.short_boa_price, season.short_external_price])
	long_day_cost = max([season.long_education_price, season.long_research_price, season.long_boa_price, season.long_external_price])

	if kwargs.get("type"):
		type = kwargs.get("type")
		receipt["type"] = type
		if type == "research":
			short_day_cost = season.short_research_price
			long_day_cost = season.long_research_price
		elif type == "education":
			short_day_cost = season.short_education_price
			long_day_cost = season.long_education_price
		elif type == "boa":
			short_day_cost = season.short_boa_price
			long_day_cost = season.long_boa_price
		elif type == "external":
			short_day_cost = season.short_external_price
			long_day_cost = season.long_external_price

	# calculate cost of short days

	item = {"name": "Short days", "count": 0, "unit_cost": short_day_cost, "list_cost": 0}

	if kwargs.get("short_days"):
		short_days = kwargs.get("short_days")
		item = {"name": item["name"], "count": short_days, "unit_cost": short_day_cost, "list_cost": short_days*short_day_cost}

	receipt["items"].append(item)

	# calculate cost of long days

	item = {"name": "Long days", "count": 0, "unit_cost": long_day_cost, "list_cost": 0}

	if kwargs.get("long_days"):
		long_days = kwargs.get("long_days")
		item = {"name": item["name"], "count": long_days, "unit_cost": long_day_cost, "list_cost": long_days*long_day_cost}

	receipt["items"].append(item)

	# calculate food costs

	item = {"name": "Breakfasts", "count": 0, "unit_cost": season.breakfast_price, "list_cost": 0}

	if kwargs.get("breakfasts"):
		breakfasts = kwargs.get("breakfasts")
		item = {"name": item["name"], "count": breakfasts, "unit_cost": season.breakfast_price, "list_cost": breakfasts*season.breakfast_price}

	receipt["items"].append(item)

	item = {"name": "Lunches", "count": 0, "unit_cost": season.lunch_price, "list_cost": 0}

	if kwargs.get("lunches"):
		lunches = kwargs.get("lunches")
		item = {"name": item["name"], "count": lunches, "unit_cost": season.lunch_price, "list_cost": lunches*season.lunch_price}

	receipt["items"].append(item)

	item = {"name": "Dinners", "count": 0, "unit_cost": season.dinner_price, "list_cost": 0}

	if kwargs.get("dinners"):
		dinners = kwargs.get("dinners")
		item = {"name": item["name"], "count": dinners, "unit_cost": season.dinner_price, "list_cost": dinners*season.dinner_price}

	receipt["items"].append(item)

	for item in receipt["items"]:
		receipt["sum"] += item["list_cost"]
		item["list_cost"] = str(item["list_cost"])
		item["count"] = str(item["count"])
		item["unit_cost"] = str(item["unit_cost"])

	receipt["sum"] = str(receipt["sum"])

	receipt["success"] = 1

	return receipt

def get_missing_cruise_information(**kwargs):
	missing_information = {}

	# keyword args should be set if called on a form object - can't do db queries before objs exist in db
	if kwargs.get("cleaned_data"):
		CruiseDict = kwargs.get("cleaned_data")
		# a cruise that's just been submitted can't be approved by an admin yet.
		CruiseDict["is_approved"] = False
	else:
		instance = kwargs.get("cruise")
		cruise = Cruise.objects.get(pk=instance.pk)
		CruiseDict = cruise.to_dict()
		CruiseDict["leader"] = cruise.leader

	if kwargs.get("cruise_days"):
		temp_cruise_days = kwargs["cruise_days"]
		cruise_days = []
		for cruise_day in temp_cruise_days:
			if cruise_day.get("date"):
				cruise_days.append(cruise_day)

	else:
		temp_cruise_days = kwargs.get("cruise").get_cruise_days()
		cruise_days = []
		for cruise_day in temp_cruise_days:
			try:
				cruise_day_dict = cruise_day.to_dict()
				cruise_day_dict["date"] = cruise_day.event.start_time
				cruise_days.append(cruise_day_dict)
			except:
				pass

	if kwargs.get("cruise_participants"):
		cruise_participants = kwargs["cruise_participants"]
		for cruise_participant in cruise_participants:
			if not cruise_participant.get("name"):
				cruise_participants.remove(cruise_participant)
	else:
		cruise_participants = Participant.objects.filter(cruise=kwargs.get("cruise").pk)

	if kwargs.get("cruise_invoice"):
		cruise_invoice = kwargs["cruise_invoice"]
	else:
		cruise_invoice = []
		try:
			cruise_invoice.append(InvoiceInformation.objects.filter(cruise=kwargs.get("cruise").pk, is_cruise_invoice=True).first().to_dict())
		except:
			pass

	missing_information["invoice_info_missing"] = False
	missing_information["invoice_info_missing_external_address"] = False
	missing_information["invoice_info_missing_accounting_place"] = False

	if len(cruise_invoice) < 1:
		missing_information["invoice_info_missing"] = True
	else:
		if CruiseDict["leader"].userdata.role == "external":
			cruise_invoice = cruise_invoice[0]
			if "billing_address" in cruise_invoice and len(cruise_invoice["billing_address"]) > 0:
				missing_information["invoice_info_missing"] = False
			else:
				missing_information["invoice_info_missing"] = True
				missing_information["invoice_info_missing_external_address"] = True
		else:
			cruise_invoice = cruise_invoice[0]
			if "internal_accounting_place" in cruise_invoice and str(cruise_invoice["internal_accounting_place"]).isdigit():
				missing_information["invoice_info_missing"] = False
			else:
				missing_information["invoice_info_missing"] = True
				missing_information["invoice_info_missing_accounting_place"] = True

	missing_information["cruise_days_missing"] = False
	missing_information["season_not_open_to_user"] = False
	missing_information["cruise_day_outside_season"] = False
	missing_information["cruise_day_overlaps"] = False
	missing_information["cruise_day_in_past"] = False
	missing_information["cruise_destination_missing"] = False
	missing_information["too_many_overnight_stays"] = False

	if len(cruise_days) < 1:
		missing_information["cruise_days_missing"] = True
	else:
		for cruise_day in cruise_days:
			if cruise_day["overnight_count"] is not None and (cruise_day["overnight_count"] > 3 or cruise_day["overnight_count"] < 0):
				missing_information["too_many_overnight_stays"] = True
			if len(cruise_day["destination"]) < 1:
				missing_information["cruise_destination_missing"] = True
			if cruise_day["date"]:
				if cruise_day["date"] < timezone.now():
					if not CruiseDict["is_approved"]:
						missing_information["cruise_day_in_past"] = True
				else:
					if CruiseDict["is_approved"]:
						if datetime_in_conflict_with_future_events(cruise_day["date"]):
							missing_information["cruise_day_overlaps"] = True
					else:
						if unapproved_datetime_in_conflict_with_future_events(cruise_day["date"]):
							missing_information["cruise_day_overlaps"] = True
						if not time_is_in_season(cruise_day["date"]):
							missing_information["cruise_day_outside_season"] = True
						if not season_is_open(CruiseDict["leader"], cruise_day["date"]):
							missing_information["season_not_open_to_user"] = True

	if (CruiseDict["number_of_participants"] is not None):
		if (CruiseDict["number_of_participants"] > 0):
			missing_information["cruise_participants_missing"] = False
			if (CruiseDict["number_of_participants"] > get_settings_object().max_participants):
				missing_information["too_many_participants"] = True
			else:
				missing_information["too_many_participants"] = False
		else:
			missing_information["cruise_participants_missing"] = True
			missing_information["too_many_participants"] = False
	else:
		missing_information["cruise_participants_missing"] = True
		missing_information["too_many_participants"] = False

	if (len(CruiseDict["description"]) > 1):
		missing_information["description_missing"] = False
	else:
		missing_information["description_missing"] = True

	if CruiseDict["safety_analysis_required"] and not (CruiseDict["safety_analysis_documents_uploaded"] or CruiseDict["safety_analysis_requirements"] != ""):
		missing_information["safety_analysis_info_missing"] = True
	else:
		missing_information["safety_analysis_info_missing"] = False

	if CruiseDict["dangerous_substances_required"] and not CruiseDict["substance_datasheets_uploaded"]:
		missing_information["datasheets_missing"] = True
	else:
		missing_information["datasheets_missing"] = False

	if CruiseDict["terms_accepted"]:
		missing_information["terms_not_accepted"] = False
	else:
		missing_information["terms_not_accepted"] = True
	if not CruiseDict["student_participation_ok"] and CruiseDict["no_student_reason"] == "":
		missing_information["no_student_reason_missing"] = True
	else:
		missing_information["no_student_reason_missing"] = False
	try:
		if UserData.objects.get(user=CruiseDict["leader"]).role == "" and not CruiseDict["leader"].is_superuser:
			missing_information["user_unapproved"] = True
		else:
			missing_information["user_unapproved"] = False
	except (ObjectDoesNotExist, AttributeError):
		# user does not have UserData; probably a superuser created using manage.py's createsuperuser.
		if not User.objects.get(pk=CruiseDict["leader"]).is_superuser:
			missing_information["user_unapproved"] = True
		else:
			missing_information["user_unapproved"] = False

	return missing_information

class InvoiceInformation(models.Model):
	cruise = models.ForeignKey(Cruise, on_delete=models.CASCADE, blank=True, null=True)
	event = models.ForeignKey(Event, on_delete=models.CASCADE, blank=True, null=True)
	default_invoice_information_for = models.ForeignKey(Organization, on_delete=models.SET_NULL, blank=True, null=True)

	title = models.CharField(max_length=200, blank=True, default='')
	business_reg_num = models.PositiveIntegerField(blank=True, null=True)
	billing_address = models.CharField(max_length=200, blank=True, default='')
	internal_accounting_place = models.PositiveIntegerField(blank=True, null=True) # k-sted
	external_accounting_place = models.CharField(max_length=200, blank=True, default='')
	project_number = models.CharField(max_length=200, blank=True, default='')
	project_leader = models.CharField(max_length=200, blank=True, default='')
	course_code = models.CharField(max_length=200, blank=True, default='')
	course_lecturer = models.CharField(max_length=200, blank=True, default='')
	reference = models.CharField(max_length=200, blank=True, default='')
	invoice_mark = models.CharField(max_length=200, blank=True, default='')
	contact_name = models.CharField(max_length=200, blank=True, default='')
	contact_email = models.EmailField(blank=True, null=True)
	description = models.TextField(max_length=2000, blank=True, default='')

	# indicates whether the invoice has been marked as finished by an admin
	is_finalized = models.BooleanField(default=False)
	# stores the rejection message - if any - sent by invoicers when an invoice is rejected
	rejection_message = models.TextField(max_length=2000, blank=True, default='')

	# indicates whether the invoice has been marked as sent by an invoice manager
	is_sent = models.BooleanField(default=False)
	send_date = models.DateTimeField(blank=True, null=True)

	# indicates whether and when the invoice was marked as paid
	is_paid = models.BooleanField(default=False)
	paid_date = models.DateTimeField(blank=True, null=True)

	# indicates whether or not this is the main invoice for a cruise.
	is_cruise_invoice = models.BooleanField(default=True)

	def is_finalizable(self):
		# checks whether the cruise is done, more or less
		if self.cruise is None:
			return True
		return (self.cruise.cruise_end < timezone.now() and self.cruise.is_approved)

	def is_done(self):
		# checks whether the invoice is sent, paid or finalized - thus cannot be changed or deleted
		if self.is_sent or self.is_paid or self.is_finalized:
			return True
		return False

	def __str__(self):
		if self.title != '':
			return self.title
		return 'Untitled invoice'

	def get_list_prices(self):
		return ListPrice.objects.filter(invoice=self.pk)

	def to_dict(self):
		invoice_dict = {}
		invoice_dict["cruise"] = self.cruise
		invoice_dict["event"] = self.event
		invoice_dict["default_invoice_information_for"] = self.default_invoice_information_for
		invoice_dict["title"] = self.title
		invoice_dict["business_reg_num"] = self.business_reg_num
		invoice_dict["billing_address"] = self.billing_address
		invoice_dict["internal_accounting_place"] = self.internal_accounting_place
		invoice_dict["external_accounting_place"] = self.external_accounting_place
		invoice_dict["invoice_mark"] = self.invoice_mark
		invoice_dict["project_number"] = self.project_number
		invoice_dict["project_leader"] = self.project_leader
		invoice_dict["course_code"] = self.course_code
		invoice_dict["course_lecturer"] = self.course_lecturer
		invoice_dict["reference"] = self.reference
		invoice_dict["contact_name"] = self.contact_name
		invoice_dict["contact_email"] = self.contact_email
		invoice_dict["description"] = self.description
		invoice_dict["is_sent"] = self.is_sent
		invoice_dict["is_cruise_invoice"] = self.is_cruise_invoice
		return invoice_dict

	def get_sum(self):
		sum = Decimal(0)
		for item in self.get_list_prices():
			sum += item.price
		return sum

class Equipment(models.Model):
	cruise = models.ForeignKey(Cruise, on_delete=models.CASCADE)

	name = models.CharField(max_length=200, blank=True, default='')
	is_on_board = models.BooleanField(default=False)
	weight = models.FloatField(blank=True, null=True) # in kilograms
	size = models.CharField(max_length=200, blank=True, default='')

	def __str__(self):
		return self.name

class Announcement(models.Model):
	name = models.CharField(max_length=200, blank=True, default='')
	message = SanitizedCharField(
		max_length=1000,
		allowed_tags=['a', 'i'],
		allowed_attributes=['href', 'class'],
		strip=False,
		blank=True,
		default=''
	)
	is_active = models.BooleanField(default=True)

	USERGROUPS = (
		("anon", "Unauthenticated users (guests)"),
		("internal", "Internal users"),
		("external", "External users"),
		("admin", "Administrators"),
		("invoicer", "Invoice managers"),
	)

	target_roles = MultiSelectField(
		choices=USERGROUPS,
		default=("anon", "internal", "external", "admin", "invoicer"),
	)

	ALERT_TYPES = (
		("alert-info", 'Info'),
		("alert-success", 'Success'),
		("alert-warning", 'Warning'),
		("alert-danger", 'Danger'),
	)

	type = models.CharField(
		max_length=20,
		choices=ALERT_TYPES,
		default="alert-info",
	)

	def __str__(self):
		return self.name

	def render(self):
		return mark_safe('<div class="alert '+self.type+'">'+self.message+'</div>')

def get_announcements(**kwargs):
	""" Returns announcements for the user's role if defined,
		otherwise returns announcements for unauthorized users """
	announcements = []
	role = "anon"

	if kwargs.get("userdata"):
		userdata = kwargs.get("userdata")
		if userdata and userdata.role != "":
			role = userdata.role

	for announcement in Announcement.objects.filter(is_active=True):
		if role in announcement.target_roles:
			announcements.append(announcement)

	return announcements

def render_announcements(**kwargs):
	announcements_string = ""
	for announcement in get_announcements(**kwargs):
		announcements_string += announcement.render()
	return announcements_string

class Document(models.Model):
	cruise = models.ForeignKey(Cruise, on_delete=models.CASCADE)

	name = models.CharField(max_length=200, blank=True, default='')
	file = models.FileField(blank=True, null=True)

	def __str__(self):
		return self.name

class Participant(models.Model):
	cruise = models.ForeignKey(Cruise, on_delete=models.CASCADE)

	name = models.CharField(max_length=200, blank=True, default='')
	email = models.EmailField(blank=True, null=True)
	nationality = models.CharField(max_length=50, blank=True, default='')
	date_of_birth = models.DateField(blank=True, null=True)

	def __str__(self):
		return self.name

class Settings(models.Model):
	emails_enabled = models.BooleanField(default=True)
	debug_enabled = models.BooleanField(default=True)
	last_edit_date = models.IntegerField(default=16)
	last_cancel_date = models.IntegerField(default=16)
	internal_order_day_count = models.PositiveSmallIntegerField(default=150)
	external_order_day_count = models.PositiveSmallIntegerField(default=30)
	max_participants = models.PositiveSmallIntegerField(default=20)


	def __str__(self):
		return "Settings object"

def get_settings_object():
	settings_object = Settings.objects.all().first()
	if settings_object is None:
		settings_object = Settings()
		settings_object.save()
	return settings_object

class EventDictionary(models.Model):
	serialized_dictionary = models.TextField()
	needs_update = models.BooleanField(default=True)

	def make_outdated(self):
		self.needs_update = True
		self.save()

	def get_dict(self):
		if self.needs_update:
			self.update()
		return eval(self.serialized_dictionary)

	def update(self):
		print("updated date dict")
		busy_days_dict = {}
		for cruise in Cruise.objects.filter(is_approved=True):
			for cruise_day in cruise.get_cruise_days():
				try:
					if cruise_day.event.start_time:
						date_string = str(cruise_day.event.start_time.date())
						if date_string in busy_days_dict:
							busy_days_dict[date_string] += 1
						else:
							busy_days_dict[date_string] = 1
				except:
					pass
		for event in Event.objects.filter(is_hidden_from_users=False):
			if event.is_scheduled_event():
				date_string = str(event.start_time.date())
				if date_string in busy_days_dict:
					busy_days_dict[date_string] += 1
				else:
					busy_days_dict[date_string] = 1
		self.serialized_dictionary = str(busy_days_dict)
		self.needs_update = False
		self.save()

def get_event_dict_instance():
	event_dict_instance = EventDictionary.objects.all().first()
	if event_dict_instance is None:
		event_dict_instance = EventDictionary()
		event_dict_instance.save()
	return event_dict_instance

def set_date_dict_outdated():
	instance = get_event_dict_instance()
	instance.make_outdated()

class CruiseDay(models.Model):
	cruise = models.ForeignKey(Cruise, related_name='cruise', on_delete=models.CASCADE, null=True)
	event = models.OneToOneField(Event, related_name='cruiseday', on_delete=models.CASCADE, null=True)
	season = models.ForeignKey(Season, on_delete=models.SET_NULL, null=True, blank=True)

	is_long_day = models.BooleanField(default=True)
	destination = models.TextField(max_length=2000, blank=True, default='')
	description = models.TextField(max_length=2000, blank=True, default='')

	breakfast_count = models.PositiveSmallIntegerField(blank=True, null=True)
	lunch_count = models.PositiveSmallIntegerField(blank=True, null=True)
	dinner_count = models.PositiveSmallIntegerField(blank=True, null=True)
	special_food_requirements = models.TextField(max_length=2000, blank=True, default='')
	overnight_count = models.PositiveSmallIntegerField(blank=True, null=True)

	def save(self, **kwargs):
		self.update_food()
		super(CruiseDay, self).save(**kwargs)
		self.cruise.update_cruise_start_end()

	def delete(self):
		super(CruiseDay, self).delete()
		self.cruise.update_cruise_start_end()

	def to_dict(self):
		cruiseday_dict = {}
		cruiseday_dict["cruise"] = self.cruise
		cruiseday_dict["event"] = self.event
		cruiseday_dict["is_long_day"] = self.is_long_day
		cruiseday_dict["destination"] = self.destination
		cruiseday_dict["description"] = self.description
		cruiseday_dict["breakfast_count"] = self.breakfast_count
		cruiseday_dict["lunch_count"] = self.lunch_count
		cruiseday_dict["dinner_count"] = self.dinner_count
		cruiseday_dict["special_food_requirements"] = self.special_food_requirements
		cruiseday_dict["overnight_count"] = self.overnight_count
		return cruiseday_dict

	def update_food(self):
		if (self.breakfast_count != None or self.lunch_count != None or self.dinner_count != None or self.overnight_count != None):
			if self.breakfast_count == None:
				self.breakfast_count = 0
			if self.lunch_count == None:
				self.lunch_count = 0
			if self.dinner_count == None:
				self.dinner_count = 0
			if self.overnight_count == None:
				self.overnight_count = 0

	def get_extra_info_string(self):
		info_string = ""
		extra_information_list = []
		if self.breakfast_count:
			if self.breakfast_count == 1:
				extra_information_list.append("1 breakfast")
			else:
				extra_information_list.append(str(self.breakfast_count)+" breakfasts")
		if self.lunch_count:
			if self.lunch_count == 1:
				extra_information_list.append("1 lunch")
			else:
				extra_information_list.append(str(self.lunch_count)+" lunches")
		if self.dinner_count:
			if self.dinner_count == 1:
				extra_information_list.append("1 dinner")
			else:
				extra_information_list.append(str(self.dinner_count)+" dinners")
		if self.overnight_count:
			if self.overnight_count == 1:
				extra_information_list.append("1 overnight stay")
			else:
				extra_information_list.append(str(self.overnight_count)+" overnight stays")
		if self.special_food_requirements:
			extra_information_list.append("the following special requirements regarding food: " + self.special_food_requirements)
		if len(extra_information_list) > 0:
			#random.shuffle(extra_information_list)
			info_string += "Requires "
			if len(extra_information_list) > 2:
				for index, item in enumerate(extra_information_list):
					if index == len(extra_information_list)-1:
						info_string += item
					elif index == len(extra_information_list)-2:
						info_string += item + " and "
					else:
						info_string += item + ", "

			elif len(extra_information_list) > 1:
				info_string += extra_information_list[0] + " and " + extra_information_list[1]
			else:
				info_string += extra_information_list[0]
			info_string += "."
		else:
			info_string = "This day has no requirements for food or overnight stays specified."
		return info_string

	def get_date(self):
		return str(self.event.start_time.date())

	class Meta:
		ordering = ['event__start_time']

	def __str__(self):
		if self.event is not None:
			return "Cruise Day " + str(self.event.start_time.date())
		else:
			return "Eventless Cruise Day (broken, requires fixing)"

class WebPageText(models.Model):
	name = models.CharField(max_length=50, blank=True, default='')
	description = models.TextField(blank=True, default='')
	text = models.TextField(default='')

	def __str__(self):
		return self.name

class Action(models.Model):
	timestamp = models.DateTimeField()
	user = models.ForeignKey(User)
	target = models.TextField(max_length=1000, blank=True, default='')
	action = models.TextField(max_length=1000, blank=True, default='')
	description = models.TextField(max_length=1000, blank=True, default='')

	def __str__(self):
		return "Action by " + str(self.user) + " at " + str(self.timestamp)

class ListPrice(models.Model):
	invoice = models.ForeignKey(InvoiceInformation, on_delete=models.CASCADE)

	name = models.CharField(max_length=200, blank=True, default='')
	price = models.DecimalField(max_digits=MAX_PRICE_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)
	is_generated = models.BooleanField(default=False)

	def __str__(self):
		return self.name

class DebugData(models.Model):
	label = models.TextField(max_length=1000, blank=True, default='')
	timestamp = models.DateTimeField()
	data = models.TextField(max_length=75000, blank=True, default='')
	request_metadata = models.TextField(max_length=75000, blank=True, default='')

	def __str__(self):
		return self.label + " " + str(self.timestamp)

class Statistics(models.Model):
	timestamp = models.DateTimeField(blank=True, null=True)
	event_count = models.PositiveIntegerField(blank=True, default=0)
	cruise_count = models.PositiveIntegerField(blank=True, default=0)
	approved_cruise_count = models.PositiveIntegerField(blank=True, default=0)
	cruise_day_count = models.PositiveIntegerField(blank=True, default=0)
	approved_cruise_day_count = models.PositiveIntegerField(blank=True, default=0)
	user_count = models.PositiveIntegerField(blank=True, default=0)
	emailconfirmed_user_count = models.PositiveIntegerField(blank=True, default=0)
	organization_count = models.PositiveIntegerField(blank=True, default=0)
	email_notification_count = models.PositiveIntegerField(blank=True, default=0)

# Receiver functions

@receiver(post_delete, sender=CruiseDay)
def auto_delete_event_with_cruiseday(sender, instance, **kwargs):
	try:
		instance.event.delete()
	except AttributeError:
		pass

@receiver(post_save, sender=Event, dispatch_uid="set_cruise_missing_information_outdated_receiver")
@receiver(post_save, sender=CruiseDay, dispatch_uid="set_cruise_missing_information_outdated_receiver")
@receiver(post_save, sender=Season, dispatch_uid="set_cruise_missing_information_outdated_receiver")
@receiver(post_save, sender=Cruise, dispatch_uid="set_cruise_missing_information_outdated_receiver")
def set_cruise_missing_information_outdated_receiver(sender, instance, **kwargs):
	Cruise.objects.all().update(missing_information_cache_outdated=True)

@receiver(post_save, sender=Event, dispatch_uid="set_date_dict_outdated_receiver")
@receiver(post_save, sender=CruiseDay, dispatch_uid="set_date_dict_outdated_receiver")
@receiver(post_save, sender=Cruise, dispatch_uid="set_date_dict_outdated_receiver")
def set_date_dict_outdated_receiver(sender, instance, **kwargs):
	set_date_dict_outdated()

@receiver(post_save, sender=CruiseDay, dispatch_uid="update_cruise_invoice_receiver")
@receiver(post_save, sender=Cruise, dispatch_uid="update_cruise_invoice_receiver")
@receiver(post_save, sender=InvoiceInformation, dispatch_uid="update_cruise_invoice_receiver")
def update_cruise_invoice_receiver(sender, instance, **kwargs):
	try:
		instance.cruise.generate_main_invoice()
	except AttributeError:
		pass

	try:
		instance.generate_main_invoice()
	except AttributeError:
		pass
