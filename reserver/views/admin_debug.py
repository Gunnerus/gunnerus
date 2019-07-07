import json

from django.shortcuts import render
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils import timezone

from reserver.models import DebugData

def admin_debug_view(request):
	if request.user.is_superuser:
		debug_data = DebugData.objects.all()
		debug_data = debug_data[::-1]
		paginator = Paginator(debug_data, 5)
		page = request.GET.get('page')
		try:
			page_debug_data = paginator.page(page)
		except PageNotAnInteger:
			# If page is not an integer, deliver first page.
			page_debug_data = paginator.page(1)
		except EmptyPage:
			# If page is out of range (e.g. 9999), deliver last page of results.
			page_debug_data = paginator.page(paginator.num_pages)
	else:
		raise PermissionDenied

	return render(request, 'reserver/admin/admin_debug.html', {'debug_data': page_debug_data})

class StringReprJSONEncoder(json.JSONEncoder):
	def default(self, o):
		try:
			return repr(o)
		except:
			return '[unserializable]'

@csrf_exempt
def log_debug_data(request):
	if request.user.is_authenticated():
		log_data = ""
		label = ""
		try:
			json_data = json.loads(request.body.decode("utf-8"))
			log_data = json_data["log_data"]
			label = json_data["label"]
		except:
			pass
		log = DebugData()
		log.data = log_data
		log.label = label + " from user " + str(request.user)
		log.timestamp = timezone.now()
		log.request_metadata = json.dumps(request.META, cls=StringReprJSONEncoder, ensure_ascii=True)
		log.save()
	else:
		raise PermissionDenied
	return JsonResponse(json.dumps([], ensure_ascii=True), safe=False)
