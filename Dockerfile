FROM python:3.7-alpine

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /code

# Install native dependencies.
RUN pip install pipenv \
 && apk add --no-cache jpeg zlib \
 && apk add --no-cache --virtual .build-deps build-base jpeg-dev python-dev zlib-dev

# Install Python dependencies and remove build-only native dependencies.
COPY Pipfile Pipfile.lock /code/
RUN pipenv install --system \
 && pip uninstall -y pipenv \
 && apk del .build-deps \
 && rm -fr ~/.cache

COPY . /code/

RUN mkdir /data
COPY local_settings.py.example /code/local_settings.py

EXPOSE 8000/tcp
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

#RUN python manage.py test \
# && rm local_settings.py
