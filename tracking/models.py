import logging
import traceback
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.gis.geoip import HAS_GEOIP
if HAS_GEOIP:
    from django.contrib.gis.geoip import GeoIP, GeoIPException
from django.db import models
from django.conf import settings
from django.contrib.auth.signals import user_logged_out
from django.db.models.signals import post_save, pre_delete
from tracking.managers import VisitorManager, PageviewManager
from tracking.settings import TRACK_USING_GEOIP, TRACK_PARSE_AGENT
from .compat import User

try:
    user_agents = None
    if TRACK_PARSE_AGENT:
        # https://github.com/selwin/python-user-agents
        import user_agents
except ImportError:
    pass

GEOIP_CACHE_TYPE = getattr(settings, 'GEOIP_CACHE_TYPE', 4)

log = logging.getLogger(__file__)

class Visitor(models.Model):
    session_key = models.CharField(max_length=40, primary_key=True)
    user = models.ForeignKey(User, related_name='visit_history',
        null=True, editable=False)
    # Update to GenericIPAddress in Django 1.4
    ip_address = models.CharField(max_length=39, editable=False)
    user_agent = models.TextField(null=True, editable=False)
    start_time = models.DateTimeField(default=timezone.now, editable=False)
    expiry_age = models.IntegerField(null=True, editable=False)
    expiry_time = models.DateTimeField(null=True, editable=False)
    time_on_site = models.IntegerField(null=True, editable=False)
    end_time = models.DateTimeField(null=True, editable=False)

    objects = VisitorManager()

    def session_expired(self):
        "The session has ended due to session expiration"
        if self.expiry_time:
            return self.expiry_time <= timezone.now()
        return False
    session_expired.boolean = True

    def session_ended(self):
        "The session has ended due to an explicit logout"
        return bool(self.end_time)
    session_ended.boolean = True

    @property
    def last_time(self):
        "datetime of last time visited - start_time + time_on_site"
        return self.start_time + timedelta(seconds=self.time_on_site)

    @property
    def geoip_data(self):
        "Attempts to retrieve MaxMind GeoIP data based upon the visitor's IP"
        if not HAS_GEOIP or not TRACK_USING_GEOIP:
            return

        if not hasattr(self, '_geoip_data'):
            self._geoip_data = None
            try:
                gip = GeoIP(cache=GEOIP_CACHE_TYPE)
                self._geoip_data = gip.city(self.ip_address)
            except GeoIPException:
                log.error('Error getting GeoIP data for IP "%s": %s' % (self.ip_address, traceback.format_exc()))

        return self._geoip_data

    @property
    def platform(self):
        """
        Returns string describing browser platform. Falls back to agent
        string if either user_agents module not found, or
        TRACK_PARSE_AGENT is False
        """
        if not user_agents:
            return self.user_agent

        if not hasattr(self, '_platform_string'):
            platform = user_agents.parse(self.user_agent)
            self._platform_string = ("%s %d %s %s " %
                                     (platform.browser.family,
                                      platform.browser.version[0],
                                      platform.os.family,
                                      platform.os.version_string))
            if platform.device.family:
                self._platform_string += platform.device.family

        return self._platform_string

    class Meta(object):
        ordering = ('-start_time',)
        permissions = (
            ('view_visitor', 'Can view visitor'),
        )


class Pageview(models.Model):
    visitor = models.ForeignKey(Visitor, related_name='pageviews')
    url = models.CharField(max_length=500)
    method = models.CharField(max_length=20, null=True)
    view_time = models.DateTimeField()

    objects = PageviewManager()

    class Meta(object):
        ordering = ('-view_time',)


from tracking import handlers
user_logged_out.connect(handlers.track_ended_session)
post_save.connect(handlers.post_save_cache, sender=Visitor)
