from django import template
import pyqrcode
import io
import base64
from django.urls import reverse_lazy

register = template.Library()

@register.simple_tag
def path_to_b64_qr_url(path):
	b64_path = base64.b64encode(bytes(str(path), 'utf-8'))
	print(reverse_lazy('path-to-qr', kwargs={'b64_path': str(b64_path, "utf-8 ")}))
	return reverse_lazy('path-to-qr', kwargs={'b64_path': str(b64_path, "utf-8 ")})
	
@register.simple_tag
def path_to_b64_qr(path, http_host_string):
	qr = pyqrcode.create(http_host_string+path)
	buffer = io.BytesIO()
	qr.png(buffer, scale=15)
	encoded_qr = base64.b64encode(buffer.getvalue())
	return "data:image/png;base64,"+str(encoded_qr, "utf-8")
	
@register.simple_tag
def subtract(value, arg):
    return value - arg