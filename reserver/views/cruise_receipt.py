import datetime
import json

from django.views.decorators.csrf import csrf_exempt

from django.http import JsonResponse

from reserver.models import get_season_containing_time, get_cruise_receipt

@csrf_exempt
def cruise_receipt_source(request):
	json_data = json.loads(request.body.decode("utf-8"))
	try:
		json_data["season"] = get_season_containing_time(datetime.datetime.strptime(json_data["dates"][0], '%Y-%m-%d').replace(hour=12))
	except:
		pass
	if request.user.is_authenticated:
		return JsonResponse(json.dumps(get_cruise_receipt(**json_data), ensure_ascii=True), safe=False)