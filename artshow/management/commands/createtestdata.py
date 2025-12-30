from django.core.management.base import BaseCommand

from artshow import testdata


class Command(BaseCommand):
    help = "Fills the database with fake artists, pieces, bidders and bids"

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            type=str,
            help="Email address for users")
        parser.add_argument(
            "--voice-auction",
            action="store_true",
            help="Add voice auction bids")

    def handle(self, *args, **options):
        if options['email']:
            testdata.create(options['email'])
            self.stdout.write(self.style.SUCCESS("Created test data."))
        if options['voice_auction']:
            testdata.voice_auction()
            self.stdout.write(self.style.SUCCESS("Completed voice auction."))
