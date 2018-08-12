import logging
import uuid

import squareconnect
from squareconnect.rest import ApiException
from squareconnect.apis.transactions_api import TransactionsApi
from squareconnect.apis.locations_api import LocationsApi

from .conf import settings

logger = logging.getLogger(__name__)

squareconnect.configuration.access_token = settings.ARTSHOW_SQUARE_ACCESS_TOKEN
location_id = settings.ARTSHOW_SQUARE_LOCATION_ID

def charge(payment, nonce):
    api_instance = TransactionsApi()
    idempotency_key = str(uuid.uuid1())
    body = {
        'idempotency_key': idempotency_key,
        'card_nonce': nonce,
        'amount_money': {
            'amount': int(payment.amount * 100),
            'currency': 'USD'
        },
    }
    try:
        api_response = api_instance.charge(location_id, body)
        logger.debug('Square charge successful: %s' % api_response.transaction)
        return api_response.transaction.id
    except ApiException:
        logger.exception('Exception when charging through Square')
        return None
