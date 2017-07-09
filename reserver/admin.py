from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Cruise, Event, InvoiceInformation, Organization, Season, CruiseDay, Participant, UserData
from django.db import models

class UserDataInline(admin.StackedInline):
	model = UserData
	can_delete = False
	
class UserAdmin(BaseUserAdmin):
	inlines = (UserDataInline, )
#
#class CruiseAdmin(admin.ModelAdmin):
#	list_display = ('earliest_cruise_day')
#	
#	def get_queryset(self, request):
#		qs1 = super(CruiseAdmin, self).get_queryset(request)
#		qs2 = CruiseDay.objects.filter(cruise=self.pk).order_by('event__start_time')
#		return qs1.intersection(qs2)
#	
#	def earliest_cruise_day(self, obj):
#		return CruiseDay.objects.filter(cruise=obj.pk).earliest('event__start_time')
#		
#	earliest_cruise_day.admin_order_field = 'earliest_cruise_day'
	
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

admin.site.register([Cruise, Event, InvoiceInformation, Organization, Season, CruiseDay, Participant])