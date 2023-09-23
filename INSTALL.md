Installation Steps
==================

<i>Note: These steps are incomplete. I am taking notes on the configuration process as I go.</i>

1. Install dependencies:

```
pip install -r requirements.txt
```

2. Modify `artshowjockey/settings.py` as needed.

| Config Variable              | Description |
| ---------------------------- | ----------- |
| ARTSHOW_SHOW_NAME            | Name of the show |
| ARTSHOW_TAX_RATE             | Tax rate to collect on auction sales |
| ARTSHOW_TAX_DESCRIPTION      | Description of the tax collected on auction sales |
| ARTSHOW_EMAIL_SENDER         | Sender address for outgoing mail |
| ARTSHOW_EMAIL_FOOTER         | Footer on outgoing mail |
| SITE_ROOT_URL                | Canonical URL for the site |
| ARTSHOW_ARTIST_AGREEMENT_URL | Link to artist agreement page |
| SECRET_KEY                   | Random string used to encrypt session data |
| RECAPTCHA_PUBLIC_KEY         | reCAPTCHA public API key |
| RECAPTCHA_PRIVATE_KEY        | reCAPTCHA private API key |

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
