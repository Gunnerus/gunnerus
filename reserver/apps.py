from django.apps import AppConfig


class ReserverConfig(AppConfig):
	name = 'reserver'

#	def ready(self):
#		from reserver import jobs
#		jobs.main()