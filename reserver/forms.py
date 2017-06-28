from django.db import models
from django.forms import ModelForm
from reserver.models import Cruise

class CruiseForm(ModelForm):
	class Meta:
		model = Cruise
		exclude = ('is_submitted',)