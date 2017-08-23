#!/bin/sh

# Fetch the latest from git
git pull

# Apply the latest database migrations
./manage.py migrate

# Update /static
./manage.py collectstatic

# Trigger a reload of the application
touch artshowjockey/wsgi.py
