import datetime
from django import forms
from django.db import models
from django.forms import ModelForm, inlineformset_factory, DateTimeField, DateField, BooleanField, CharField, PasswordInput, ValidationError, DateInput
from reserver.models import Cruise, CruiseDay, Participant, Season, Event, UserData, Organization, Season
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils.safestring import mark_safe

class CruiseForm(ModelForm):
	class Meta:
		model = Cruise
		exclude = ('leader', 'is_submitted','is_deleted','information_approved','is_approved','submit_date','last_edit_date', 'cruise_start')
		
	user = None
		
	def __init__(self, *args, **kwargs):
		if "request" in kwargs:
			self.request = kwargs.pop("request")
		super().__init__(*args, **kwargs)
		try:
			user_org = self.user.userdata.organization
			owner_choices = User.objects.filter(userdata__organization=user_org).exclude(userdata=self.user.userdata)
			self.initial['organization'] = user_org
			self.fields['owner'].queryset = owner_choices
		except AttributeError:
			pass
		self.fields['description'].help_text = "What's the cruise for?"
		self.fields['terms_accepted'].help_text = "Please read through and verify that you accept the above terms and conditions on your use of the R/V Gunnerus."
		self.fields['student_participation_ok'].help_text = "R/V Gunnerus is owned by NTNU and may at times have students or school children aboard during cruises. Please uncheck the box below and let us know in the text field if you wish to reserve yourself against this."
		self.fields['no_student_reason'].label = "Reason for not accepting students"
		self.fields['no_student_reason'].help_text = "Please state why your cruise cannot accomodate students."
		self.fields['management_of_change'].help_text = "Does your cruise require changes in the vessel's computer network, electricity, pneumatics, hydraulics or other systems? If so, please state this here."
		self.fields['safety_clothing_and_equipment'].help_text = "Cruise participants are normally expected to bring their own, but some equipment may be borrowed on board if requested in advance."
		self.fields['safety_analysis_requirements'].help_text = "Do any of the operations or tasks conducted during your cruise require completion of a job safety analysis to ensure safety and efficiency?"
		
	def clean(self):
		Cruise = self.save(commit=False)
		cleaned_data = super(CruiseForm, self).clean()
		if "request" in self:
			# check whether we're saving or submitting the form
			if self.request.POST.get("save_cruise"):
				cleaned_data["is_submitted"] = False
			elif self.request.POST.get("submit_cruise"):
				cruiseday_form = CruiseDayFormSet(self.request.POST)
				participant_form = ParticipantFormSet(self.request.POST)
				cruise_days = cruiseday_form.full_clean()
				cruise_participants = participant_form.full_clean()
				cleaned_data["leader"] = self.request.user
				if (self.is_valid() and cruiseday_form.is_valid() and participant_form.is_valid() and Cruise.is_submittable(cleaned_data=cleaned_data, cruise_days=cruise_days, cruise_participants=cruise_participants)) or self.request.user.is_superuser:
					cleaned_data["is_submitted"] = True
					cleaned_data["submit_date"] = datetime.datetime.now()
				else:
					cleaned_data["is_submitted"] = False
					messages.add_message(self.request, messages.ERROR, mark_safe('Cruise could not be submitted:' + str(Cruise.get_missing_information_string(cleaned_data=cleaned_data, cruise_days=cruise_days, cruise_participants=cruise_participants))))
					self._errors["description"] = ["Test error"] # Will raise a error message
		return cleaned_data

class SeasonForm(ModelForm):
	class Meta:
		model = Season
		exclude = ['season_event', 'external_order_event', 'internal_order_event']
	
	season_event_start_date = DateTimeField(widget=DateInput())
	season_event_end_date = DateTimeField(widget=DateInput())
	internal_order_event_date = DateTimeField(widget=DateInput())
	external_order_event_date = DateTimeField(widget=DateInput())
	
	def clean(self):
		cleaned_data = super(SeasonForm, self).clean()
		season_event_start = cleaned_data.get("season_event_start_date")
		season_event_end = cleaned_data.get("season_event_end_date")
		internal_order_event = cleaned_data.get("internal_order_event_date")
		external_order_event = cleaned_data.get("external_order_event_date")
		
		if (season_event_start <= internal_order_event or season_event_start <= external_order_event):
			raise ValidationError("Order events cannot be before the season event")
		if (season_event_start >= season_event_end):
			raise ValidationError("Season start must be before season end")
	
	def save(self, commit=True):
		season = super(ModelForm, self).save(commit=False)
		season_event = Event()
		season_event.name = 'Event for ' + self.cleaned_data.get("name")
		season_event.start_time = self.cleaned_data.get("season_event_start_date")
		season_event.start_time.replace(hour=23, minute=59)
		season_event.end_time = self.cleaned_data.get("season_event_end_date")
		season_event.end_time.replace(hour=23, minute=59)
		season_event.save()
		internal_order_event = Event()
		internal_order_event.name = 'Event for internal opening of ' + self.cleaned_data.get("name")
		internal_order_event.start_time = self.cleaned_data.get("internal_order_event_date")
		internal_order_event.save()
		external_order_event = Event()
		external_order_event.name = 'Event for external opening of ' + self.cleaned_data.get("name")
		external_order_event.start_time = self.cleaned_data.get("external_order_event_date")
		external_order_event.save()
		season.season_event = season_event
		season.internal_order_event = internal_order_event
		season.external_order_event = external_order_event
		season.save()
		return season
		
class UserForm(ModelForm):
	class Meta:
		model = User
		fields =['email', 'username']
		
	new_password=CharField(widget=PasswordInput(), required=False)
	confirm_password=CharField(widget=PasswordInput(), required=False)

	def clean(self):
		cleaned_data = super(UserForm, self).clean()
		new_password = cleaned_data.get("new_password")
		confirm_password = cleaned_data.get("confirm_password")

		if new_password != confirm_password:
			raise ValidationError("Passwords do not match")

	def save(self, commit=True):
		user = super(ModelForm, self).save(commit=False)
		if self.cleaned_data["new_password"] != "":
			user.set_password(self.cleaned_data["new_password"])
		if commit:
			user.save()
		return user

class UserRegistrationForm(forms.ModelForm):
	class Meta:
		model = User
		fields = ['username', 'first_name', 'last_name', 'email']
		
	password = forms.CharField(widget=PasswordInput(), required=True)
	confirm_password = forms.CharField(widget=PasswordInput(), required=True)
	
	def __init__(self, *args, **kwargs):
		super(UserRegistrationForm, self).__init__(*args, **kwargs)
		
	def clean(self):
		cleaned_data = super(UserRegistrationForm, self).clean()
		password = cleaned_data.get("password")
		confirm_password = cleaned_data.get("confirm_password")

		if password != confirm_password:
			raise ValidationError("Passwords do not match")
		
	def save(self, commit=True):
		user = super(ModelForm, self).save(commit=False)
		user.set_role('not approved')
		if self.cleaned_data["password"] != "":
			user.set_password(self.cleaned_data["password"])
		if commit:
			user.save()
		return user
		
class UserDataForm(forms.ModelForm):
	class Meta:
		model = UserData
		fields = ['phone_number', 'nationality', 'date_of_birth', 'organization']
	
	new_organization = forms.CharField(required=False)
	is_NTNU = forms.BooleanField(required=False)
	
	def __init__(self, *args, **kwargs):
		super(UserDataForm, self).__init__(*args, **kwargs)
		
	def clean(self):
		cleaned_data = super(UserDataForm, self).clean()
		organization = cleaned_data.get("organization")
		new_organization = cleaned_data.get("new_organization")
		is_ntnu = cleaned_data.get("is_ntnu")
		
		if ((organization and new_organization) or ( not organization and not new_organization)):
			raise ValidationError("Choose existing organization or make a new one")
		
	def save(self, commit=True):
		userdata = super(ModelForm, self).save(commit=False)
		if self.cleaned_data["organization"] != None:
			print("Old Org")
			userdata.organization = self.cleaned_data["organization"]
		elif self.cleaned_data["new_organization"] != "":
			print("New Org")
			new_org = Organization()
			new_org.name = self.cleaned_data["new_organization"]
			new_org.is_NTNU = self.cleaned_data["is_NTNU"]
			new_org.save()
			userdata.organization = new_org
		if commit:
			userdata.save()
		return userdata
		
class CruiseDayForm(ModelForm):
	class Meta:
		model = CruiseDay
		exclude = ('event', 'season')
		
	date = DateField()
	has_food = BooleanField(initial=False, required=False)
	field_order=['date','is_long_day','description', 'overnight_count', 'has_food', 'breakfast_count', 'lunch_count', 'dinner_count']
		
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
		
		self.fields['has_food'].label = "Food on board required"
		self.fields['has_food'].help_text = "Does this cruise day need any meals on board? We can provide breakfast, lunch and/or dinner by request."
		
		self.fields['is_long_day'].label = "Long day"
		self.fields['is_long_day'].help_text = "Long days last from a to b, while short days - the default option - last from x to y."
		
		self.fields['breakfast_count'].label = "Breakfasts"
		self.fields['breakfast_count'].help_text = "How many cruise participants will need breakfast on board?"
		self.fields['lunch_count'].label = "Lunches"
		self.fields['lunch_count'].help_text = "How many cruise participants will need lunch on board?"
		self.fields['dinner_count'].label = "Dinners"
		self.fields['dinner_count'].help_text = "How many cruise participants will need dinner on board?"
		self.fields['overnight_count'].label = "Overnight stays"
		self.fields['overnight_count'].help_text = "How many cruise participants will need overnight accommodation on R/V Gunnerus?"
		self.fields['date'].help_text = "The format is YYYY-MM-DD; the date may also be picked using the cruise calendar above instead of typing it in manually."
	
	def save(self, commit=True):
		instance = super(CruiseDayForm, self).save(commit=True)
		# create event for the cruise day
		# i have no idea when a cruise ends or starts, 8-12 and 8-16 is probably fine
		end_time = datetime.time(12,0,0)

		if(self.cleaned_data["is_long_day"]):
			end_time = datetime.time(16,0,0)
			
		start_datetime = datetime.datetime.combine(self.cleaned_data["date"],datetime.time(8,0,0))
		end_datetime = datetime.datetime.combine(self.cleaned_data["date"], end_time)
		
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

#UserDataFormSet = inlineformset_factory(User, UserData, UserDataForm, fields='__all__', can_delete=False)