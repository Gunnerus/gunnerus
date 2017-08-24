from django.apps import AppConfig
from reserver.utils import check_for_and_fix_users_without_userdata, check_default_models

class ReserverConfig(AppConfig):
	name = 'reserver'

	#def ready(self):
	#	from reserver import jobs
	#	jobs.main()