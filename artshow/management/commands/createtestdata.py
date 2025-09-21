from django.core.management.base import BaseCommand

from artshow import testdata


class Command(BaseCommand):
    help = "Fills the database with fake artists, pieces, bidders and bids"

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            type=str,
            required=True,
            help="Email address for users")

    def handle(self, *args, **options):
        testdata.create(options['email'])
