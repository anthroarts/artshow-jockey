import re
import csv
import io
from django.contrib.auth import get_user_model
from decimal import Decimal

from .conf import settings

User = get_user_model()


class AttributeFilter(object):
    """This creates a proxy object that will only allow
    access to the proxy if the attribute matches the
    regular expression. Otherwise,
    an AttributeError is returned."""

    def __init__(self, target, expression):
        """'target' is the object to be proxied. 'expression' is a regular expression
        (compiled or not) that will be used as the filter."""
        self.__target = target
        self.__expression = expression
        if not hasattr(self.__expression, 'match'):
            self.__expression = re.compile(self.__expression)

    def __getattr__(self, name):
        if self.__expression.match(name):
            return self.__target.__getattr__(name)
        else:
            raise AttributeError("AttributeFilter blocked access to '%s' on object '%s'" % (name, self.__target))


artshow_settings = AttributeFilter(settings, r"ARTSHOW_|SITE_NAME$|SITE_ROOT_URL$")


class UnicodeCSVWriter:
    """
    A CSV writer which will write rows to CSV file "f".
    """

    def __init__(self, f, dialect=csv.excel, **kwds):
        # Redirect output to a queue
        self.queue = io.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f

    def writerow(self, row):
        self.writer.writerow(row)
        # Fetch output from the queue ...
        data = self.queue.getvalue()
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


_quantization_value = Decimal(10) ** -settings.ARTSHOW_MONEY_PRECISION


def format_money(value):
    return str(value.quantize(_quantization_value))
