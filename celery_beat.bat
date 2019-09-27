@echo off
del celerybeat.pid
celery -A pango beat -l info