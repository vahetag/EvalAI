FROM python:3.7.5

ENV PYTHONUNBUFFERED 1

RUN mkdir /code
WORKDIR /code

ADD requirements/* /code/
RUN pip install -r prod.txt

CMD ["./docker/wait-for-it.sh", "memcached:11211", "--","sh", "/code/docker/prod_self/django/container-start.sh"]