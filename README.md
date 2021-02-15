# Reserver
Python, Django and SQLite-based cruise reservation system.

![Django CI](https://github.com/Gunnerus/gunnerus/workflows/Django%20CI/badge.svg?branch=master)

The `server` branch is protected from pushing, you need to [make a pull request](https://github.com/Gunnerus/gunnerus/compare/server...master) to update the server. Admins can approve their own pull requests, this is mostly a protection to prevent accidental updates of the production server and for documenting what's changed since the last update. Please include a short note with what's changed since the last server update in your pull request.

## Issues
 - [Approved Issues Board](https://github.com/Gunnerus/gunnerus/projects/1) 
   - [View as list](https://github.com/Gunnerus/gunnerus/issues?q=is%3Aissue+is%3Aopen+project%3AGunnerus%2Fgunnerus%2F1)
   - Contains issues that have been reviewed and planned for implementation. Should contain all issues that are actively being worked on, or that should be worked on soon.
 - [Pending Issues Board](https://github.com/Gunnerus/gunnerus/projects/2)
   - [View as list](https://github.com/Gunnerus/gunnerus/issues?q=is%3Aissue+is%3Aopen+project%3AGunnerus%2Fgunnerus%2F2)
   - Contains issues that have not yet been reviewed and considered approved, such as new suggestions, feature requests or ideas. Should not be worked on yet.
 - [Open issues not labeled as suggestions](https://github.com/Gunnerus/gunnerus/issues?q=is%3Aissue+is%3Aopen+-label%3Asuggestion)
 - [Current Sprint Review](https://github.com/Gunnerus/gunnerus/milestone/1) (due 2021-02-15)

## Structure
 - The "reserver" app is intended to encapsulate the main functionality of the reservation system.

## Installation notes
 - Typical dev setup:
      - Working directory with two folders, "env" and "gunnerus"
      - "gunnerus" folder contains this repository
      - "env" contains a virtual [Python 3.6](https://www.python.org/ftp/python/3.6.8/python-3.6.8-amd64.exe) environment
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
