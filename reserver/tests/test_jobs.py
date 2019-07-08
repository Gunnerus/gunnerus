import sys
import io

from contextlib import redirect_stdout

from django.test import TestCase

from reserver import jobs
from reserver.utils import init
from reserver.models import Cruise

class SchedulerTests(TestCase):
	def setUp(self):
		""" 
			Starts the scheduler and adds the default tasks (unless it's already running). 
		    We are doing this inside a try/except statement to catch the case where the 
			scheduler object hasn't been defined yet, which would raise an error when trying
			to check jobs.scheduler.running. This handles both the case where it's defined
			but not running, and the case where it's not defined at all yet.
		"""

		try:
			if not jobs.scheduler.running:
				raise Exception('Scheduler not already running')
		except:
			trap = io.StringIO()
			with redirect_stdout(trap):
				init()

	def test_default_jobs_creation(self):
		""" 
			Checks that our main jobs, daily_0800 and daily_0000, are created as expected.
		"""
		jobs_list = ""
		for job in jobs.scheduler.get_jobs():
			jobs_list += ("name: %s, trigger: %s, next run: %s, handler: %s" % (job.name, job.trigger, job.next_run_time, job.func))
		self.assertIn("daily_0800", jobs_list)
		self.assertIn("daily_0000", jobs_list)

	def test_statistics_collection(self):
		cruise_count = Cruise.objects.all().count()
		statistics = jobs.collect_statistics()
		self.assertEqual(cruise_count, statistics.cruise_count)

#	def test_send_season_email(self):
#		create_season_notifications(season)