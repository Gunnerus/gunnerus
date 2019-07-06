from django.test import TestCase
from reserver.models import *
from reserver.utils import check_default_models
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, date, datetime

def create_initial_test_models():
    check_default_models() # creates one org, event categories, and email templates
    ext_org = Organization.objects.create(name='NASA', is_NTNU=False)
    SeasonForm(data={
        'name':"test summer season",
        'season_event_start_date':datetime(2019, 4, 1, 8),
        'season_event_end_date':datetime(2019, 9, 30, 20),
        'internal_order_event_date':datetime(2019, 1, 1, 8),
        'external_order_event_date':datetime(2019, 2, 1, 8),
        'long_education_price':9,
        'long_research_price':3,
        'long_boa_price':5,
        'long_external_price':3,
        'short_education_price':7,
        'short_research_price':3,
        'short_boa_price':8,
        'short_external_price':1,
        'breakfast_price':1,
        'lunch_price':1,
        'dinner_price':1
    }).save()

    SeasonForm(data={
        'name':"test winter season",
        'season_event_start_date':datetime(2019, 10, 1, 8),
        'season_event_end_date':datetime(2019, 3, 31, 20),
        'internal_order_event_date':datetime(2019, 7, 1, 8),
        'external_order_event_date':datetime(2019, 8, 1, 8),
        'long_education_price':8,
        'long_research_price':4,
        'long_boa_price':3,
        'long_external_price':4,
        'short_education_price':8,
        'short_research_price':2,
        'short_boa_price':9,
        'short_external_price':1,
        'breakfast_price':1,
        'lunch_price':1,
        'dinner_price':1
    }).save()

def create_blank_cruise(leader):
    return Cruise.objects.create(leader=leader)

def create_basic_cruise(leader, description, number_of_participants):
    return Cruise.objects.create(leader=leader, description=description, number_of_participants=number_of_participants)

def create_cruise_day(season, date, cruise, season, is_long_day, destination, description, breakfast_count, lunch_count, dinner_count, special_food_requirements, overnight_count):
    return CruiseDay.objects.create(cruise=cruise, event=Event.objects.create(name='Cruise day', start_time=date()))

def create_events():
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
	ev10 = Event.objects.create(name='Cruise day 1', start_time=date(2017, 11, 3))
	ev11 = Event.objects.create(name='Cruise day 2', start_time=date(2017, 11, 4))
	ev12 = Event.objects.create(name='Cruise day 3', start_time=date(2017, 11, 5))
	ev13 = Event.objects.create(name='Cruise day 4', start_time=date(2017, 11, 6))

def create_users():
    #Creating users
	u1 = User.objects.create_user(username='jon_snow', email='jon.snow@nightswatch.net', password='knows some things')
	u2 = User.objects.create_user(username='hot_pie', email='hawtpie@orphan.org', password='winterhell')
	u3 = User.objects.create_user(username='jorah_da_explorah', email='jorah.mormont@mereen.com', password='khaleeeeeeesi')
	u4 = User.objects.create_user(username='arry', email='noone@faceless.se', password='the hound merryn trant queen cersei joffrey the tickler the mountain')
	u5 = User.objects.create_user(username='bran_not_the_builder', email='brandon.stark@winterfell.gov', password='rip legs now i fly')

    #Creating user data
	#u = UserData.objects.create(organization=, user=User.objects.create(username=, email=, password=), role=, phone_number=, nationality=, identity_document_types=, is_crew=, date_of_birth=)
	u_d1 = UserData.objects.create(organization=org7, user=u1, role='internal', phone_number='0000', nationality='The North', identity_document_types='Driver\'s license', is_crew=False, date_of_birth=date(281, 2, 15))
	u_d2 = UserData.objects.create(organization=org1, user=u2, role='external', phone_number='1111', nationality='The Crownlands', identity_document_types='Passport, looks supsiciously like a pice of bread', is_crew=False, date_of_birth=date(287, 6, 3))
	u_d3 = UserData.objects.create(organization=org5, user=u3, role='not_approved', phone_number='1234', nationality='The North', identity_document_types='Driver\'s license', is_crew=True, date_of_birth=date(269, 8, 24))
	u_d4 = UserData.objects.create(organization=org6, user=u4, role='internal', phone_number='5432', nationality='The North', identity_document_types='5 fake passports with different identities', is_crew=True, date_of_birth=date(288, 5, 5))
	u_d5 = UserData.objects.create(organization=org4, user=u5, role='invoicer', phone_number='7345', nationality='The North', identity_document_types='Visa', is_crew=False, date_of_birth=date(290, 1, 1))

def create_seasons():
    #Creating seasons
	#s = Season.objects.create(name=, season_event, external_order_event, internal_order_event=, is_winter=, long_education_price=, long_research_price=, long_boa_price=, long_external_price=, short_education_price=, short_research_price=, short_boa_price=, short_external_price=, breakfast_price=, lunch_price=, dinner_price=)
	s1 = Season.objects.create(name='Summer 2017', season_event=ev4, external_order_event=ev6, internal_order_event=ev5, long_education_price=2000, long_research_price=2400, long_boa_price=2600, long_external_price=4000, short_education_price=1000, short_research_price=1200, short_boa_price=1300, short_external_price=2000)
	s2 = Season.objects.create(name='Winter 2017/2018', season_event=ev7, external_order_event=ev9, internal_order_event=ev8, long_education_price=2200, long_research_price=2600, long_boa_price=2800, long_external_price=4200, short_education_price=1100, short_research_price=1300, short_boa_price=1400, short_external_price=2100)

def create_cruises():
    continue

def create_equipment():
    #Creating equipment
	#equip = Equipment.objects.create(cruise=, name=, is_on_board=, weight=, size=)
	equip1 = Equipment.objects.create(cruise=c1, name='Dragon glass/obsidian, 50 pieces', is_on_board=False, 12.0, "Box, 35x35x35cm")

def create_participants():
    #Creating participants
	#part = Participant.objects.create(cruise=, name= email=, nationality=, date_of_birth=, identity_document_types=)
	part1 = Participant.objects.create(cruise=c1, name='Tormund "Horn-blower", "Husband to bears", "Father of hosts" Giantsbane', email='tormund.giantsbane@freefolk.net', nationality='Beyond the Wall', date_of_birth=None)
	part2 = Participant.objects.create(cruise=c1, name='Eddison "Dolororus Edd" Tollett', email='edd.tollett@nightswatch.net', nationality='The Vale', date_of_birth=None)

def create_cruise_days():
    continue
