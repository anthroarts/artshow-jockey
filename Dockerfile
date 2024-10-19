FROM python:3.12-alpine AS native-deps

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code

# Install native dependencies.
RUN mkdir /data /run/nginx
RUN pip install --upgrade pip pipenv
RUN apk add --no-cache libcurl nginx
RUN apk add --no-cache --virtual .build-deps build-base curl-dev

FROM native-deps AS pipfile
COPY Pipfile Pipfile.lock /code/

# Development environment.
FROM pipfile AS dev
RUN pipenv install --system --dev

EXPOSE 8000/tcp
CMD ["/usr/local/bin/supervisord", "-c", "/code/supervisord.conf"]

COPY . /code/

ENV DEBUG=1
ENV SECRET_KEY="Secret key for development"
ENV DATABASE_URL="sqlite:///data/artshowjockey.db"

# Setup OAuth provider required for automated tests.
ENV OAUTHLIB_INSECURE_TRANSPORT=1
ENV TEST_OAUTH_PROVIDER=1

RUN flake8 && \
    python -Wa manage.py test && \
    python manage.py collectstatic

# Production environment.
FROM pipfile AS prod
RUN pipenv install --system \
 && pip uninstall -y pipenv \
 && apk del .build-deps \
 && rm -fr ~/.cache

EXPOSE 8000/tcp
CMD ["/usr/local/bin/supervisord", "-c", "/code/supervisord.conf"]

COPY . /code/

RUN DATABASE_URL="sqlite:///data/artshowjockey.db" \
    python manage.py collectstatic
