from django import template
from django.conf import settings

from twitsocket.models import Tweet, Top, Flooder

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


@register.inclusion_tag('twitsocket/top_tweets.html')
def top_tweets(count):
    count = int(count)
    return {'top_tweets': Top.objects.all()[:count]}


@register.inclusion_tag('twitsocket/top_users.html')
def top_users(count):
    count = int(count)
    return {'top_users': Flooder.objects.all()[:count]}


@register.inclusion_tag('twitsocket/count.html')
def count():
    return {'count': Tweet.objects.count()}
