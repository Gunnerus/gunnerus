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
		season_event = Season.objects.get(name="test season").season_event
		season_event.start_time = timezone.now() + timedelta(days=3)
		season_event.end_time = timezone.now() + timedelta(days=5)
		season_event.save()
		self.assertTrue(season_is_open(user, timezone.now() + timedelta(days=4)))

	def test_get_season_containing_time(self):
		season_event = Season.objects.all()[0].season_event
		season_event.start_time = timezone.now() - timedelta(days=1)
		season_event.end_time = timezone.now() + timedelta(days=1)
		season_event.save()
		self.assertEqual(get_season_containing_time(timezone.now()), Season.objects.all()[0])
		self.assertNotEqual(get_season_containing_time(timezone.now() + timedelta(days=2)), Season.objects.all()[0])

	def test_time_is_in_season(self):
		season_event = Season.objects.all()[0].season_event
		season_event.start_time = timezone.now() - timedelta(days=1)
		season_event.end_time = timezone.now() + timedelta(days=1)
		season_event.save()
		self.assertTrue(time_is_in_season(timezone.now()))
		self.assertFalse(time_is_in_season(timezone.now() + timedelta(days=2)))

class CruiseTests(TestCase):
	def test_is_viewable_by_user_in_internal_org(self):
		org = Organization.objects.create(name="test", is_NTNU=True)
		user = User.objects.create(username="test", password="test")
		userdata = UserData.objects.create(user=user, role="internal", organization=org)
		leader = User.objects.create(username="leader", password="leader")
		cruise = Cruise.objects.create(leader=leader, organization=org)
		self.assertTrue(cruise.is_viewable_by(user))

	def test_is_viewable_by_user_in_another_internal_org(self):
		org1 = Organization.objects.create(name="one", is_NTNU=True)
		org2 = Organization.objects.create(name="two", is_NTNU=True)
		user = User.objects.create(username="test", password="test")
		userdata = UserData.objects.create(user=user, role="internal", organization=org1)
		leader = User.objects.create(username="leader", password="leader")
		cruise = Cruise.objects.create(leader=leader, organization=org2)
		self.assertTrue(cruise.is_viewable_by(user))

	def test_is_viewable_by_user_in_external_org(self):
		org = Organization.objects.create(name="test", is_NTNU=False)
		user = User.objects.create(username="test", password="test")
		userdata = UserData.objects.create(user=user, role="external", organization=org)
		leader = User.objects.create(username="leader", password="leader")
		cruise = Cruise.objects.create(leader=leader, organization=org)
		self.assertTrue(cruise.is_viewable_by(user))

	def test_is_viewable_by_user_in_another_external_org(self):
		org1 = Organization.objects.create(name="one", is_NTNU=False)
		org2 = Organization.objects.create(name="two", is_NTNU=False)
		user = User.objects.create(username="test", password="test")
		userdata = UserData.objects.create(user=user, role="external", organization=org1)
		leader = User.objects.create(username="leader", password="leader")
		cruise = Cruise.objects.create(leader=leader, organization=org2)
		self.assertFalse(cruise.is_viewable_by(user))

	def test_external_cruise_is_viewable_by_internal_user(self):
		org1 = Organization.objects.create(name="one", is_NTNU=True)
		org2 = Organization.objects.create(name="two", is_NTNU=False)
		user = User.objects.create(username="test", password="test")
		userdata = UserData.objects.create(user=user, role="internal", organization=org1)
		leader = User.objects.create(username="leader", password="leader")
		cruise = Cruise.objects.create(leader=leader, organization=org2)
		self.assertFalse(cruise.is_viewable_by(user))

	def test_is_viewable_by_admin(self):
		org1 = Organization.objects.create(name="one", is_NTNU=True)
		org2 = Organization.objects.create(name="two", is_NTNU=False)
		user = User.objects.create(username="test", password="test")
		userdata = UserData.objects.create(user=user, role="admin", organization=org1)
		leader = User.objects.create(username="leader", password="leader")
		cruise = Cruise.objects.create(leader=leader, organization=org2)
		self.assertTrue(cruise.is_viewable_by(user))

	def test_is_viewable_by_leader(self):
		org1 = Organization.objects.create(name="one", is_NTNU=False)
		org2 = Organization.objects.create(name="two", is_NTNU=True)
		user = User.objects.create(username="test", password="test")
		userdata = UserData.objects.create(user=user, role="external", organization=org1)
		cruise = Cruise.objects.create(leader=user, organization=org2)
		self.assertTrue(cruise.is_viewable_by(user))

	def test_is_viewable_by_owner(self):
		org1 = Organization.objects.create(name="one", is_NTNU=False)
		org2 = Organization.objects.create(name="two", is_NTNU=True)
		user = User.objects.create(username="test", password="test")
		userdata = UserData.objects.create(user=user, role="external", organization=org1)
		leader = User.objects.create(username="leader", password="leader")
		cruise = Cruise.objects.create(leader=leader, organization=org2)
		cruise.owner.add(user)
		self.assertTrue(cruise.is_viewable_by(user))

	def test_get_owners_minus_leader(self):
		user = User.objects.create(username="test", password="test")
		userdata = UserData.objects.create(user=user, role="external")
		leader = User.objects.create(username="leader", password="leader")
		cruise = Cruise.objects.create(leader=leader)
		cruise.owner.add(user)
		self.assertEqual(list(cruise.get_owners_minus_leader()), [user])

	def test_is_editable_cancellable_by_leader(self):
		leader = User.objects.create(username="leader", password="leader")
		cruise = Cruise.objects.create(leader=leader, is_approved=True, cruise_start=timezone.now() + timedelta(minutes=1))
		self.assertTrue(cruise.is_editable_by(leader) and cruise.is_cancellable_by(leader))

	def test_is_editable_cancellable_by_owner(self):
		user = User.objects.create(username="test", password="test")
		userdata = UserData.objects.create(user=user, role="external")
		leader = User.objects.create(username="leader", password="leader")
		cruise = Cruise.objects.create(leader=leader, is_approved=True, cruise_start=timezone.now() + timedelta(minutes=1))
		cruise.owner.add(user)
		self.assertTrue(cruise.is_editable_by(user) and cruise.is_cancellable_by(user))

	def test_get_cruise_days(self):
		leader = User.objects.create(username="leader", password="leader")
		cruise1 = Cruise.objects.create(leader=leader)
		cruise2 = Cruise.objects.create(leader=leader)
		day1 = CruiseDay.objects.create(cruise=cruise1)
		day2 = CruiseDay.objects.create(cruise=cruise2)
		day3 = CruiseDay.objects.create(cruise=cruise1)
		self.assertEqual(list(cruise1.get_cruise_days()), [day1, day3])

	def test_get_cruise_equipment(self):
		leader = User.objects.create(username="leader", password="leader")
		cruise1 = Cruise.objects.create(leader=leader)
		cruise2 = Cruise.objects.create(leader=leader)
		equip1 = Equipment.objects.create(cruise=cruise1)
		equip2 = Equipment.objects.create(cruise=cruise2)
		equip3 = Equipment.objects.create(cruise=cruise1)
		self.assertEqual(list(cruise1.get_cruise_equipment()), [equip1, equip3])

	def test_get_cruise_documents(self):
		leader = User.objects.create(username="leader", password="leader")
		cruise1 = Cruise.objects.create(leader=leader)
		cruise2 = Cruise.objects.create(leader=leader)
		doc1 = Document.objects.create(cruise=cruise1)
		doc2 = Document.objects.create(cruise=cruise2)
		doc3 = Document.objects.create(cruise=cruise1)
		self.assertEqual(list(cruise1.get_cruise_documents()), [doc1, doc3])

	def test_get_billing_type(self):
		# TODO: test different combinations
		pass

	def test_get_contact_emails(self):
		leader = User.objects.create(username="leader", password="leader", email="test")
		cruise = Cruise.objects.create(leader=leader)
		self.assertEqual(cruise.get_contact_emails(), "test")

	def test_get_cruise_sum(self):
		leader = User.objects.create(username="leader", password="leader", email="test")
		cruise = Cruise.objects.create(leader=leader, billing_type="research")
		create_no_time_season()
		season = Season.objects.all()[0]
		season.short_research_price = 1000
		season.long_research_price = 1500
		season.breakfast_price = 10
		season.lunch_price = 15
		season.dinner_price = 20
		season.save()
		CruiseDay.objects.create(
			cruise=cruise, season=season, is_long_day=True,
			breakfast_count=0, lunch_count=5, dinner_count=5)
		CruiseDay.objects.create(
			cruise=cruise, season=season, is_long_day=False,
			breakfast_count=5, lunch_count=5, dinner_count=0)
		self.assertEqual(float(cruise.get_cruise_sum()), (1500 + 1000 + (5*10) + (10*15) + (5*20)))

	def test_get_missing_cruise_information(self):
		leader = User.objects.create(username="test", password="test")
		userdata = UserData.objects.create(user=leader, role="internal")
		cruise = Cruise.objects.create(leader=leader, billing_type="education")
		cruise.missing_information_cache_outdated = True
		create_no_time_season()
		season = Season.objects.all()[0]
		season.season_event.start_time = timezone.now()
		season.season_event.end_time = timezone.now() + timedelta(days=50)
		season.internal_order_event.start_time = timezone.now() - timedelta(days=50)
		season.external_order_event.start_time = timezone.now() - timedelta(days=50)
		season.season_event.save()
		season.internal_order_event.save()
		season.external_order_event.save()
		season.save()
		CruiseDay.objects.create(
			cruise=cruise, season=season, destination="Test destination",
			event=Event.objects.create(
				start_time=(timezone.now() + timedelta(days=15)),
				end_time=(timezone.now() + timedelta(days=15, hours=8))
			)
		)
		cruise.number_of_participants = 5
		cruise.terms_accepted = True
		cruise.description = "Test description"
		cruise.save()
		missing_info = cruise.get_missing_information_list()
		for item in missing_info:
			print(item)
