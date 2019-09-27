@echo off
del db.sqlite3
del celerybeat.pid
del regression\migrations\0*.py
del report\*
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser --username admin --email i@hsury.com
start_all.bat