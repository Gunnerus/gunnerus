import os, tempfile, zipfile

from wsgiref.util import FileWrapper

from django.http import HttpResponse
from django.utils import timezone
from django.conf import settings

def backup_view(request):
	"""
	Create a ZIP file on disk and transmit it in chunks of 8KB,
	without loading the whole file into memory. A similar approach can
	be used for large dynamic PDF files.
	"""
	temp = tempfile.TemporaryFile()
	archive = zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED)
	archive.write(settings.DATABASES["default"]["NAME"], 'db.sqlite3')
	for filename in os.listdir(settings.MEDIA_ROOT):
		filepath = os.path.join(settings.MEDIA_ROOT, filename)
		if os.path.isdir(filepath):
			# skip directories
			continue
		archive.write(filepath, "uploads\\"+filename)
	for filename in os.listdir(os.path.join(settings.BASE_DIR, "reserver/migrations")):
		filepath = os.path.join(os.path.join(settings.BASE_DIR, "reserver/migrations"), filename)
		if os.path.isdir(filepath):
			# skip directories
			continue
		archive.write(filepath, "migrations\\"+filename)
	archive.close()
	length = temp.tell()
	wrapper = FileWrapper(temp)
	temp.seek(0)
	response = HttpResponse(wrapper, content_type='application/zip')
	response['Content-Disposition'] = 'attachment; filename=reserver-backup-'+timezone.now().strftime('%Y-%m-%d-%H%M%S')+'.zip'
	response['Content-Length'] = length
	return response
