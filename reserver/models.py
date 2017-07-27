import datetime
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.forms.models import model_to_dict

PRICE_DECIMAL_PLACES = 2
MAX_PRICE_DIGITS = 10 + PRICE_DECIMAL_PLACES # stores numbers up to 10^10-1 with 2 digits of accuracy

def get_missing_cruise_information(**kwargs):
	missing_information = {}
	
	# keyword args should be set if called on a form object - can't do db queries before objs exist in db
	
	if kwargs.get("cleaned_data"):
		CruiseDict = kwargs.get("cleaned_data")
	else:
		instance = kwargs.get("cruise")
		CruiseDict = model_to_dict(instance, fields=[field.name for field in instance._meta.fields])
	
	if kwargs.get("cruise_days"):
		temp_cruise_days = kwargs["cruise_days"]
		cruise_days = []
		for cruise_day in temp_cruise_days:
			if cruise_day.fields["date"]:
				cruise_days.append(cruise_day.fields)
			
	else:
		temp_cruise_days = kwargs.get("cruise").get_cruise_days()
		cruise_days = []
		for cruise_day in temp_cruise_days:
			if cruise_day.event.start_time:
				cruise_day_dict = model_to_dict(cruise_day, fields=[field.name for field in cruise_day._meta.fields])
				cruise_day_dict["date"] = cruise_day.event.start_time
				cruise_days.append(cruise_day_dict)
		
	if kwargs.get("cruise_participants"):
		cruise_participants = kwargs["cruise_participants"]
		for cruise_participant in cruise_participants:
			if not cruise_participant.fields["name"]:
				cruise_participants.remove(cruise_participant)
	else:
		cruise_participants = Participant.objects.filter(cruise=kwargs.get("cruise").pk)

	if len(cruise_days) < 1:
		missing_information["cruise_days_missing"] = True
		missing_information["cruise_day_outside_season"] = False
	else:
		missing_information["cruise_days_missing"] = False
		missing_information["cruise_day_outside_season"] = False
		for cruise_day in cruise_days:
			if cruise_day["date"]:
				if not time_is_in_season(cruise_day["date"]):
					missing_information["cruise_day_outside_season"] = True
			
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
		if UserData.objects.get(user=CruiseDict["leader"]).role is "" and not CruiseDict["leader"].is_superuser:
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
	
def time_is_in_season(time):
	for season in Season.objects.all():
		if season.contains_time(time):
			return True
	return False
	
#def event_collides(event):
#	for 
#	return False

class Event(models.Model):
	name = models.CharField(max_length=200)
	start_time = models.DateTimeField(blank=True, null=True)
	end_time = models.DateTimeField(blank=True, null=True)
	description = models.TextField(max_length=1000, blank=True, default='')
	
	class Meta:
		ordering = ['name', 'start_time']
	
	def __str__(self):
		return self.name
		
	def isCruiseDay(self):
		try:
			if self.cruiseday != None:
				return True
		except ObjectDoesNotExist:
			return False
	
	def isSeason(self):
		try:
			if self.season != None:
				return True
		except ObjectDoesNotExist:
			return False
	
	def isInternalOrder(self):
		try:
			if self.internal_order != None:
				return True
		except ObjectDoesNotExist:
			return False
			
	def isExternalOrder(self):
		try:
			if self.external_order != None:
				return True
		except ObjectDoesNotExist:
			return False
		
class Organization(models.Model):
	name = models.CharField(max_length=200)
	is_NTNU = models.BooleanField()
	
	class Meta:
		ordering = ['name']

	def __str__(self):
		return self.name
		
class EmailNotification(models.Model):
	event = models.ManyToManyField(Event)
	
	title = models.CharField(max_length=200, blank=True, default='')
	message = models.TextField(blank=True, default='')
	time_before = models.DurationField(blank=True, null=True)
	is_active = models.BooleanField(default=False)
	is_muteable = models.BooleanField(default=False)
	date = models.DateTimeField(blank=True, null=True)
	
	def __str__(self):
		return self.title

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

	def update_cruise_start(self):
		try:
			self.cruise_start = self.cruiseday_set.order_by('event__start_time').event.start_time
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
		name = self.leader.get_full_name()
		if name is "":
			name = self.leader.username
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
			print("No invoice information exists for this cruise.")
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
	
class CruiseDay(models.Model):
	cruise = models.ForeignKey(Cruise, on_delete=models.CASCADE, null=True)
	event = models.OneToOneField(Event, related_name='cruiseday', on_delete=models.SET_NULL, null=True)
	season = models.ForeignKey(Season, on_delete=models.SET_NULL, null=True, blank=True)
	
	is_long_day = models.BooleanField(default=True)
	description = models.TextField(max_length=2000, blank=True, default='')
	
	breakfast_count = models.PositiveSmallIntegerField(blank=True, null=True)
	lunch_count = models.PositiveSmallIntegerField(blank=True, null=True)
	dinner_count = models.PositiveSmallIntegerField(blank=True, null=True)
	overnight_count = models.PositiveSmallIntegerField(blank=True, null=True)
	
	def save(self, **kwargs):
		self.update_food()
		super(CruiseDay, self).save(**kwargs)
		self.cruise.update_cruise_start()
	
	def delete(self):
		super(CruiseDay, self).delete()
		self.cruise.update_cruise_start()
	
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
