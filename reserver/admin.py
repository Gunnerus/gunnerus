from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Cruise, Event, InvoiceInformation, Organization, Season, CruiseDay, Participant, UserData

class UserDataInline(admin.StackedInline):
	model = UserData
	can_delete = True
	
class UserAdmin(BaseUserAdmin):
	inlines = (UserDataInline, )
	
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

admin.site.register([Cruise, Event, InvoiceInformation, Organization, Season, CruiseDay, Participant])