import datetime
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

MAX_PRICE_DIGITS = 12
PRICE_DECIMAL_PLACES = 2 #decimals

class Event(models.Model):
	name = models.CharField(max_length=200)
	
	def __str__(self):
		return self.name
	
class TimeInterval(models.Model):
	event = models.OneToOneField(Event, on_delete=models.CASCADE, null=True, blank=True)
	name = models.CharField(max_length=50)
	start_time = models.DateTimeField()
	end_time = models.DateTimeField()
	
	def __str__(self):
		if self.event: 
			return self.event.name
		else:
			return self.name

class InvoiceInformation(models.Model):
	business_reg_num = models.PositiveIntegerField()
	invoice_address = models.CharField(max_length=200)
	accounting_place = models.CharField(max_length=200)
	project_number = models.CharField(max_length=200)
	invoice_mark = models.CharField(max_length=200)
	contact_name = models.CharField(max_length=200)
	contact_email = models.EmailField()

class Organization(models.Model):
	name = models.CharField(max_length=200)
	is_NTNU = models.BooleanField()
	default_invoice_information = models.ForeignKey(InvoiceInformation, on_delete=models.SET_NULL, null=True)

	def __str__(self):
		return self.name

class UserData(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE)
	is_crew = models.BooleanField()
	role = models.CharField(max_length=50)
	phone_number = models.CharField(max_length=50)
	
	organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True)
	
	nationality = models.CharField(max_length=50)
	date_of_birth = models.DateField()
	identity_document_types = models.CharField(max_length=200)
	
	def __str__(self):
		return self.user.get_full_name()
	
class Season(models.Model):
	name = models.CharField(max_length=100)
	
	season_interval = models.OneToOneField(TimeInterval, on_delete=models.SET_NULL, null=True, related_name='season_interval')
	external_order_interval = models.OneToOneField(TimeInterval, on_delete=models.SET_NULL, null=True, related_name='external_order_interval')
	internal_order_interval = models.OneToOneField(TimeInterval, on_delete=models.SET_NULL, null=True, related_name='internal_order_interval')
	
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
	cruise_name = models.CharField(max_length=200)
	cruise_description = models.CharField(max_length=1000)
	is_submitted = models.BooleanField()
	terms_accepted = models.BooleanField()
	cruise_approved = models.BooleanField()
	last_edit_date = models.DateTimeField()
	submit_date = models.DateTimeField()
	
	season = models.ForeignKey(Season, on_delete=models.SET_NULL, null=True)
	cruise_owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
	organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True)
	
	cruise_leader_name = models.CharField(max_length=200)
	cruise_leader_email = models.EmailField()
	cruise_leader_contact = models.CharField(max_length=200)
	
	student_participation_ok = models.BooleanField()
	no_student_reason = models.CharField(max_length=200)
	
	management_of_change = models.CharField(max_length=200)
	safety_clothing_and_equipment = models.CharField(max_length=200)
	safety_analysis_requirements = models.CharField(max_length=200)
	equipment_description = models.CharField(max_length=200)
	meals_on_board = models.CharField(max_length=471)
	
	def __str__(self):
		return self.cruise_name
		
	def was_edited_recently(self):
		now = timezone.now()
		return now - datetime.timedelta(days=1) <= self.edit_date <= now
		
	was_edited_recently.admin_order_field = 'edit_date'
	was_edited_recently.boolean = True
	was_edited_recently.short_description = 'Edited recently?'
	
class Participant(models.Model):
	cruise = models.ForeignKey(Cruise, on_delete=models.CASCADE)
	email = models.EmailField()
	name = models.CharField(max_length=200)
	
	nationality = models.CharField(max_length=50)
	date_of_birth = models.DateField()
	identity_document_types = models.CharField(max_length=200)
	
	def __str__(self):
		return self.name
	
class CruiseDay(models.Model):
	event = models.OneToOneField(Event, on_delete=models.SET_NULL, null=True)
	cruise = models.OneToOneField(Cruise, on_delete=models.CASCADE)
	
	is_long_day = models.BooleanField()
	description = models.CharField(max_length=471)
	
	breakfast_count = models.PositiveSmallIntegerField()
	lunch_count = models.PositiveSmallIntegerField()
	dinner_count = models.PositiveSmallIntegerField()
	overnight_count = models.PositiveSmallIntegerField()
	
	def __str__(self):
		return self.cruise.name
	
class GeographicalArea(models.Model):
	cruise_day = models.OneToOneField(CruiseDay, on_delete=models.CASCADE)
	name = models.CharField(max_length=200)
	description = models.CharField(max_length=200)
	
	# lat/long is stored as decimal degrees.
	latitude = models.DecimalField(max_digits=13, decimal_places=10)
	longitude = models.DecimalField(max_digits=13, decimal_places=10)
	
	def __str__(self):
		return self.name
	
class ListPrice(models.Model):
	invoice = models.ForeignKey(InvoiceInformation, on_delete=models.CASCADE)
	name = models.CharField(max_length=200)
	price = models.DecimalField(max_digits=MAX_PRICE_DIGITS, decimal_places=PRICE_DECIMAL_PLACES)
	
	def __str__(self):
		return self.name
