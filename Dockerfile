FROM python:3.10-alpine AS native-deps

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /code

# Install native dependencies.
RUN mkdir /data /run/nginx \
 && pip install --upgrade pip pipenv \
 && apk add --no-cache jpeg libcurl libpq nginx zlib \
 && apk add --no-cache --virtual .build-deps build-base curl-dev jpeg-dev postgresql-dev zlib-dev

FROM native-deps AS pipfile
COPY Pipfile Pipfile.lock /code/

# Development environment.
FROM pipfile AS dev
RUN pipenv install --system --dev

EXPOSE 8000/tcp
CMD ["/usr/local/bin/supervisord", "-c", "/code/supervisord.conf"]

COPY . /code/

RUN flake8 && python manage.py test && python manage.py collectstatic

# Production environment.
FROM pipfile AS prod
RUN pipenv install --system \
 && pip uninstall -y pipenv \
 && apk del .build-deps \
 && rm -fr ~/.cache

EXPOSE 8000/tcp
CMD ["/usr/local/bin/supervisord", "-c", "/code/supervisord.conf"]

COPY . /code/

RUN python manage.py collectstatic
