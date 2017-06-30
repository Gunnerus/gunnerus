from models import Event, Organization, EmailNotification, TimeInterval, UserData, UserPreferences, 
								Season, Cruises, InvoiceInformation, Equipment, Document, Participant, CruiseDay, 
								WebPageText, SystemSettings, GeographicalArea, ListPrice
from django.db import models
from django.utils import timezone
import datetime

def create_events(models.Model, event_name):
	x = Event(name=event_name)
	x.save()

def create_organization(models.Model):
	x = Organization(name='Fakultet for klovn')
	
def create_time_interval(models.Model):
	