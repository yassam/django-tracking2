from django.conf import settings

TRACK_PAGEVIEWS = getattr(settings, 'TRACK_PAGEVIEWS', False)
TRACK_AJAX_REQUESTS = getattr(settings, 'TRACK_AJAX_REQUESTS', False)
TRACK_ANONYMOUS_USERS = getattr(settings, 'TRACK_ANONYMOUS_USERS', True)
TRACK_USING_GEOIP = getattr(settings, 'TRACK_USING_GEOIP', False)
if hasattr(settings, 'TRACKING_USE_GEOIP'):
    raise DeprecationWarning('TRACKING_USE_GEOIP has been renamed to TRACK_USING_GEOIP')
