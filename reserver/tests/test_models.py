from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from reserver.models import *
from reserver.tests.setup import create_seasons
import pytz
from datetime import datetime

class EventTests(TestCase):
	def setUp(self):
		create_seasons()

	def test_is_cruise_day(self):
		user = User.objects.create(username="test", password="test")
		cruise = Cruise.objects.create(leader=user)
		event = Event.objects.create(name="test")
		cruise_day = CruiseDay.objects.create(cruise=cruise, event=event)
		self.assertTrue(event.is_cruise_day())

	def test_is_season(self):
		event = Season.objects.get(name="test summer season").season_event
		self.assertTrue(event.is_season())

	def test_is_internal_order(self):
		event = Season.objects.get(name="test summer season").internal_order_event
		self.assertTrue(event.is_internal_order())

	def test_is_external_order(self):
		event = Season.objects.get(name="test summer season").external_order_event
		self.assertTrue(event.is_external_order())

	def test_get_description(self):
		event = Event.objects.create(name="test", description="testing")
		self.assertEqual(event.get_description(), "testing")

	def test_is_scheduled_event(self):
		event = Season.objects.get(name="test summer season").season_event
		self.assertFalse(event.is_scheduled_event())
		event = Event.objects.create(name="empty test")
		self.assertTrue(event.is_scheduled_event())

	def test_get_events_in_period(self):
		zone = pytz.timezone("Europe/Oslo")
		e1 = Event.objects.create(name="test", start_time=datetime(2020, 1, 1).replace(tzinfo=zone))
		e2 = Event.objects.create(name="test", start_time=datetime(2020, 1, 2).replace(tzinfo=zone))
		e3 = Event.objects.create(name="test", start_time=datetime(2020, 1, 3).replace(tzinfo=zone))
		e4 = Event.objects.create(name="test", start_time=datetime(2020, 1, 4).replace(tzinfo=zone))
		self.assertEqual(list(get_events_in_period(datetime(2020, 1, 2).replace(tzinfo=zone), datetime(2020, 1, 3).replace(tzinfo=zone))), [e2,e3])
