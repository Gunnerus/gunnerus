import datetime
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

PRICE_DECIMAL_PLACES = 2
MAX_PRICE_DIGITS = 10 + PRICE_DECIMAL_PLACES # stores numbers up to 10^10-1 with 2 digits of accuracy

class Event(models.Model):
	name = models.CharField(max_length=200)
	start_time = models.DateTimeField(blank=True, null=True)
	end_time = models.DateTimeField(blank=True, null=True)
	
	def __str__(self):
		return self.name
		
class Organization(models.Model):
	name = models.CharField(max_length=200)
	is_NTNU = models.BooleanField()

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
	organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True)
	user = models.OneToOneField(User, on_delete=models.CASCADE)
	
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
	
	season_event = models.OneToOneField(Event, on_delete=models.SET_NULL, null=True, related_name='season_event')
	external_order_event = models.OneToOneField(Event, on_delete=models.SET_NULL, null=True, related_name='external_order_event')
	internal_order_event = models.OneToOneField(Event, on_delete=models.SET_NULL, null=True, related_name='internal_order_event')
	
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

class Cruise(models.Model):
	leader = models.ForeignKey(User, related_name='cruise_leader')
	organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True)
	owner = models.ManyToManyField(User, related_name='cruise_owner', blank=True)

	name = models.CharField(max_length=200, blank=True, default='')
	description = models.CharField(max_length=1000, blank=True, default='')
	is_submitted = models.BooleanField(default=False)
	terms_accepted = models.BooleanField(default=False)
	is_deleted = models.BooleanField(default=False)
	information_approved = models.BooleanField(default=False)
	cruise_approved = models.BooleanField(default=False)
	last_edit_date = models.DateTimeField(blank=True, null=True)
	submit_date = models.DateTimeField(blank=True, null=True)
	student_participation_ok = models.BooleanField(default=True)
	no_student_reason = models.CharField(max_length=200, blank=True, default='')
	management_of_change = models.CharField(max_length=200, blank=True, default='')
	safety_clothing_and_equipment = models.CharField(max_length=200,  blank=True, default='')
	safety_analysis_requirements = models.CharField(max_length=200, blank=True, default='')
	equipment_description = models.CharField(max_length=200, blank=True, default='')
	meals_on_board = models.CharField(max_length=471, blank=True, default='')
	number_of_participants = models.PositiveSmallIntegerField(blank=True, null=True)
	
	def __str__(self):
		return self.name
		
	def was_edited_recently(self):
		now = timezone.now()
		return now - datetime.timedelta(days=1) <= self.edit_date <= now
		
	was_edited_recently.admin_order_field = 'edit_date'
	was_edited_recently.boolean = True
	was_edited_recently.short_description = 'Edited recently?'

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
	cruise = models.ForeignKey(Cruise, on_delete=models.CASCADE)
	event = models.OneToOneField(Event, on_delete=models.SET_NULL, null=True)
	season = models.ForeignKey(Season, on_delete=models.SET_NULL, null=True)
	
	is_long_day = models.BooleanField(default=False)
	description = models.CharField(max_length=471, blank=True, default='')
	
	breakfast_count = models.PositiveSmallIntegerField(blank=True, null=True)
	lunch_count = models.PositiveSmallIntegerField(blank=True, null=True)
	dinner_count = models.PositiveSmallIntegerField(blank=True, null=True)
	overnight_count = models.PositiveSmallIntegerField(blank=True, null=True)
	
	def __str__(self):
		return self.cruise.name
		
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
	description = models.CharField(max_length=200, blank=True, default='')
	
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
