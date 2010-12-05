import urllib2
import urllib
import time

from django.conf import settings
from django.core.management.base import NoArgsCommand
from django.utils import simplejson as json

import oauth2 as oauth

from twitsocket.models import Tweet

LIST_MEMBERS = 'https://api.twitter.com/1/%s/members.json' % settings.TWITTER_LIST

def oauth_request(url, method='GET', params={}, data=None):
    qs = ''
    if method == 'GET':
        qs = '&'.join(['%s=%s' % (key, value) for key, value in params.items()])
    if qs:
        url += '?%s' % qs
    consumer = oauth.Consumer(secret=settings.CONSUMER_SECRET,
                              key=settings.CONSUMER_KEY)
    token = oauth.Token(secret=settings.TOKEN_SECRET,
                        key=settings.TOKEN_KEY)
    oparams = {
        'oauth_version': '1.0',
        'oauth_nonce': oauth.generate_nonce(),
        'oauth_timestamp': int(time.time()),
        'oauth_token': token.key,
        'oauth_consumer_key': consumer.key,
    }
    if method == 'POST':
        oparams.update(params)
    req = oauth.Request(method=method, url=url, parameters=oparams)
    signature_method = oauth.SignatureMethod_HMAC_SHA1()
    req.sign_request(signature_method, consumer, token)
    if method == 'POST':
        return urllib2.Request(url, data, headers=req.to_header())
    return urllib2.Request(url, headers=req.to_header())


class Command(NoArgsCommand):
    """Adds all the twitter users to the list"""

    def handle_noargs(self, **options):
        members = self.get_list_members()
        users = self.get_users(Tweet.objects.all())
        for u in users:
            if u not in members:
                print "Adding %s to list" % u
                self.add_to_list(u)
                time.sleep(1)

    def get_list_members(self):
        more_pages = True
        members = []
        cursor = -1
        while more_pages:
            request = oauth_request(LIST_MEMBERS, params={'cursor': cursor})
            data = urllib2.urlopen(request).read()

            payload = json.loads(data)
            cursor = payload['next_cursor']
            for user in payload['users']:
                members.append(user['id'])
            more_pages = len(payload['users']) == 20
        return members

    def get_users(self, queryset):
        users = []
        for tweet in queryset:
            content = tweet.get_content()
            if 'retweeted_status' in content:
                continue
            user_id = content['user']['id']
            if user_id not in users:
                users.append(user_id)
        return users

    def add_to_list(self, user_id):
        data = urllib.urlencode({'id': user_id})
        request = oauth_request(LIST_MEMBERS, method='POST',
                                params={'id': user_id}, data=data)
        response = urllib2.urlopen(request).read()
