from optparse import make_option
import select

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils.timezone import now

from ...models import BatchScan


class Command(BaseCommand):
    args = ''
    help = "Monitor connected scanner"

    option_list = BaseCommand.option_list + (
        make_option("--device", type="string", action="append", default=settings.ARTSHOW_SCANNER_DEVICE,
                    help="scanner device name [%default]"),
    )

    def handle(self, *args, **options):
        device = options['device']
        # TODO find out why buffering=0 (no buffering) is required.
        f = open(device, buffering=0)

        while True:
            data = []
            print("waiting for new data")
            line = f.readline()
            print("\a")
            while True:
                if not line:
                    print("oops. no data to read. wtf?")
                line = line.strip()
                if line:
                    data.append(line)
                print(line)
                rlist, wlist, xlist = select.select([f], [], [f], 5.0)
                if not rlist and not xlist:
                    break
                line = f.readline()
            print("timed out")
            print("\a")
            data_str = "\n".join(data) + "\n"
            batchscan = BatchScan(data=data_str, date_scanned=now())
            batchscan.save()
            print(str(batchscan), "saved")
