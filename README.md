# Reserver
Python, Django and SQLite-based cruise reservation system

## Mockup
http://gunnerus.471.no

## ER diagram
https://drive.google.com/file/d/0B12qJja_kwUTSG9naHl1X3hiSmc/view?usp=sharing

## Structure
 - The "reserver" app is intended to encapsulate the main functionality of the reservation system. Other stuff will be placed in separate apps as appropriate during the development process.

## Installation notes
 - Typical dev setup:
      - Working directory with two folders, "env" and "gunnerus"
      - "gunnerus" folder contains this repository
      - "env" contains a virtual Python 3.6 environment
      - Set up using...
           - virtualenv --python=python3.6 env 
           - env\Scripts\activate
           - pip install -r requirements.txt
      - Run using "python manage.py runserver" as usual
      - Use "deactivate" to stop using the virtual environment when you're done
      - If you run into issues with database tables not being created on the initial run of the server, use migrate --run-syncdb.
 - To use the systemd config file reserver.service you need to: 
      - Update the paths to match your installation of Reserver using your favorite text editor (e.g. "nano reserver.service")
      - cp reserver.service /etc/systemd/system
      - sudo systemctl enable reserver
