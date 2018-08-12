#!/bin/bash

if [ "$1" == "" ]; then
  echo "First parameter must be the supervisord job name."
  exit 1
fi

# Fetch the latest from git
git pull

# Sync installed packages to Pipfile.lock.
pipenv install --system

# Apply the latest database migrations
./manage.py migrate

# Update /static
./manage.py collectstatic --noinput

# Trigger a reload of the application
sudo supervisorctl restart "$1"
