from django.contrib import admin
from .models import Cruise, Event, InvoiceInformation, Organization, Season

admin.site.register([Cruise, Event, InvoiceInformation, Organization, Season])