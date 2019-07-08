from django.urls import reverse
from django.test import TestCase
from django.test.utils import setup_test_environment
from django.test import Client
from django.utils import timezone
from reserver.models import *
from reserver.forms import *
from reserver.utils import check_default_models
from django.contrib.auth.models import User
from datetime import date, datetime
import pytz

def create_initial_test_models():
	create_users()
	create_seasons()

def create_users():
	#Creating users
	u1 = User.objects.create(username='testadmin', email='jon.snow@example.com', password='knows some things')
	u2 = User.objects.create(username='pie', email='hawtpie@example.com', password='winterhell')
	u3 = User.objects.create(username='bear', email='jorah.mormont@example.com', password='khaleeeeeeesi')
	u4 = User.objects.create(username='arry', email='noone@example.com', password='the hound merryn trant queen cersei joffrey the tickler the mountain')
	u5 = User.objects.create(username='raven', email='brandon.stark@example.com', password='rip legs now i fly')

	#Creating basic organizations
	int_org = Organization.objects.create(name="test int org", is_NTNU=True)
	ext_org = Organization.objects.create(name="test ext org", is_NTNU=False)

	#Creating user data
	#u = UserData.objects.create(organization=, user=User.objects.create(username=, email=, password=), role=, phone_number=, nationality=, identity_document_types=, is_crew=, date_of_birth=)
	u_d1 = UserData.objects.create(organization=int_org, user=u1, role='admin', phone_number='0000', nationality='The North', is_crew=False, date_of_birth=date(281, 2, 15))
	u_d2 = UserData.objects.create(organization=ext_org, user=u2, role='external', phone_number='1111', nationality='The Crownlands', is_crew=False, date_of_birth=date(287, 6, 3))
	u_d3 = UserData.objects.create(organization=ext_org, user=u3, role='not_approved', phone_number='1234', nationality='The North', is_crew=True, date_of_birth=date(269, 8, 24))
	u_d4 = UserData.objects.create(organization=int_org, user=u4, role='internal', phone_number='5432', nationality='The North', is_crew=True, date_of_birth=date(288, 5, 5))
	u_d5 = UserData.objects.create(organization=int_org, user=u5, role='invoicer', phone_number='7345', nationality='The North', is_crew=False, date_of_birth=date(290, 1, 1))

def create_seasons():
	zone = pytz.timezone("Europe/Oslo")
	Season.objects.create(
		name="test summer season",
		season_event=Event.objects.create(
			name="summer start",
			start_time=datetime(2019, 4, 1, 8).replace(tzinfo=zone),
			end_time=datetime(2019, 9, 30, 20).replace(tzinfo=zone)),
		internal_order_event=Event.objects.create(
			name="summer int order",
			start_time=datetime(2019, 1, 1, 8).replace(tzinfo=zone)),
		external_order_event=Event.objects.create(
			name="summer ext order",
			start_time=datetime(2019, 2, 1, 8).replace(tzinfo=zone)),
		long_education_price=9,
		long_research_price=3,
		long_boa_price=5,
		long_external_price=3,
		short_education_price=7,
		short_research_price=3,
		short_boa_price=8,
		short_external_price=1,
		breakfast_price=1,
		lunch_price=1,
		dinner_price=1
	)
	Season.objects.create(
		name="test winter season",
		season_event=Event.objects.create(
			name="winter start",
			start_time=datetime(2019, 10, 1, 8).replace(tzinfo=zone),
			end_time=datetime(2020, 3, 31, 20).replace(tzinfo=zone)),
		internal_order_event=Event.objects.create(
			name="winter int order",
			start_time=datetime(2019, 7, 1, 8).replace(tzinfo=zone)),
		external_order_event=Event.objects.create(
			name="winter ext order",
			start_time=datetime(2019, 8, 1, 8).replace(tzinfo=zone)),
		long_education_price=8,
		long_research_price=4,
		long_boa_price=6,
		long_external_price=4,
		short_education_price=6,
		short_research_price=4,
		short_boa_price=9,
		short_external_price=1,
		breakfast_price=1,
		lunch_price=1,
		dinner_price=1
	)

def create_equipment():
	#Creating equipment
	#equip = Equipment.objects.create(cruise=, name=, is_on_board=, weight=, size=)
	equip1 = Equipment.objects.create(cruise=c1, name='Dragon glass/obsidian, 50 pieces', is_on_board=False, weight=12.0, size="Box, 35x35x35cm")

def create_participants():
	#Creating participants
	#part = Participant.objects.create(cruise=, name= email=, nationality=, date_of_birth=, identity_document_types=)
	part1 = Participant.objects.create(cruise=c1, name='Tormund "Horn-blower", "Husband to bears", "Father of hosts" Giantsbane', email='tormund.giantsbane@freefolk.net', nationality='Beyond the Wall', date_of_birth=None)
	part2 = Participant.objects.create(cruise=c1, name='Eddison "Dolororus Edd" Tollett', email='edd.tollett@nightswatch.net', nationality='The Vale', date_of_birth=None)
