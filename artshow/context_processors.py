from .utils import artshow_settings as _artshow_settings


def artshow_settings(request):
    return {'artshow_settings': _artshow_settings}
