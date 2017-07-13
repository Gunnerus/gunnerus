import datetime
from django.db import models
from django.forms import ModelForm, inlineformset_factory, DateTimeField, DateField, BooleanField
from reserver.models import Cruise, CruiseDay, Participant, Season, Event
from django.contrib.auth.models import User

class CruiseForm(ModelForm):
	class Meta:
		model = Cruise
		exclude = ('is_submitted','is_deleted','information_approved','cruise_approved','submit_date','last_edit_date', 'cruise_start')
		
	user = None
		
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		user_org = self.user.userdata.organization
		owner_choices = User.objects.filter(userdata__organization=user_org)
		self.initial['organization'] = user_org
		self.fields['owner'].queryset = owner_choices
		self.fields['description'].help_text = "What's the cruise for?"
		self.fields['terms_accepted'].help_text = "Suspendisse arcu nisi, iaculis nec fringilla vitae, rutrum condimentum nisl. Sed condimentum sit amet diam nec ultrices. Praesent eu metus enim. Integer hendrerit, diam vel euismod interdum, arcu eros laoreet mi, porttitor iaculis turpis felis a neque. Quisque molestie luctus ligula a sodales. Sed rhoncus enim turpis, in interdum orci fermentum nec."
		self.fields['student_participation_ok'].help_text = "R/V Gunnerus is owned by NTNU and may at times have students and school children on cruises. Please uncheck the box below and let us know in the text field if you wish to reserve yourself against this."
		self.fields['no_student_reason'].help_text = "Please state why your cruise cannot accomodate students."
		self.fields['management_of_change'].help_text = "Does your cruise require changes in the vessel's computer network, electricity, pneumatics, hydraulics or other systems? If so, please state this here."
		self.fields['safety_clothing_and_equipment'].help_text = "Cruise participants are normally expected to bring their own, but some equipment may be borrowed on board if requested in advance."
		self.fields['safety_analysis_requirements'].help_text = "Do any of the operations or tasks conducted during your cruise require completion of a job safety analysis to ensure safety and efficiency?"

class UserForm(ModelForm):
	class Meta:
		model = User
		fields =['email', 'password', 'username']

	def save(self, commit=True):
		user = super(ModelForm, self).save(commit=False)
		user.set_password(self.cleaned_data["password"])
		if commit:
			user.save()
		return user
		
class CruiseDayForm(ModelForm):
	class Meta:
		model = CruiseDay
		exclude = ('event', 'season')
		
	date = DateField()
	has_food = BooleanField(initial=False, required=False)
		
	def __init__(self, *args, **kwargs):
		cruise_day_instance = kwargs.get('instance', None)
		if cruise_day_instance is not None and cruise_day_instance.event is not None:
			kwargs.update(initial={
				# 'field': 'value'
				'date': cruise_day_instance.event.start_time.date(),
				'event': cruise_day_instance.event
			})
		super().__init__(*args, **kwargs)
		self.fields['has_food'].widget.attrs['class'] = 'foodSelector'
		self.fields['breakfast_count'].widget.attrs['class'] = 'food'
		self.fields['lunch_count'].widget.attrs['class'] = 'food'
		self.fields['dinner_count'].widget.attrs['class'] = 'food'
	
	def save(self, commit=True):
		# create event for the cruise day
		# i have no idea when a cruise ends or starts, 8-12 and 8-16 is probably fine
		end_time = datetime.time(16,0,0)

		if(self.cleaned_data["is_long_day"]):
			end_time = datetime.time(12,0,0)
			
		start_datetime = datetime.datetime.combine(self.cleaned_data["date"],datetime.time(8,0,0))
		end_datetime = datetime.datetime.combine(self.cleaned_data["date"], end_time)
			
		instance = super(CruiseDayForm, self).save(commit=True)
		
		if instance.event is not None and instance.event.id is not None:
			event = Event.objects.get(id=instance.event.id)
		else: 
			event = Event()
			
		event.name = "Cruise day from " + str(start_datetime) + " to " + str(end_datetime)
		event.start_time = start_datetime
		event.end_time = end_datetime
			
		event.save()
		
		instance.event = event
		
		instance.save()
		
		# ModelForms should return the saved model on saving.
		return instance
	
CruiseDayFormSet = inlineformset_factory(Cruise, CruiseDay, CruiseDayForm, fields='__all__', extra=1, can_delete=True)
ParticipantFormSet = inlineformset_factory(Cruise, Participant, fields='__all__', extra=1, can_delete=True)