from django.core.management.base import BaseCommand
from ...mod11codes import make_check
from ...models import BidderId
from ...conf import settings


class Command(BaseCommand):
    help = "Generate a list of valid BidderID codes"

    def add_arguments(self, parser):
        parser.add_argument("num_ids", metavar='N', type=int, nargs=1,
                            help="create up to N unused bidder ids")
        parser.add_argument("--digits", type=int, default=3,
                            help="pad to this many digits"),
        parser.add_argument("--allow-x", action="store_true", default=False,
                            help="allow X checkdigit"),
        parser.add_argument("--offset", type=int,
                            default=settings.ARTSHOW_BIDDERID_MOD11_OFFSET or 0,
                            help="offset checkdigit"),

    def handle(self, *args, **options):
        value = 1
        num_ids = options['num_ids'][0]
        digits = options['digits']
        allow_x = options['allow_x']
        offset = options['offset']

        unused_codes = BidderId.objects.filter(bidder__isnull=True).count()
        while unused_codes < num_ids:
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
