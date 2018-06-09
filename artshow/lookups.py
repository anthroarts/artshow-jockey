from ajax_select import register, LookupChannel
from .models import Bidder


@register('bidder')
class BidderLookup(LookupChannel):
    model = Bidder

    def get_query(self, q, request):
        return self.model.objects.filter(person__name__icontains=q).order_by('person__name')
