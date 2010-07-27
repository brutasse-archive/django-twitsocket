from django import template
from django.conf import settings

from twitsocket.models import Tweet

register = template.Library()


@register.inclusion_tag('twitsocket/websocket.html')
def websocket_client():
    return {'websocket_server': settings.WEBSOCKET_SERVER}


@register.inclusion_tag('twitsocket/tweets.html')
def render_tweets(count):
    count = int(count)
    return {'tweets': Tweet.objects.all()[:count]}


@register.inclusion_tag('twitsocket/flash_hack.html')
def flash_hack():
    return {'MEDIA_URL': settings.MEDIA_URL}
