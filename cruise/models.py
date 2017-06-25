import datetime
from django.db import models
from django.utils import timezone

# Create your models here.

class Cruise(models.Model):
	cruise_name = models.CharField(max_length=200)
	cruise_description = models.CharField(max_length=1000)
	is_submitted = models.BooleanField()
	terms_accepted = models.BooleanField()
	cruise_approved = models.BooleanField()
	last_edit_date = models.DateTimeField(max_length=200)
	submit_date = models.DateTimeField(max_length=200)
	
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