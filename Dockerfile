FROM python:3.7-alpine as build

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /code

# Install native dependencies.
RUN pip install pipenv \
 && apk add --no-cache jpeg zlib \
 && apk add --no-cache --virtual .build-deps build-base jpeg-dev python-dev zlib-dev

COPY Pipfile Pipfile.lock /code/
RUN pipenv install --system

COPY . /code/

RUN mkdir /data
COPY local_settings.py.example /code/local_settings.py

EXPOSE 8000/tcp
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

FROM build as test
RUN python manage.py test

FROM build as prod
RUN pip uninstall -y pipenv \
 && apk del .build-deps \
 && rm -fr ~/.cache
