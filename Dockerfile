FROM python:3.7-alpine as build

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /code

# Install native dependencies.
RUN pip install gunicorn pipenv \
 && apk add --no-cache jpeg nginx supervisor zlib \
 && apk add --no-cache --virtual .build-deps build-base jpeg-dev python-dev zlib-dev

COPY Pipfile Pipfile.lock /code/
RUN pipenv install --system

COPY . /code/

RUN mkdir /data \
 && mkdir /run/nginx \
 && python manage.py collectstatic

EXPOSE 80/tcp
CMD ["/usr/bin/supervisord", "-c", "/code/supervisord.conf"]

FROM build as test
RUN python manage.py test

FROM build as prod
RUN pip uninstall -y pipenv \
 && apk del .build-deps \
 && rm -fr ~/.cache
