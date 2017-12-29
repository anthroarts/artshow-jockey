from django.core.management.base import BaseCommand
from ...mod11codes import make_check
from ...models import BidderId
from ...conf import settings


class Command(BaseCommand):
    help = "Generate a list of valid BidderID codes"

    def add_arguments(self, parser):
        parser.add_argument("--digits", type=int, default=3,
                            help="pad to this many digits [%default]"),
        parser.add_argument("--allow-x", action="store_true", default=False,
                            help="allow X checkdigit"),
        parser.add_argument("--prefix", type=str, default="",
                            help="prefix characters [%default]"),
        parser.add_argument("--suffix", type=str, default="",
                            help="suffix characters [%default]"),
        parser.add_argument("--offset", type=int,
                            default=settings.ARTSHOW_BIDDERID_MOD11_OFFSET or 0,
                            help="offset checkdigit [%default]"),

    def handle(self, *args, **options):
        value = 1
        digits = options['digits']
        allow_x = options['allow_x']
        prefix = options['prefix']
        suffix = options['suffix']
        offset = options['offset']

        unused_codes = BidderId.objects.filter(bidder__isnull=True).count()
        while unused_codes < 100:
            code = '%0*d' % (digits, value)
            value += 1
            check = make_check(code, offset=offset)
            if check == 'X' and not allow_x:
                continue
            result = code + check

            if not BidderId.objects.filter(id=result).exists():
                bidder_id = BidderId(id=result)
                bidder_id.save()
                unused_codes += 1
