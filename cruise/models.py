import datetime
from django.db import models
from django.utils import timezone

class UserData(models.Model):
	user = OneToOneField(User, on_delete=models.CASCADE)
	is_crew = models.BooleanField()
	role = models.CharField(max_length=50)
	phone_number = models.CharField(max_length=50)
	
	organization = models.ForeignKeymodels.ForeignKey(Organization, on_delete=models.SET_NULL, null=True)
	
	nationality = models.CharField(max_length=50)
	date_of_birth = models.DateField()
	identity_document_types = models.CharField(max_length=200)
	
class Participant(models.Model):
	cruise = models.ForeignKey(Cruise, on_delete=models.CASCADE)
	email = models.EmailField()
	name = models.CharField(max_length=200)
	
	nationality = models.CharField(max_length=50)
	date_of_birth = models.DateField()
	identity_document_types = models.CharField(max_length=200)
	
class Organization(models.Model):
	name = models.CharField(max_length=200)
	is_NTNU = models.BooleanField()
	default_invoice_information = models.ForeignKey(InvoiceInformation, on_delete=models.SET_NULL, null=True)
	
class InvoiceInformation(models.Model):
	business_reg_num = models.PositiveIntegerField()
	invoice_address = models.CharField(max_length=200)
	accounting_place = models.CharField(max_length=200)
	project_number = models.CharField(max_length=200)
	invoice_mark = models.CharField(max_length=200)
	contact_name = models.CharField(max_length=200)
	contact_email = models.EmailField()
	
class ListPrice(models.Model):
	invoice = models.ForeignKeymodels.ForeignKey(InvoiceInformation, on_delete=models.CASCADE
	name = models.CharField(max_length=200)
	price = models.DecimalField()
	
class Cruise(models.Model):
	cruise_name = models.CharField(max_length=200)
	cruise_description = models.CharField(max_length=1000)
	is_submitted = models.BooleanField()
	terms_accepted = models.BooleanField()
	cruise_approved = models.BooleanField()
	last_edit_date = models.DateTimeField(max_length=200)
	submit_date = models.DateTimeField(max_length=200)
	
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
	meals_on_board = models.CharField(max_length=500)
	
	def __str__(self):
		return self.cruise_name
		
	def was_edited_recently(self):
		now = timezone.now()
		return now - datetime.timedelta(days=1) <= self.edit_date <= now
		
	was_edited_recently.admin_order_field = 'edit_date'
	was_edited_recently.boolean = True
	was_edited_recently.short_description = 'Edited recently?'

