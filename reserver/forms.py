from django.db import models
from django.forms import ModelForm, inlineformset_factory
from reserver.models import Cruise, CruiseDay, Participant

class CruiseForm(ModelForm):
	class Meta:
		model = Cruise
		exclude = ('is_submitted','submit_date','last_edit_date')
		
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['name'].help_text = "test"
		
CruiseDayFormSet = inlineformset_factory(Cruise, CruiseDay, fields='__all__', extra=1)
ParticipantFormSet = inlineformset_factory(Cruise, Participant, fields='__all__', extra=1)

class BetterCruiseForm(ModelForm):
	class Meta:
		model = Cruise
		exclude = ('is_submitted','submit_date','last_edit_date')
#
#		self.fields['name'].widget.attrs.update({
#					'placeholder': 'Name',
#					'class': 'input-calss_name'
#				})
#		for field in iter(self.fields):
#			self.fields[field].widget.attrs.update({
#				'class': 'form-control'
#		})