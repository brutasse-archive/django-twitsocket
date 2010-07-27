import urllib2
import urllib
import time

from django.conf import settings
from django.core.management.base import NoArgsCommand
from django.utils import simplejson as json

from tweets.models import Tweet

params = (settings.TWITTER_USERNAME, settings.TWITTER_LIST)
LIST_MEMBERS = 'https://api.twitter.com/1/%s/%s/members.json' % params

password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
password_manager.add_password(None, LIST_MEMBERS,
                              settings.TWITTER_USERNAME,
                              settings.TWITTER_PASSWORD)
handler = urllib2.HTTPBasicAuthHandler(password_manager)
opener = urllib2.build_opener(handler)
urllib2.install_opener(opener)


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
            data = urllib2.urlopen(LIST_MEMBERS + '?cursor=%s' % cursor).read()
            payload = json.loads(data)
            cursor = payload['next_cursor']
            for user in payload['users']:
                members.append(user['id'])
            more_pages = len(payload['users']) == 20
        return members

    def get_users(self, queryset):
        users = []
        for tweet in queryset:
            user_id = tweet.get_content()['user']['id']
            if user_id not in users:
                users.append(user_id)
        return users

    def add_to_list(self, user_id):
        data = urllib.urlencode({'id': user_id})
        response = opener.open(LIST_MEMBERS, data)
