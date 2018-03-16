import datetime
import pytz
from django.utils import timezone
from django import forms
from django.db import models
from django.forms import ModelForm, inlineformset_factory, DateTimeField, DateField, BooleanField, CharField, PasswordInput, ValidationError, DateInput, DateTimeInput, CheckboxSelectMultiple
from reserver.models import *
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.utils.safestring import mark_safe
from reserver.utils import check_for_and_fix_users_without_userdata, send_activation_email

def check_for_and_fix_users_without_userdata():
	for user in User.objects.all():
		# check for users without user data, and add them to unapproved users if they're not admins
		# these may be legacy accounts or accounts created using manage.py's adduser
		try:
			user.userdata
		except:
			user_data = UserData()
			if user.is_superuser:
				user_data.role = "admin"
			else:
				user_data.role = ""
			user_data.user = user
			user_data.save()

class CruiseForm(ModelForm):
	class Meta:
		model = Cruise
		exclude = ('safety_clothing_and_equipment', 'missing_information_cache_outdated', 'missing_information_cache', 'leader', 'organization', 'is_submitted','is_deleted','information_approved','is_approved','submit_date','last_edit_date', 'cruise_start', 'cruise_end')
		widgets = {'owner': CheckboxSelectMultiple}
	user = None
	
	def clean_owner(self):
		# adds current user to owner field to prevent them from losing access on save
		return (self.cleaned_data['owner'] | User.objects.filter(pk=self.user.pk))

	def __init__(self, *args, **kwargs):
		check_for_and_fix_users_without_userdata()
		if "request" in kwargs:
			self.request = kwargs.pop("request")
		super().__init__(*args, **kwargs)
		try:	
			org_user = None
			try:
				org_user = self.instance.leader
			except User.DoesNotExist:
				org_user = self.user
			print(org_user)
			user_org = org_user.userdata.organization
			owner_choices = User.objects.filter(userdata__organization=user_org).exclude(userdata=org_user.userdata)
			self.initial['organization'] = user_org
			self.fields['owner'].queryset = owner_choices
		except AttributeError:
			pass
			
		self.fields['owner'].label = "Cruise owners"
		self.fields['owner'].help_text = "If you wish to give other members of your organization viewing, editing and submit/cancellation access to your cruise you may do so by selecting them here."
		self.fields['number_of_participants'].help_text = "How many will at most be on board at once on your cruise? There's a limit of 20 pax simultaneously, but you may still take more than 20 in a day if your cruise goes out multiple times."
		self.fields['description'].label = "Cruise description"
		self.fields['description'].help_text = "Agenda/aim for the cruise?"
		self.fields['terms_accepted'].help_text = mark_safe("<span class='text-warning glyphicon glyphicon-exclamation-sign' aria-hidden='true'></span> Please read through and verify that you accept the terms and conditions.")
		self.fields['student_participation_ok'].label = "External participation ok"
		self.fields['student_participation_ok'].help_text = "R/V Gunnerus is owned by NTNU and may at times have guests, students or school children aboard during cruises. Uncheck if this is not possible."
		self.fields['no_student_reason'].label = "Reason for not accepting students"
		self.fields['no_student_reason'].help_text = mark_safe("<span class='text-warning glyphicon glyphicon-exclamation-sign' aria-hidden='true'></span> Can you give a reason why this is not possible?")
		self.fields['management_of_change'].help_text = "Does your cruise require changes in the vessel's computer network, electricity, pneumatics, hydraulics or other systems? If so, please state this here."
		self.fields['dangerous_substances_required'].help_text = "Will you be bringing chemicals or other dangerous substances on your cruise?"
		self.fields['substance_datasheets_uploaded'].help_text = "Please upload any relevant datasheets in the \"Documents\" section below and tick the checkbox when you're done."
		self.fields['safety_analysis_requirements'].help_text = "Please enter the relevant safety analysis requirements here or upload them in the \"Documents\" section, and tick the checkbox below."
		self.fields['safety_analysis_required'].help_text = "Do any of the operations or tasks conducted during the cruise require a risk assessment?"
		
class SeasonForm(ModelForm):
	class Meta:
		model = Season
		exclude = ['season_event', 'external_order_event', 'internal_order_event']
	
	season_event_start_date = DateTimeField(widget=DateInput())
	season_event_end_date = DateTimeField(widget=DateInput())
	internal_order_event_date = DateTimeField(widget=DateInput())
	external_order_event_date = DateTimeField(widget=DateInput())
	
	def __init__(self, *args, **kwargs):
		if "request" in kwargs:
			self.request = kwargs.pop("request")
		super().__init__(*args, **kwargs)
	
	def clean(self):
		cleaned_data = super(SeasonForm, self).clean()
		season_event_start = cleaned_data.get("season_event_start_date")
		season_event_end = cleaned_data.get("season_event_end_date")
		internal_order_event = cleaned_data.get("internal_order_event_date")
		external_order_event = cleaned_data.get("external_order_event_date")
		
		if season_event_start and season_event_end and internal_order_event and external_order_event:
			if (season_event_start <= internal_order_event or season_event_start <= external_order_event):
				raise ValidationError("Order events cannot be before the season event")
			if (season_event_start >= season_event_end):
				raise ValidationError("Season start must be before season end")
		
class EventForm(ModelForm):
	class Meta:
		model = Event
		fields = ['name', 'category', 'start_time', 'end_time', 'description', 'is_hidden_from_users']
	
	def clean(self):
		cleaned_data = super(EventForm, self).clean()
		start = cleaned_data.get("start_time")
		end = cleaned_data.get("end_time")
		
		if start and end:
			if (start >= end):
				raise ValidationError("Start time must be before end time")
				
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		try:
			internal_categories = ["Internal season opening", "External season opening", "Season", "Cruise day", "Red day"]
			category_choices = EventCategory.objects.all().exclude(name__in=internal_categories)
			self.fields['category'].queryset = category_choices
		except AttributeError:
			pass
	
	def save(self, commit=True):
		event = super(ModelForm, self).save(commit=False)
		# why were we doing this?
		# event.end_time = event.end_time.replace(hour=23, minute=59)
		event.save()
		return event
		
class AnnouncementForm(ModelForm):
	class Meta:
		model = Announcement
		fields = ['name', 'message', 'is_active', 'target_roles', 'type']
		
class SettingsForm(ModelForm):
	class Meta:
		model = Settings
		fields = '__all__'
		
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		
		self.fields['emails_enabled'].label = "Notification system enabled"
		self.fields['emails_enabled'].help_text = "Unchecking this disables all sending of emails from the notification system for maintenance or debugging."
		
		self.fields['last_edit_date'].label = "Days before cruise editing is disabled"
		self.fields['last_edit_date'].help_text = "This options sets how many days before the cruise editing should be disabled."

		self.fields['last_cancel_date'].label = "Days before cruise cancelling is disabled"
		self.fields['last_cancel_date'].help_text = "This options sets how many days before the cruise cancelling should be disabled. The last cancellation chance email is sent one day before this deadline."
		
		self.fields['internal_order_day_count'].label = "Internal cruise days per year"
		self.fields['internal_order_day_count'].help_text = "How many cruise days are available to internal users per year?"
		
		self.fields['external_order_day_count'].label = "External cruise days per year"
		self.fields['external_order_day_count'].help_text = "How many cruise days are available to internal users per year?"

class NotificationForm(ModelForm):
	recips = forms.ModelMultipleChoiceField(queryset=UserData.objects.exclude(role=''), label='Individual users', required=False)
	all = BooleanField(required=False)
	internal = BooleanField(required=False, label='Internal users')
	external = BooleanField(required=False, label='External users')
	admins = BooleanField(required=False, label='Admins')
	#upcoming_cruise = BooleanField(required=False, label='Users with upcoming cruises') #Implement maybe later
	
	class Meta:
		model = EmailNotification
		fields = ['recips', 'all', 'internal', 'external', 'admins', 'event', 'template', 'is_sent']
		
	def __init__(self, *args, **kwargs):
		if "request" in kwargs:
			self.request = kwargs.pop("request")
		super().__init__(*args, **kwargs)
	
	def clean(self):
		cleaned_data = super(NotificationForm, self).clean()
	
	def save(self, commit=True, new=True, old=None):
		if new:
			notification = super(ModelForm, self).save(commit=False)
			if self.cleaned_data.get("all"):
				qs = UserData.objects.exclude(role='')
			else:
				qs = self.cleaned_data.get("recips")
				if self.cleaned_data.get("internal"):
					qs = (qs.distinct() | UserData.objects.filter(role='internal').distinct()).distinct()
				if self.cleaned_data.get("external"):
					qs = (qs.distinct() | UserData.objects.filter(role='external').distinct()).distinct()
				if self.cleaned_data.get("admins"):
					qs = (qs.distinct() | UserData.objects.filter(role='admin').distinct()).distinct()
				#if self.cleaned_data.get("upcoming_cruise"): #Implement this part mayble later
			notification.save()
			notification.recipients = qs
			notification.save()
			return notification
		else:
			if self.cleaned_data.get("all"):
				qs = UserData.objects.exclude(role='')
			else:
				qs = self.cleaned_data.get("recips")
				if self.cleaned_data.get("internal"):
					qs = (qs.distinct() | UserData.objects.filter(role='internal').distinct()).distinct()
				if self.cleaned_data.get("external"):
					qs = (qs.distinct() | UserData.objects.filter(role='external').distinct()).distinct()
				if self.cleaned_data.get("admins"):
					qs = (qs.distinct() | UserData.objects.filter(role='admin').distinct()).distinct()
			old.recipients = qs
			old.save()
			return old
		
class EmailTemplateNonDefaultForm(ModelForm):
	class Meta:
		model = EmailTemplate
		fields = ['title', 'group', 'message', 'is_active', 'date']
	
	time_before_hours = forms.IntegerField(required=False, label='Hours')
	time_before_days = forms.IntegerField(required=False, label='Days')
	time_before_weeks = forms.IntegerField(required=False, label='Weeks')
	
	def __init__(self, *args, **kwargs):
		if "request" in kwargs:
			self.request = kwargs.pop("request")
		super().__init__(*args, **kwargs)
		
class EmailTemplateForm(ModelForm):
	class Meta:
		model = EmailTemplate
		fields = ['message']
	
	def __init__(self, *args, **kwargs):
		if "request" in kwargs:
			self.request = kwargs.pop("request")
		super().__init__(*args, **kwargs)
		
class UserForm(ModelForm):
	from reserver.utils import send_activation_email
	class Meta:
		model = User
		fields = ['email', 'username', 'first_name', 'last_name']
		
	def __init__(self, *args, **kwargs):
		if "request" in kwargs:
			self.request = kwargs.pop("request")
		super().__init__(*args, **kwargs)
		
	new_password=CharField(widget=PasswordInput(), required=False)
	confirm_password=CharField(widget=PasswordInput(), required=False)

	def clean(self):
		cleaned_data = super(UserForm, self).clean()
		new_password = cleaned_data.get("new_password")
		confirm_password = cleaned_data.get("confirm_password")
		
		if new_password and confirm_password:
			if new_password != confirm_password:
				raise ValidationError("Passwords do not match")
				
		email = cleaned_data.get('email')
		username = cleaned_data.get('username')
		if email and User.objects.filter(email=email).exclude(username=username).exists():
			raise ValidationError({'email': 'Email address already in use.',})

	def save(self, commit=True):
		user = super(ModelForm, self).save(commit=False)
		if self.cleaned_data["new_password"] != "":
			user.set_password(self.cleaned_data["new_password"])
		if self.fields["email"].has_changed(self.initial, self.data) and (self.initial.get("email") != self.data.get("email")):
			send_activation_email(self.request, user)
		if commit:
			user.save()
		return user

class UserRegistrationForm(forms.ModelForm):
	class Meta:
		model = User
		fields = ['username', 'email', 'first_name', 'last_name', 'password', 'confirm_password']
		
	password = forms.CharField(widget=PasswordInput(), required=True)
	confirm_password = forms.CharField(widget=PasswordInput(), required=True)
	
	def __init__(self, *args, **kwargs):
		super(UserRegistrationForm, self).__init__(*args, **kwargs)
		
	def clean(self):
		cleaned_data = super(UserRegistrationForm, self).clean()
		password = cleaned_data.get("password")
		confirm_password = cleaned_data.get("confirm_password")
		email = cleaned_data.get("email")
		
		if not email:
			raise ValidationError("Please enter an email address")
		
		if password and confirm_password:
			if password != confirm_password:
				raise ValidationError("Passwords do not match")
				
	def clean_email(self):
		email = self.cleaned_data.get('email')
		username = self.cleaned_data.get('username')
		if email and User.objects.filter(email=email).exclude(username=username).exists():
			raise ValidationError('Email address already in use.')
		return email
		
	def save(self, commit=True):
		user = super(ModelForm, self).save(commit=False)
		if self.cleaned_data["password"] != "":
			user.set_password(self.cleaned_data["password"])
		if commit:
			user.save()
		return user
		
	def __init__(self, *args, **kwargs):
		super(UserRegistrationForm, self).__init__(*args, **kwargs)
		self.fields['email'].required = True
		#self.fields['email'].label
		self.fields['email'].help_text = "We will send a verification email to this address before you're able to log in, so please double-check that this is correct."

class AdminUserDataForm(forms.ModelForm):
	class Meta:
		model = UserData
		fields = ['organization', 'phone_number', 'nationality', 'date_of_birth']

class UserDataForm(forms.ModelForm):
	class Meta:
		model = UserData
		fields = ['organization', 'phone_number', 'nationality', 'date_of_birth']
	
	new_organization = forms.CharField(required=False)
	is_NTNU = forms.BooleanField(required=False)
	field_order=['organization', 'new_organization', 'is_NTNU', 'phone_number', 'nationality', 'date_of_birth']
		
	def clean(self):
		cleaned_data = super(UserDataForm, self).clean()
		organization = cleaned_data.get("organization")
		new_organization = cleaned_data.get("new_organization")
		is_ntnu = cleaned_data.get("is_ntnu")
		
		if not organization and not new_organization:
			raise ValidationError({'organization': "Please choose an existing organization or make a new one.", 'new_organization': ""})
		
		if organization and new_organization and is_ntnu:
			if ((organization and new_organization) or (not organization and not new_organization)):
				raise ValidationError({'organization': "Please choose an existing organization or make a new one.", 'new_organization': ""})
		
	def save(self, commit=True):
		userdata = super(ModelForm, self).save(commit=False)
		if self.cleaned_data["organization"] != None:
			userdata.organization = self.cleaned_data["organization"]
		elif self.cleaned_data["new_organization"] != "":
			new_org = Organization()
			new_org.name = self.cleaned_data["new_organization"]
			new_org.is_NTNU = self.cleaned_data["is_NTNU"]
			new_org.save()
			userdata.organization = new_org
		if commit:
			userdata.save()
		return userdata
	
	def __init__(self, *args, **kwargs):
		super(UserDataForm, self).__init__(*args, **kwargs)
		self.fields['is_NTNU'].label = "Is an NTNU organization"
		self.fields['phone_number'].help_text = "Optional"
		self.fields['date_of_birth'].help_text = "Optional"
		self.fields['nationality'].help_text = "Optional"
		
class CruiseDayForm(ModelForm):
	utc = pytz.UTC
	
	class Meta:
		model = CruiseDay
		exclude = ('event', 'season')
	
	date = DateTimeField(widget=DateInput())
	has_food = BooleanField(initial=False, required=False)
	field_order=['date','is_long_day', 'destination', 'description', 'overnight_count', 'has_food', 'breakfast_count', 'lunch_count', 'dinner_count']
		
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
		self.fields['is_long_day'].help_text = "Long days - the default option - last from 0800 to 2000, while short days last from 0800 to 1545 in winter and from 0800 to 1500 in summer."
		
		self.fields['breakfast_count'].label = "Breakfasts"
		self.fields['breakfast_count'].help_text = "How many cruise participants will need breakfast on board?"
		self.fields['lunch_count'].label = "Lunches"
		self.fields['lunch_count'].help_text = "How many cruise participants will need lunch on board?"
		self.fields['dinner_count'].label = "Dinners"
		self.fields['dinner_count'].help_text = "How many cruise participants will need dinner on board?"
		self.fields['overnight_count'].label = "Overnight stays"
		self.fields['overnight_count'].help_text = "How many cruise participants will need overnight accommodation on R/V Gunnerus?"
		self.fields['date'].help_text = "The may be picked using the cruise calendar above."
	
	def save(self, commit=True):
		instance = super(CruiseDayForm, self).save(commit=True)
		# create event for the cruise day
		# Long day always 8-20, short day winter 8-15:45, short day summer 8-15:00
		start_datetime = self.cleaned_data["date"].replace(hour=8)
		end_datetime = self.cleaned_data["date"].replace(hour=15)

		if(self.cleaned_data["is_long_day"]):
			end_datetime = self.cleaned_data["date"].replace(hour=20)
		
		if instance.event is not None and instance.event.id is not None:
			event = Event.objects.get(id=instance.event.id)
		else: 
			event = Event()
			
		event.name = "Cruise day " + str(start_datetime.date())
		event.start_time = start_datetime
		event.end_time = end_datetime
		event.category = EventCategory.objects.get(name="Cruise day")
		
		seasons = Season.objects.all()
		for season in seasons:
			if season.contains_time(event.start_time):
				instance.season = season
				#if(season.is_winter):
				#	event.end_time = event.end_time.replace(minutes=45)
			
		event.save()
		
		instance.event = event

		instance.save()
		
		# ModelForms should return the saved model on saving.
		return instance
		
class DocumentForm(ModelForm):
	class Meta:
		model = Document
		exclude = ('cruise',)
		
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['name'].help_text = "Please add a descriptive name for the file you're uploading."
		
class ListPriceForm(ModelForm):
	class Meta:
		model = ListPrice
		exclude = ('invoice', 'is_generated')
		
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		#self.fields['name'].help_text = "Please add a descriptive name for the file you're uploading."
		
class EquipmentForm(ModelForm):
	class Meta:
		model = Equipment
		exclude = ('cruise',)
		
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['is_on_board'].help_text = "Is this a piece of equipment that's already on board the R/V Gunnerus that you need to loan or use? The weight and size fields do not usually need to be filled out in this case."
		self.fields['weight'].help_text = "In kilos."
		self.fields['size'].help_text = "Please describe the size of your item."
		
class OrganizationForm(ModelForm):
	class Meta:
		model = Organization
		fields = '__all__'
		
class EventCategoryForm(ModelForm):
	class Meta:
		model = EventCategory
		exclude = ('name','is_default',)
		
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['icon'].help_text = mark_safe("This needs to be a valid <a target='_BLANK' href='http://fontawesome.io/icons/'>Font Awesome</a> icon.")
		
class EventCategoryNonDefaultForm(ModelForm):
	class Meta:
		model = EventCategory
		exclude = ('is_default',)
		
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['icon'].help_text = mark_safe("This needs to be a valid <a target='_BLANK' href='http://fontawesome.io/icons/'>Font Awesome</a> icon.")
		
class InvoiceInformationForm(ModelForm):
	class Meta:
		model = InvoiceInformation
		exclude = ('cruise', 'default_invoice_information_for', 'title', 'is_sent', 'is_cruise_invoice', 'is_finalized', 'rejection_message', 'send_date', 'is_paid', 'paid_date')
		
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['business_reg_num'].label = "Business registration number"
		self.fields['business_reg_num'].help_text = "This is the number your organization is listed under in the Brønnøysund register."
		self.fields['internal_accounting_place'].label = "Accounting place (K-sted)"
		self.fields['external_accounting_place'].label = "Accounting place"
		self.fields['invoice_mark'].label = "Mark invoice with"
		
CruiseDayFormSet = inlineformset_factory(Cruise, CruiseDay, CruiseDayForm, fields='__all__', extra=1, can_delete=True)
ParticipantFormSet = inlineformset_factory(Cruise, Participant, fields='__all__', extra=1, can_delete=True)
DocumentFormSet = inlineformset_factory(Cruise, Document, DocumentForm, fields='__all__', extra=1, can_delete=True)
EquipmentFormSet = inlineformset_factory(Cruise, Equipment, EquipmentForm, fields='__all__', extra=1, can_delete=True)
InvoiceFormSet = inlineformset_factory(Cruise, InvoiceInformation, InvoiceInformationForm, fields='__all__', extra=1, can_delete=False)