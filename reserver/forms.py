from django.db import models
from django.forms import ModelForm, inlineformset_factory, DateTimeField
from reserver.models import Cruise, CruiseDay, Participant

class CruiseForm(ModelForm):
	class Meta:
		model = Cruise
		exclude = ('is_submitted','submit_date','last_edit_date')
		
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['cruise_name'].help_text = "test"
		
	start_time = DateTimeField()
	end_time = DateTimeField()
	event_name = "Cruise Day"
	season = "Current season"
	
	def save(self, commit=True):
		# do something with self.cleaned_data['temp_id']
		return super(CruiseForm, self).save(commit=commit)
		
CruiseDayFormSet = inlineformset_factory(Cruise, CruiseDay, fields='__all__', exclude=['event','season'], extra=1)
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