from reserver.models import Event, Organization, EmailNotification, UserData, UserPreferences, Season, Cruise, InvoiceInformation, Equipment, Document, Participant, CruiseDay, WebPageText, SystemSettings, GeographicalArea, ListPrice
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, date, datetime


def create_test_models():
	#Creating organizations
	#org = Organization.objects.create(name='', is_NTNU=)
	org1 = Organization.objects.create(name='Fakultet for klovnekunst', is_NTNU=True)
	org2 = Organization.objects.create(name='Fakultet for typografi', is_NTNU=True)
	org3 = Organization.objects.create(name='Statgass', is_NTNU=False)
	org4 = Organization.objects.create(name='Institutt for pingvinvitenskap', is_NTNU=True)
	org5 = Organization.objects.create(name='NASA',  is_NTNU=False)
	org6 = Organization.objects.create(name='Ila barnehage',  is_NTNU=False)
	org7 = Organization.objects.create(name='The Researcher\'s Night\'s watch',  is_NTNU=False)
	
	#Creating events
	#ev = Event.objects.create(name='', start_time=, end_time=)
	ev1 = Event.objects.create(name='Cruise created', start_time=date(2017, 6, 30))
	ev2 = Event.objects.create(name='Cruise start', start_time=date(2017, 7, 28))
	ev3 = Event.objects.create(name='Cruise end', start_time=date(2017, 7, 30))
	ev4 = Event.objects.create(name='Summer 2017', start_time=datetime(2017, 4, 1), end_time=datetime(2017, 10, 1))
	ev5 = Event.objects.create(name='Internal order summer 2017', start_time=datetime(2017, 1, 1))
	ev6 = Event.objects.create(name='External order summer 2017', start_time=datetime(2017, 2, 1))
	ev7 = Event.objects.create(name='Winter 2017/2018', start_time=datetime(2017, 10, 1), end_time=datetime(2018, 4, 1))
	ev8 = Event.objects.create(name='Internal order winter 2017/2018', start_time=datetime(2017, 7, 1))
	ev9 = Event.objects.create(name='External order winter 2017/2018', start_time=datetime(2017, 8, 1))
	ev10 = Event.objects.create(name='Cruise day 1', start_time=datetime(2017, 11, 3, 8), end_time=datetime(2017, 11, 3, 16))
	ev11 = Event.objects.create(name='Cruise day 2', start_time=datetime(2017, 11, 4, 8), end_time=datetime(2017, 11, 3, 16))
	ev12 = Event.objects.create(name='Cruise day 3', start_time=datetime(2017, 11, 5, 8), end_time=datetime(2017, 11, 3, 16))
	ev13 = Event.objects.create(name='Cruise day 4', start_time=datetime(2017, 11, 6, 8), end_time=datetime(2017, 11, 3, 16))
	
	#Creating email notifications
	#em_no = EmailNotification.objects.create(event=, title=, message=, time_before=, is_active=, is_muteable=)
	em_no1 = EmailNotification.objects.create(title='Cruise in 4 weeks', message='A cruise you are participating in is in 4 weeks', time_before=timedelta(days=28), is_active=True, is_muteable=False)
	em_no1.event.add(ev2)
	em_no1.save()
	em_no2 = EmailNotification.objects.create(title='Cruise in 3 weeks', message='A cruise you are participating in is in 3 weeks', time_before=timedelta(days=21), is_active=True, is_muteable=False)
	em_no2.event.add(ev2)
	em_no2.save()
	em_no3 = EmailNotification.objects.create(title='Cruise in 2 weeks', message='A cruise you are participating in is in 2 weeks', time_before=timedelta(days=14), is_active=True, is_muteable=False)
	em_no3.event.add(ev2)
	em_no3.save()
	em_no4 = EmailNotification.objects.create(title='Cruise in 1 week', message='A cruise you are participating in is in 1 week', time_before=timedelta(days=7), is_active=True, is_muteable=False)
	em_no4.event.add(ev2)
	em_no4.save()
	em_no5 = EmailNotification.objects.create(title='Cruise missing information', message='A cruise departing in 4 weeks needs more information', time_before=timedelta(days=28), is_active=True, is_muteable=False)
	em_no5.event.add(ev2)
	em_no5.save()
	em_no6 = EmailNotification.objects.create(title='Cruise missing information', message='A cruise departing in 3 weeks needs more information', time_before=timedelta(days=21), is_active=True, is_muteable=False)
	em_no6.event.add(ev2)
	em_no6.save()
	em_no7 = EmailNotification.objects.create(title='New cruise created', message='You have been set as an owner of a cruise', time_before=timedelta(days=0), is_active=True, is_muteable=False)
	em_no7.event.add(ev1)
	em_no7.save()
	
	#Creating users
	u1 = User.objects.create_user(username='jon_snow', email='jon.snow@nightswatch.net', password='knows some things')
	u2 = User.objects.create_user(username='hot_pie', email='hawtpie@orphan.org', password='winterhell')
	u3 = User.objects.create_user(username='jorah_da_explorah', email='jorah.mormont@mereen.com', password='khaleeeeeeesi')
	u4 = User.objects.create_user(username='arry', email='noone@faceless.se', password='the hound merryn trant queen cersei joffrey the tickler the mountain')
	u5 = User.objects.create_user(username='bran_not_the_builder', email='brandon.stark@winterfell.gov', password='rip legs now i fly')
	
	#Creating user data
	#u = UserData.objects.create(organization=, user=User.objects.create(username=, email=, password=), role=, phone_number=, nationality=, is_crew=, date_of_birth=)
	u_d1 = UserData.objects.create(organization=org7, user=u1, role='internal', phone_number='0000', nationality='The North', is_crew=False, date_of_birth=date(281, 2, 15))
	u_d2 = UserData.objects.create(organization=org1, user=u2, role='external', phone_number='1111', nationality='The Crownlands', is_crew=False, date_of_birth=date(287, 6, 3))
	u_d3 = UserData.objects.create(organization=org5, user=u3, role='not_approved', phone_number='1234', nationality='The North', is_crew=True, date_of_birth=date(269, 8, 24))
	u_d4 = UserData.objects.create(organization=org6, user=u4, role='internal', phone_number='5432', nationality='The North', is_crew=True, date_of_birth=date(288, 5, 5))
	u_d5 = UserData.objects.create(organization=org4, user=u5, role='internal', phone_number='7345', nationality='The North', is_crew=False, date_of_birth=date(290, 1, 1))
	
	#Creating user preferences
	#u = UserPreferences.objects.create(user=)
	"""
	u_p1 = UserPreferences.objects.create(user=u1)
	u_p2 = UserPreferences.objects.create(user=u2)
	u_p3 = UserPreferences.objects.create(user=u3)
	u_p4 = UserPreferences.objects.create(user=u4)
	u_p5 = UserPreferences.objects.create(user=u5)
	"""
	
	#Creating seasons
	#s = Season.objects.create(name=, season_event, external_order_event, internal_order_event=, long_education_price=, long_research_price=, long_boa_price=, long_external_price=, short_education_price=, short_research_price=, short_boa_price=, short_external_price=)
	s1 = Season.objects.create(name='Summer 2017', season_event=ev4, external_order_event=ev6, internal_order_event=ev5, long_education_price=2000, long_research_price=2400, long_boa_price=2600, long_external_price=4000, short_education_price=1000, short_research_price=1200, short_boa_price=1300, short_external_price=2000)
	s2 = Season.objects.create(name='Winter 2017/2018', season_event=ev7, external_order_event=ev9, internal_order_event=ev8, long_education_price=2200, long_research_price=2600, long_boa_price=2800, long_external_price=4200, short_education_price=1100, short_research_price=1300, short_boa_price=1400, short_external_price=2100)
	
	#Creating cruises
	#c = Cruise.objects.create(leader=, organization=, name=, description=, last_edit_date=, submit_date=, student_participation_ok=)
	c1 = Cruise.objects.create(leader=u1, organization=org7, name='Save wildlings at Hardhome', description='We\'re going to Hardhome to pick up some wildlings before the White Walkers get them and add them to their army of the dead', last_edit_date=datetime.now(), submit_date=None, student_participation_ok=True, equipment_description='Swords, food, blankets, etc.')
	
	#Creating invoice information
	
	
	#Creating equipment
	#equip = Equipment.objects.create(cruise=, name=, is_on_board=)
	equip1 = Equipment.objects.create(cruise=c1, name='Dragon glass/obsidian, 50 pieces', is_on_board=False)
	
	#Creating documents
	
	
	#Creating participants
	#part = Participant.objects.create(cruise=, name= email=, nationality=, date_of_birth=)
	part1 = Participant.objects.create(cruise=c1, name='Tormund "Horn-blower", "Husband to bears", "Father of hosts" Giantsbane', email='tormund.giantsbane@freefolk.net', nationality='Beyond the Wall', date_of_birth=None)
	part2 = Participant.objects.create(cruise=c1, name='Eddison "Dolororus Edd" Tollett', email='edd.tollett@nightswatch.net', nationality='The Vale', date_of_birth=None)
	
	#Creating cruise days
	#c_day = CruiseDay.objects.create(cruise=, event=, season=, is_long_day=, description=, breakfast_count=, lunch_count=, dinner_count=, overnight_count=)
	c_day1 = CruiseDay.objects.create(cruise=c1, event=ev10, season=s2, is_long_day=True, description='Setting out from East Watch by the Sea', breakfast_count=200, lunch_count=200, dinner_count=200, overnight_count=200)
	c_day2 = CruiseDay.objects.create(cruise=c1, event=ev11, season=s2, is_long_day=True, description='Arriving at Hardhome, begin putting wildlings on ships', breakfast_count=200, lunch_count=200, dinner_count=10000, overnight_count=10000)
	c_day3 = CruiseDay.objects.create(cruise=c1, event=ev12, season=s2, is_long_day=True, description='Finish up at Hardhome and set sail again', breakfast_count=11000, lunch_count=13000, dinner_count=15000, overnight_count=15000)
	c_day4 = CruiseDay.objects.create(cruise=c1, event=ev13, season=s2, is_long_day=True, description='Arrive at East Watch by the Sea', breakfast_count=15000, lunch_count=5000, dinner_count=100, overnight_count=0)
	
	#Creating web page text
	
	
	#Creating system settings
	
	
	#Creating geographical areas
	
	
	#Creating list prices
	