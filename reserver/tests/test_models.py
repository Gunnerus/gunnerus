from django.test import TestCase
from django.contrib.auth.models import User
from datetime import datetime, date
from reserver.models import *
from reserver.tests.setup import create_seasons

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
		season = Season.objects.get(name="test summer season")
		event = Event.objects.create(name="test")
		season.season_event = event
		self.assertTrue(event.is_season())

	def test_is_internal_order(self):
		season = Season.objects.get(name="test summer season")
		event = Event.objects.create(name="test")
		season.internal_order_event = event
		self.assertTrue(event.is_internal_order())

	def test_is_external_order(self):
		season = Season.objects.get(name="test summer season")
		event = Event.objects.create(name="test")
		season.external_order_event = event
		self.assertTrue(event.is_external_order())

	def test_get_description(self):
		event = Event.objects.create(name="test", description="testing")
		self.assertEqual(event.get_description(), "testing")

	def test_is_scheduled_event(self):
		season = Season.objects.get(name="test summer season")
		event = Event.objects.create(name="test")
		season.season_event = event
		self.assertFalse(event.is_scheduled_event())
		event = Event.objects.create(name="empty test")
		self.assertTrue(event.is_scheduled_event())

	def test_get_events_in_period(self):
		e1 = Event.objects.create(name="test", start_time=date(2020, 1, 1))
		e2 = Event.objects.create(name="test", start_time=date(2020, 1, 2))
		e3 = Event.objects.create(name="test", start_time=date(2020, 1, 3))
		e4 = Event.objects.create(name="test", start_time=date(2020, 1, 4))
		self.assertEqual(list(get_events_in_period(date(2020, 1, 2), date(2020, 1, 3))), [e2,e3])
