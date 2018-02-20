# Reserver
Python, Django and SQLite-based cruise reservation system

## Mockup
http://gunnerus.471.no

## ER diagram
https://drive.google.com/file/d/0B12qJja_kwUTSG9naHl1X3hiSmc/view?usp=sharing

## Structure
 - The "reserver" app is intended to encapsulate the main functionality of the reservation system. Other stuff will be placed in separate apps as appropriate during the development process.

## Installation notes
 - Requires (virtual) environment with Django, django-extra-views and django-bootstrap3
 - Typical dev setup:
      - Working directory with two folders, "env" and "gunnerus"
      - "gunnerus" folder contains this repository
      - "env" contains a virtual Python 3 environment with Django and django-bootstrap3
      - Set up using...
           - virtualenv env
           - env\Scripts\activate
           - pip install django
           - pip install django-bootstrap3==8.2.3
           - pip install apscheduler
           - pip install django-anymail
           - pip install python-dateutil
           - pip install django-easy-pdf
           - pip install django-hijack
           - pip install django-multiselectfield
           - pip install django-html_sanitizer
           - pip install pyqrcode
           - pip install pypng
      - Run using "python manage.py runserver" as usual
      - Use "deactivate" to stop using the virtual environment when you're done
      - If you run into issues with database tables not being created on the initial run of the server, use migrate --run-syncdb.
