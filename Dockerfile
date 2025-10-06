FROM python:3.13-slim-trixie AS native-deps

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_NO_MANAGED_PYTHON=1
ENV UV_PROJECT_ENVIRONMENT=/venv
ENV PGSSLCERT=/tmp/postgresql.crt

WORKDIR /code

# Install native dependencies.
RUN apt update
RUN apt install -y nginx
RUN mkdir /data

# Development environment.
FROM native-deps AS dev

COPY pyproject.toml uv.lock /code/
RUN uv sync

COPY . /code/

ENV DEBUG=1
ENV SECRET_KEY="Secret key for development"
ENV DATABASE_URL="sqlite:///data/artshowjockey.db"

# Setup OAuth provider required for automated tests.
ENV OAUTHLIB_INSECURE_TRANSPORT=1
ENV TEST_OAUTH_PROVIDER=1

RUN uv run flake8 && \
    uv run -- python -Wa manage.py test && \
    uv run manage.py collectstatic

EXPOSE 8000/tcp
CMD ["/venv/bin/supervisord", "-c", "/code/supervisord.conf"]

# Production environment.
FROM native-deps AS prod

ENV UV_NO_DEV=1

COPY pyproject.toml uv.lock /code/
RUN uv sync

COPY . /code/
RUN DATABASE_URL="sqlite:///data/artshowjockey.db" \
    uv run manage.py collectstatic

EXPOSE 8000/tcp
CMD ["/venv/bin/supervisord", "-c", "/code/supervisord.conf"]
