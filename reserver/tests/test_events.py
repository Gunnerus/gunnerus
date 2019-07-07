from django.test import TestCase
from reserver.models import Event

class EventModelTests(TestCase):
	def test_event_creation(self):
		"""
		Check that events can be created
		"""
		name = "Test event"
		event = Event(name=name)
		self.assertIs(event.name, name)