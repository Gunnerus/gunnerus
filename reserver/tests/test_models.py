from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from reserver.models import *
from reserver.tests.setup import *
import pytz
from datetime import datetime, timedelta

class EventTests(TestCase):
	def setUp(self):
		create_some_time_season()

	def test_is_cruise_day(self):
		user = User.objects.create(username="test", password="test")
		cruise = Cruise.objects.create(leader=user)
		event = Event.objects.create(name="test")
		cruise_day = CruiseDay.objects.create(cruise=cruise, event=event)
		self.assertTrue(event.is_cruise_day())

	def test_is_season(self):
		event = Season.objects.all()[0].season_event
		self.assertTrue(event.is_season())

	def test_is_internal_order(self):
		event = Season.objects.all()[0].internal_order_event
		self.assertTrue(event.is_internal_order())

	def test_is_external_order(self):
		event = Season.objects.all()[0].external_order_event
		self.assertTrue(event.is_external_order())

	def test_get_description(self):
		event = Event.objects.create(name="test", description="testing")
		self.assertEqual(event.get_description(), "testing")

	def test_is_scheduled_event(self):
		event = Season.objects.all()[0].season_event
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

class UserDataTests(TestCase):
	def test_get_announcements(self):
		announcement = Announcement.objects.create(name="test", target_roles=["external"])
		user = User.objects.create(username="test", password="test")
		user_data = UserData.objects.create(user=user, role="external")
		self.assertEqual(user_data.get_announcements(), [announcement])

	def test_get_some_announcements(self):
		announcement1 = Announcement.objects.create(target_roles=["external", "anon"])
		announcement2 = Announcement.objects.create(target_roles=["internal", "admin"])
		announcement3 = Announcement.objects.create(target_roles=[])
		announcement4 = Announcement.objects.create(target_roles=["invoicer"])
		announcement5 = Announcement.objects.create(target_roles=["internal"])
		user = User.objects.create(username="test", password="test")
		user_data = UserData.objects.create(user=user, role="internal")
		self.assertEqual(user_data.get_announcements(), [announcement2, announcement5])

	def test_is_invoicer(self):
		self.assertTrue(UserData.objects.create(user=User.objects.create(username="test"), role="invoicer").is_invoicer())

	def test_is_not_invoicer(self):
		self.assertFalse(UserData.objects.create(user=User.objects.create(username="test"), role="admin").is_invoicer())

	def test_save(self):
		userdata = UserData(user=User.objects.create(username="test"))
		self.assertFalse(UserData.objects.filter(user__username="test").exists())
		userdata.save()
		self.assertTrue(UserData.objects.filter(user__username="test").exists())

class EmailNotificationTests(TestCase):
	def test_get_no_send_time(self):
		self.assertIsNone(EmailNotification.objects.create().get_send_time())

	def test_get_cruise_administration_send_time(self):
		template = EmailTemplate.objects.create(group="Cruise administration")
		notif = EmailNotification.objects.create(template=template)
		self.assertLess(notif.get_send_time(), timezone.now())

	def test_get_template_with_time_before_send_time(self):
		template = EmailTemplate.objects.create(time_before=timedelta(days=14), group="Cruise deadlines")
		event = Event.objects.create(start_time=(timezone.now() + timedelta(days=13)))
		notif = EmailNotification.objects.create(template=template, event=event)
		self.assertLess(notif.get_send_time(), timezone.now())

	def test_get_template_with_date_send_time(self):
		template = EmailTemplate.objects.create(date=(timezone.now() + timedelta(days=1)), group="Cruise departure")
		event = Event.objects.create(start_time=(timezone.now() - timedelta(days=1)))
		notif = EmailNotification.objects.create(template=template, event=event)
		self.assertGreater(notif.get_send_time(), timezone.now())

	def test_get_event_send_time(self):
		template = EmailTemplate.objects.create(group="other")
		event = Event.objects.create(start_time=(timezone.now() + timedelta(days=1)))
		notif = EmailNotification.objects.create(template=template, event=event)
		self.assertGreater(notif.get_send_time(), timezone.now())

	def test_send_time_without_info(self):
		template = EmailTemplate.objects.create(group="other")
		notif = EmailNotification.objects.create(template=template)
		self.assertLess(notif.get_send_time() - timezone.now(), timedelta(milliseconds=1))

class SeasonTests(TestCase):
	def setUp(self):
		create_no_time_season()

	def test_get_start_date_string(self):
		season = Season.objects.all()[0]
		start = timezone.now()
		season.season_event.start_time = start
		self.assertEqual(season.get_start_date_string(), str(start.date()))

	def test_get_end_date_string(self):
		season = Season.objects.all()[0]
		end = timezone.now()
		season.season_event.end_time = end
		self.assertEqual(season.get_end_date_string(), str(end.date()))

	def test_contains_time(self):
		season = Season.objects.all()[0]
		season.season_event.start_time = timezone.now() - timedelta(days=50)
		season.season_event.end_time = timezone.now() + timedelta(days=50)
		self.assertTrue(season.contains_time(timezone.now()))
		self.assertFalse(season.contains_time(timezone.now() + timedelta(days=51)))

	def test_delete(self):
		self.assertTrue(Season.objects.filter(name="test season").count() == 1)
		self.assertTrue(Event.objects.filter(name="season").count() == 1)
		self.assertTrue(Event.objects.filter(name="int order").count() == 1)
		self.assertTrue(Event.objects.filter(name="ext order").count() == 1)
		Season.objects.get(name="test season").delete()
		self.assertTrue(Season.objects.filter(name="test season").count() == 0)
		self.assertTrue(Event.objects.filter(name="season").count() == 0)
		self.assertTrue(Event.objects.filter(name="int order").count() == 0)
		self.assertTrue(Event.objects.filter(name="ext order").count() == 0)

	def test_season_is_open_date_before_start_after_end(self):
		user = User.objects.create(username="test", password="test")
		UserData.objects.create(user=user, role="internal")
		event = Season.objects.get(name="test season").season_event
		event.start_time = timezone.now() + timedelta(days=1)
		event.save()
		self.assertFalse(season_is_open(user, timezone.now()))

	def test_season_is_open_internal(self):
		user = User.objects.create(username="test", password="test")
		UserData.objects.create(user=user, role="internal")
		season_event = Season.objects.get(name="test season").season_event
		season_event.start_time = timezone.now() + timedelta(days=3)
		season_event.end_time = timezone.now() + timedelta(days=5)
		season_event.save()
		internal_order_event = Season.objects.get(name="test season").internal_order_event
		internal_order_event.start_time = timezone.now() - timedelta(days=1)
		internal_order_event.save()
		self.assertTrue(season_is_open(user, timezone.now() + timedelta(days=4)))

	def test_season_is_open_external(self):
		user = User.objects.create(username="test", password="test")
		UserData.objects.create(user=user, role="external")
		season_event = Season.objects.get(name="test season").season_event
		season_event.start_time = timezone.now() + timedelta(days=3)
		season_event.end_time = timezone.now() + timedelta(days=5)
		season_event.save()
		external_order_event = Season.objects.get(name="test season").external_order_event
		external_order_event.start_time = timezone.now() + timedelta(days=1)
		external_order_event.save()
		self.assertFalse(season_is_open(user, timezone.now() + timedelta(days=4)))

	def test_season_is_open_admin(self):
		user = User.objects.create(username="test", password="test")
		UserData.objects.create(user=user, role="admin")
