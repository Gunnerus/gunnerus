from django.db import models
from django.forms import ModelForm, inlineformset_factory, DateTimeField
from reserver.models import Cruise, CruiseDay, Participant

class CruiseForm(ModelForm):
	class Meta:
		model = Cruise
		exclude = ('name','is_submitted','is_deleted','information_approved','cruise_approved','submit_date','last_edit_date')
		
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['description'].help_text = "What's the cruise for?"
		self.fields['terms_accepted'].help_text = "Suspendisse arcu nisi, iaculis nec fringilla vitae, rutrum condimentum nisl. Sed condimentum sit amet diam nec ultrices. Praesent eu metus enim. Integer hendrerit, diam vel euismod interdum, arcu eros laoreet mi, porttitor iaculis turpis felis a neque. Quisque molestie luctus ligula a sodales. Sed rhoncus enim turpis, in interdum orci fermentum nec."
		self.fields['student_participation_ok'].help_text = "R/V Gunnerus is owned by NTNU and may at times have students and school children on cruises. Please uncheck the box below and let us know in the text field if you wish to reserve yourself against this."
		self.fields['no_student_reason'].help_text = "Please state why your cruise cannot accomodate students."
		self.fields['management_of_change'].help_text = "Does your cruise require changes in the vessel's computer network, electricity, pneumatics, hydraulics or other systems? If so, please state this here."
		self.fields['safety_clothing_and_equipment'].help_text = "Cruise participants are normally expected to bring their own, but some equipment may be borrowed on board if requested in advance."
		self.fields['safety_analysis_requirements'].help_text = "Do any of the operations or tasks conducted during your cruise require completion of a job safety analysis to ensure safety and efficiency?"
		
class CruiseDayForm(ModelForm):
	class Meta:
		model = CruiseDay
		exclude = ('event', 'season')
	
	start_time = DateTimeField()
	end_time = DateTimeField()
	event_name = "Cruise Day"
	season = "Current season"
	
	def save(self, commit=True):
		# do something with self.cleaned_data['temp_id']
		return super(CruiseDayForm, self).save(commit=commit)
	
CruiseDayFormSet = inlineformset_factory(Cruise, CruiseDay, CruiseDayForm, fields='__all__', exclude=['event','season'], extra=1)
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