import datetime
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.forms.models import model_to_dict
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models.signals import post_delete


PRICE_DECIMAL_PLACES = 2
MAX_PRICE_DIGITS = 10 + PRICE_DECIMAL_PLACES # stores numbers up to 10^10-1 with 2 digits of accuracy

def get_missing_cruise_information(**kwargs):
	missing_information = {}
	
	# keyword args should be set if called on a form object - can't do db queries before objs exist in db
	if kwargs.get("cleaned_data"):
		CruiseDict = kwargs.get("cleaned_data")
	else:
		instance = kwargs.get("cruise")
		cruise = Cruise.objects.select_related().get(pk=instance.pk)
		CruiseDict = cruise.to_dict()
		CruiseDict["leader"] = cruise.leader
	
	if kwargs.get("cruise_days"):
		temp_cruise_days = kwargs["cruise_days"]
		cruise_days = []
		print(temp_cruise_days)
		for cruise_day in temp_cruise_days:
			print(cruise_day)
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
		cruise_participants = Participant.objects.select_related().filter(cruise=kwargs.get("cruise").pk)
	
	if len(cruise_days) < 1:
		missing_information["cruise_days_missing"] = True
		missing_information["season_not_open_to_user"] = False
		missing_information["cruise_day_outside_season"] = False
		missing_information["cruise_day_overlaps"] = False
		missing_information["cruise_day_in_past"] = False
	else:
		missing_information["cruise_days_missing"] = False
		missing_information["season_not_open_to_user"] = False
		missing_information["cruise_day_outside_season"] = False
		missing_information["cruise_day_overlaps"] = False
		missing_information["cruise_day_in_past"] = False
		for cruise_day in cruise_days:
			if cruise_day["date"]:
				if not time_is_in_season(cruise_day["date"]):
					missing_information["cruise_day_outside_season"] = True
				if not season_is_open(CruiseDict["leader"], cruise_day["date"]):
					missing_information["season_not_open_to_user"] = True
				if datetime_in_conflict_with_events(cruise_day["date"]):
					missing_information["cruise_day_overlaps"] = True
				if cruise_day["date"] < timezone.now():
					missing_information["cruise_day_in_past"] = True
			
	if (CruiseDict["number_of_participants"] is None and len(cruise_participants) < 1):
		missing_information["cruise_participants_missing"] = True
	else:
		missing_information["cruise_participants_missing"] = False
	if CruiseDict["terms_accepted"]:
		missing_information["terms_not_accepted"] = False
	else:
		missing_information["terms_not_accepted"] = True
	if not CruiseDict["student_participation_ok"] and CruiseDict["no_student_reason"] == "":
		missing_information["no_student_reason_missing"] = True
	else:
		missing_information["no_student_reason_missing"] = False
	try:
		if UserData.objects.select_related().get(user=CruiseDict["leader"]).role is "" and not CruiseDict["leader"].is_superuser:
			missing_information["user_unapproved"] = True
		else:
			missing_information["user_unapproved"] = False
	except (ObjectDoesNotExist, AttributeError):
		# user does not have UserData; probably a superuser created using manage.py's createsuperuser.
		if not User.objects.select_related().get(pk=CruiseDict["leader"]).is_superuser:
			missing_information["user_unapproved"] = True
		else:
			missing_information["user_unapproved"] = False
	
	return missing_information
	
class EventCategory(models.Model):
	name = models.CharField(max_length=200)
	description = models.TextField(max_length=1000, blank=True, default='')
	# contains css-compatible colours stored as a string, such as rgb(0,0,0), #000 or "black"
	colour = models.CharField(max_length=50)

class Event(models.Model):
	name = models.CharField(max_length=200)
	start_time = models.DateTimeField(blank=True, null=True)
	end_time = models.DateTimeField(blank=True, null=True)
	description = models.TextField(max_length=1000, blank=True, default='')
	category = models.ForeignKey(EventCategory, on_delete=models.SET_NULL, null=True, blank=True)
	
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
			
	def is_scheduled_event(self):
		""" should return True for scheduled events such as holidays and planned downtimes. """
		return not (self.is_external_order() or self.is_season() or self.is_internal_order() or self.is_cruise_day())
		
class Organization(models.Model):
	name = models.CharField(max_length=200)
	is_NTNU = models.BooleanField()
	
	class Meta:
		ordering = ['name']

	def __str__(self):
		return self.name

class UserData(models.Model):
	organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, blank= True, null=True)
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userdata')
	
	role = models.CharField(max_length=50, blank=True, default='')
	phone_number = models.CharField(max_length=50, blank=True, default='')
	nationality = models.CharField(max_length=50, blank=True, default='')
	is_crew = models.BooleanField(default=False)
	date_of_birth = models.DateField(blank=True, null=True)
	
	def __str__(self):
		return self.user.get_full_name()
		
class EmailTemplate(models.Model):
	title = models.CharField(max_length=200, blank=True, default='')
	message = models.TextField(blank=True, default='')
	time_before = models.DurationField(blank=True, null=True)
	is_active = models.BooleanField(default=True)
	is_muteable = models.BooleanField(default=False)
	date = models.DateTimeField(blank=True, null=True)
	
	def __str__(self):
		return self.title
		
class EmailNotification(models.Model):
	event = models.ForeignKey(Event, on_delete=models.CASCADE, blank=True, null=True)
	template = models.ForeignKey(EmailTemplate, on_delete=models.CASCADE, blank=True, null=True)
	recipients = models.ManyToManyField(UserData, blank=True)
	
	is_sent = models.BooleanField(default=False)
	
	def __str__(self):
		try:
			return str('Email notification for ' + self.event.name)
		except AttributeError:
			try:
				return self.template.title
			except AttributeError:
				return 'Event- and templateless notification'
		
class UserPreferences(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
	
	def __str__(self):
		return self.user.get_full_name + ' preferences'

class Season(models.Model):
	name = models.CharField(max_length=100)
	
	season_event = models.OneToOneField(Event, on_delete=models.SET_NULL, null=True, related_name='season')
	external_order_event = models.OneToOneField(Event, on_delete=models.SET_NULL, null=True, related_name='external_order')
	internal_order_event = models.OneToOneField(Event, on_delete=models.SET_NULL, null=True, related_name='internal_order')
	
	long_education_price = models.DecimalField(max_digits=MAX_PRICE_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)
	long_research_price = models.DecimalField(max_digits=MAX_PRICE_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)
	long_boa_price = models.DecimalField(max_digits=MAX_PRICE_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)
	long_external_price = models.DecimalField(max_digits=MAX_PRICE_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)
	
	short_education_price = models.DecimalField(max_digits=MAX_PRICE_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)
	short_research_price = models.DecimalField(max_digits=MAX_PRICE_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)
	short_boa_price = models.DecimalField(max_digits=MAX_PRICE_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)
	short_external_price = models.DecimalField(max_digits=MAX_PRICE_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)
	
	def __str__(self):
		return self.name
		
	def contains_time(self, date):
		return (int(self.season_event.start_time.timestamp()) < int(date.timestamp()) < int(self.season_event.end_time.timestamp()))
	
	def delete(self, *args, **kwargs):
		self.season_event.delete()
		self.external_order_event.delete()
		self.internal_order_event.delete()
		return super(self.__class__, self).delete(*args, **kwargs)

class Cruise(models.Model):
	terms_accepted = models.BooleanField(default=False)
	leader = models.ForeignKey(User, related_name='leader')
	organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True)
	owner = models.ManyToManyField(User, related_name='owner', blank=True)

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
	safety_clothing_and_equipment = models.TextField(max_length=2000,  blank=True, default='')
	safety_analysis_requirements = models.TextField(max_length=2000, blank=True, default='')
	number_of_participants = models.PositiveSmallIntegerField(blank=True, null=True)
	cruise_start = models.DateTimeField(blank=True, null=True)
	cruise_end = models.DateTimeField(blank=True, null=True)
	
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
		cruise_dict["number_of_participants"] = self.number_of_participants
		cruise_dict["cruise_start"] = self.cruise_start
		cruise_dict["cruise_end"] = self.cruise_end
		return cruise_dict
	
	def get_cruise_days(self):
		return CruiseDay.objects.filter(cruise=self.pk)
		
	def get_cruise_pdf(self):
		return "Could not get PDF file: get_cruise_pdf() function in models.py not implemented yet."
		
	def get_cruise_description_string(self):
		return "Could not get cruise description string: get_cruise_description_string() function in models.py not implemented yet."
	
	def get_missing_information_list(self, **kwargs):
		missing_info_list = []
		missing_information = self.get_missing_information(**kwargs)
		if missing_information["cruise_days_missing"]:
			missing_info_list.append("Cruise has no cruise days.")
		if missing_information["cruise_participants_missing"]:
			missing_info_list.append("Cruise has no (obvious) information about cruise participants.")
		if missing_information["terms_not_accepted"]:
			missing_info_list.append("Terms and conditions not accepted.")
		if missing_information["no_student_reason_missing"]:
			missing_info_list.append("You need to enter a reason for not accepting students on your cruise.")
		if missing_information["user_unapproved"]:
			missing_info_list.append("Your user account has not been approved yet, so you may not submit this cruise.")
		if missing_information["cruise_day_outside_season"]:
			missing_info_list.append("One or more cruise days are outside a season.")
		if missing_information["cruise_day_overlaps"]:
			missing_info_list.append("One or more cruise days are in conflict with another scheduled event or cruise in the calendar.")
		if missing_information["cruise_day_in_past"]:
			missing_info_list.append("One or more cruise days are in the past.")
		if missing_information["season_not_open_to_user"]:
			missing_info_list.append("One or more cruise days are in seasons not yet open to the user.")

		return missing_info_list

	def get_missing_information_string(self, **kwargs):
		missing_info_string = ""
		missing_information = self.get_missing_information_list(**kwargs)
		for item in missing_information:
			if item:
				missing_info_string += "<br><span>  - " + item + "</span>"
		return missing_info_string
			
	def get_missing_information(self, **kwargs):
		return get_missing_cruise_information(**kwargs, cruise=self)

	def is_missing_information(self, **kwargs):
		return len(self.get_missing_information_list(**kwargs)) > 0

	def is_submittable(self, **kwargs):
		# will have more than this to check for eventually. kind of redundant right now.
		return not self.is_missing_information(**kwargs)

	def update_cruise_start_end(self):
		try:
			self.cruise_start = self.cruiseday_set.order_by('event__start_time').first().event.start_time
			self.cruise_end = self.cruiseday_set.order_by('event__start_time').last().event.end_time
			self.save()
		except (IndexError, AttributeError):
			pass

	class Meta:
		ordering = ['cruise_start']

	def __str__(self):
		cruise_days = CruiseDay.objects.filter(cruise=self.pk)
		cruise_dates = []
		cruise_string = ""
		if cruise_days.count() is not 0:
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
			if name is "":
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

class InvoiceInformation(models.Model):
	cruise = models.ForeignKey(Cruise, on_delete=models.CASCADE, blank=True, null=True)
	default_invoice_information_for = models.ForeignKey(Organization, on_delete=models.SET_NULL, blank=True, null=True)
	
	title = models.CharField(max_length=200, blank=True, default='')
	business_reg_num = models.PositiveIntegerField(blank=True, null=True)
	address = models.CharField(max_length=200, blank=True, default='')
	accounting_place = models.CharField(max_length=200, blank=True, default='')
	project_number = models.CharField(max_length=200, blank=True, default='')
	mark = models.CharField(max_length=200, blank=True, default='')
	contact_name = models.CharField(max_length=200, blank=True, default='')
	contact_email = models.EmailField(blank=True, null=True)
	is_sent = models.BooleanField(default=False)
	
	def __str__(self):
		return self.title
	
class Equipment(models.Model):
	cruise = models.ForeignKey(Cruise, on_delete=models.CASCADE)
	
	name = models.CharField(max_length=200, blank=True, default='')
	is_on_board = models.BooleanField(default=False)
	weight = models.FloatField(blank=True, null=True) # in kilograms
	size = models.CharField(max_length=200, blank=True, default='')

	def __str__(self):
		return self.name
		
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
		
def season_is_open(user, date):
	for season in Season.objects.filter(season_event__end_time__gt=timezone.now()):
		if (season.season_event.start_time < date < season.season_event.end_time):
			if user.userdata.role == 'internal':
				if season.internal_order_event.start_time < date:
					return True
				else:
					return False
			elif user.userdata.role == 'external':
				if season.external_order_event.start_time < date:
					return True
				else:
					return False
			elif user.userdata.role == 'admin':
				return True
	return False
		
def time_is_in_season(time):
	for season in Season.objects.all():
		if season.contains_time(time):
			return True
	return False
	
def datetime_in_conflict_with_events(datetime):
	date_string = str(datetime.date())
	busy_days_dict = get_event_dict_instance().get_dict()
	if date_string in busy_days_dict:
		return (busy_days_dict[date_string] > 1)
	else:
		return False
	
@receiver(post_save, sender=Event, dispatch_uid="set_date_dict_outdated")
def set_date_dict_outdated(sender, instance, **kwargs):
	instance = get_event_dict_instance()
	instance.make_outdated()
	instance.update()
	
def get_event_dict_instance():
	event_dict_instance = EventDictionary.objects.all().first()
	if event_dict_instance is None:
		event_dict_instance = EventDictionary()
		event_dict_instance.save()
	return event_dict_instance
	 
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
		busy_days_dict = {}
		for cruise in Cruise.objects.filter(is_approved=True):
			for cruise_day in cruise.get_cruise_days():
				if cruise_day.event.start_time:
					date_string = str(cruise_day.event.start_time.date())
					if date_string in busy_days_dict:
						busy_days_dict[date_string] += 1
					else:
						busy_days_dict[date_string] = 1
		for event in Event.objects.all():
			if event.is_scheduled_event():
				date_string = str(event.start_time.date())
				if date_string in busy_days_dict:
					busy_days_dict[date_string] += 1
				else:
					busy_days_dict[date_string] = 1
		self.serialized_dictionary = str(busy_days_dict)
		self.needs_update = False
		self.save()

class CruiseDay(models.Model):
	cruise = models.ForeignKey(Cruise, on_delete=models.CASCADE, null=True)
	event = models.OneToOneField(Event, related_name='cruiseday', on_delete=models.CASCADE, null=True)
	season = models.ForeignKey(Season, on_delete=models.SET_NULL, null=True, blank=True)
	
	is_long_day = models.BooleanField(default=True)
	destination = models.TextField(max_length=2000, blank=True, default='')
	description = models.TextField(max_length=2000, blank=True, default='')
	
	breakfast_count = models.PositiveSmallIntegerField(blank=True, null=True)
	lunch_count = models.PositiveSmallIntegerField(blank=True, null=True)
	dinner_count = models.PositiveSmallIntegerField(blank=True, null=True)
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

	class Meta:
		ordering = ['event__start_time']
	
	def __str__(self):
	
		if self.event is not None:
			return "Cruise Day " + str(self.event.start_time.date())
		else:
			return "Eventless Cruise Day (broken, requires fixing)"

@receiver(post_delete, sender=CruiseDay)
def auto_delete_event_with_cruiseday(sender, instance, **kwargs):
	instance.event.delete()
			
class WebPageText(models.Model):
	name = models.CharField(max_length=50, blank=True, default='')
	description = models.TextField(blank=True, default='')
	text = models.TextField(default='')
	
	def __str__(self):
		return self.name
		
class SystemSettings(models.Model):
	work_in_progress = models.BooleanField(default=True)
	
class GeographicalArea(models.Model):
	cruise_day = models.ForeignKey(CruiseDay, on_delete=models.CASCADE)
	
	name = models.CharField(max_length=200, blank=True, default='')
	description = models.TextField(max_length=500, blank=True, default='')
	
	# lat/long is stored as decimal degrees.
	latitude = models.DecimalField(max_digits=13, decimal_places=10, blank=True, null=True)
	longitude = models.DecimalField(max_digits=13, decimal_places=10, blank=True, null=True)
	
	def __str__(self):
		return self.name
	
class ListPrice(models.Model):
	invoice = models.ForeignKey(InvoiceInformation, on_delete=models.CASCADE)
	
	name = models.CharField(max_length=200, blank=True, default='')
	price = models.DecimalField(max_digits=MAX_PRICE_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)
	
	def __str__(self):
		return self.name
