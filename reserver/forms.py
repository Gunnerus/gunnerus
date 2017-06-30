from django.db import models
from django.forms import ModelForm, inlineformset_factory
from reserver.models import Cruise, CruiseDay, Participant
from extra_views import InlineFormSet
from extra_views.generic import GenericInlineFormSet

class CruiseForm(ModelForm):
	class Meta:
		model = Cruise
		exclude = ('is_submitted','submit_date','last_edit_date')
		
class ParticipantInline(InlineFormSet):
	fields = '__all__'
	model = Participant

class CruiseDayInline(InlineFormSet):
	fields = '__all__'
	model = CruiseDay