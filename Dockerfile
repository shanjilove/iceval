FROM python:3.10

ENV PYTHONUNBUFFERED 1
ENV ENV=local

RUN mkdir /code
WORKDIR /code

COPY requirements.txt /code/
RUN pip install uwsgi

RUN apt-get update && apt-get install -y nginx
RUN apt-get update && apt-get install -y supervisor
RUN pip install -r requirements.txt

RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev

ENV GDAL_LIBRARY_PATH=/usr/lib/libgdal.so

RUN apt-get update && apt-get install -y postgresql postgresql-contrib

COPY ./postgresql/pg_hba.conf /etc/postgresql/pg_hba.conf
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

RUN mkdir -p /var/log/supervisor

COPY . /code/

CMD supervisord -c /etc/supervisor/conf.d/supervisord.conf