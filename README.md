# Reserver
Python, Django and SQLite-based cruise reservation system

## Mockup
http://gunnerus.471.no

## ER diagram
https://drive.google.com/file/d/0B12qJja_kwUTSG9naHl1X3hiSmc/view?usp=sharing

## Structure
 - The "reserver" app is intended to encapsulate the main functionality of the reservation system. Other stuff will be placed in separate apps as appropriate during the development process.

## Installation notes
 - Requires (virtual) environment with Django and django-bootstrap3
 - Typical dev setup:
      - Working directory with two folders, "env" and "reserver"
      - "reserver" folder contains this repository
      - "env" contains a virtual Python 3 environment with Django and django-bootstrap3
      - Set up using...
           - virtualenv env
           - env\Scripts\activate
           - pip install django
           - pip install django-bootstrap3
      - Run using "python manage.py runserver" as usual
      - Use "deactivate" to stop using the virtual environment when you're done
      - Current superuser login details are "admin" and "test1234". Exciting, I know.
