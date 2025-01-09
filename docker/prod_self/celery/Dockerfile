FROM python:3.7.5

ENV PYTHONUNBUFFERED 1

RUN apt-get update
RUN mkdir /code
WORKDIR /code

ADD requirements/* /code/

RUN pip install -r prod.txt

CMD ["./docker/wait-for-it.sh", "django:8000", "--", "sh", "/code/docker/prod_self/celery/container-start.sh"]
