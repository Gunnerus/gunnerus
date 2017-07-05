from django.contrib import admin
from .models import Cruise, Event, InvoiceInformation, Organization, Season, CruiseDay, Participant

admin.site.register([Cruise, Event, InvoiceInformation, Organization, Season, CruiseDay, Participant])