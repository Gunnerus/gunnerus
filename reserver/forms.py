from django.db import models
from django.forms import ModelForm, inlineformset_factory
from reserver.models import Cruise, CruiseDay, Participant

class CruiseForm(ModelForm):
	class Meta:
		model = Cruise
		exclude = ('is_submitted','submit_date','last_edit_date')
		
CruiseDayFormSet = inlineformset_factory(Cruise, CruiseDay, fields='__all__', extra=1)
ParticipantFormSet = inlineformset_factory(Cruise, Participant, fields='__all__', extra=1)

