#!/bin/sh
# ! Run the following line manually in case of database model changes.
# python manage.py makemigrations --noinput  && \
python manage.py migrate --noinput  && \
python manage.py collectstatic --noinput  && \
# python manage.py seed && \
uwsgi --ini /code/docker/prod_self/django/uwsgi.ini
