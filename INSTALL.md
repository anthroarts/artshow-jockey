Installation Steps
==================

<i>Note: These steps are incomplete. I am taking notes on the configuration process as I go.</i>

1. Install dependencies:

```
pip install -r requirements.txt
```

2. Copy `local_settings.py.example` to `local_settings.py` and modify as needed.

<i>TODO: Document important configuration variables.</i>

3. Create the database:

```
./manage.py migrate
```

4. Load fixtures:

```
./manage.py loaddata artshowemailsignature.json
./manage.py loaddata artshowemailtemplate.json
./manage.py loaddata artshowpaymenttypes.json
./manage.py loaddata artshowspaces.json
```

5. Create the superuser account:

```
./manage.py createsuperuser
```

6. Prepare static resources:

```
./manage.py collectstatic
```

7. Log into the admin interface (`/admin`) and configure email signatures, email templates and sites with information specific to your event.
