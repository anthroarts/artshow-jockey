"""List of all Artshow Jockey settings. Those that can have reasonable
defaults have their defaults set here. Those that must be overridden
have been set to the _UNCONFIGURED object, which will be checked during
startup of the artshow application. _DISABLED is to leave a non-critical
feature disabled"""

_UNCONFIGURED = object()
_DISABLED = object()

# These are the "PaymentType" IDs used by various procedures
# These must match the PaymentTypes loaded by the fixtures
ARTSHOW_SPACE_FEE_PK = 3
ARTSHOW_PAYMENT_SENT_PK = 5
ARTSHOW_PAYMENT_RECEIVED_PK = 1
ARTSHOW_PAYMENT_PENDING_PK = 9
ARTSHOW_COMMISSION_PK = 6
ARTSHOW_SALES_PK = 7

# name of the model handling people, in "app.model" format
ARTSHOW_PERSON_CLASS = "peeps.Person"

# name of the module used to print forms, in python path format
ARTSHOW_PREPRINT_MODULE = "artshow.preprint_dummy"

ARTSHOW_SHOW_NAME = "Generic Art Show"
ARTSHOW_SHOW_YEAR = "1999"
ARTSHOW_TAX_RATE = "0.10"  # Used to initialise a Decimal object
ARTSHOW_TAX_DESCRIPTION = "Fictitious County 10% Tax"
ARTSHOW_EMAIL_SENDER = "Generic Art Show <artshow@example.com>"
ARTSHOW_COMMISSION = "0.1" # Used to initialise a Decimal object
ARTSHOW_INVOICE_PREFIX = "1999-" # Prefixed on all printed invoices
ARTSHOW_EMAIL_FOOTER = """\
--
Random J Hacker
Generic Art Show Lead.
artshow@example.com - http://www.example.com/artshow
"""
ARTSHOW_PASSWORD_RESET_TEMPLATE = "artshow/manage_password_reset.txt"
ARTSHOW_PASSWORD_RESET_SUBJECT = "Your Art Show Management Account"
ARTSHOW_CHEQUE_THANK_YOU = "Thank you for exhibiting at Generic Art Show"
ARTSHOW_BLANK_BID_SHEET = "artshow/files/BidSheet.pdf"
ARTSHOW_BLANK_CONTROL_FORM = "artshow/files/ControlForm.pdf"

# The in-build form printing code uses this font to print piece barcodes.
# Specify as a 2-tuple: ( "font name", "font path" )
ARTSHOW_BARCODE_FONT = ('Free3of9', 'artshow/files/free3of9/FREE3OF9.TTF')

# device name of serial-connected scanner reader.
# eg: "/dev/ttyUSB0"
ARTSHOW_SCANNER_DEVICE = _DISABLED

# Set this to "True" to display allocated spaces to logged-in artists
ARTSHOW_SHOW_ALLOCATED_SPACES = False

# Set this to "True" to prevent all standard logins from making edits to
# piece details. Best used when this database is no longer the "master".
ARTSHOW_SHUT_USER_EDITS = False

# Command to send a text file to the printer.
# Eg: "enscript -q -P myprinter -DProcessColorModel:/DeviceGray -B -L 66 -f Courier-Bold10"
ARTSHOW_PRINT_COMMAND = _DISABLED
ARTSHOW_AUTOPRINT_INVOICE = ["CUSTOMER COPY", "MERCHANT COPY", "PICK LIST"]
ARTSHOW_MONEY_PRECISION = 2
ARTSHOW_MONEY_CURRENCY = "USD"

# Set this if something has gone wrong, and registration IDs should no longer
# be checked for uniqueness
ARTSHOW_REGID_NONUNIQUE = False

# Disallow piece IDs greater than
ARTSHOW_MAX_PIECE_ID = 999

# URL To the paypal standard payments API. Don't put a trailing comma or questionmark.
ARTSHOW_PAYPAL_URL = "https://www.paypal.com/cgi-bin/webscr"

ARTSHOW_PAYPAL_ACCOUNT = _UNCONFIGURED

ARTSHOW_ARTIST_AGREEMENT_URL = _UNCONFIGURED

# Change this if an offset has been applied to bidder ID MOD11 calculation.
# Use "None" to disable check completely.
ARTSHOW_BIDDERID_MOD11_OFFSET = 0