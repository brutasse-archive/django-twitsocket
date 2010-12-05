from django.core.management.base import NoArgsCommand

from twitsocket.models import Tweet, Top, Flooder


class Command(NoArgsCommand):

    def handle_noargs(self, **options):
        top_tw = {}
        top_users = {}

        for tw in Tweet.objects.order_by('id'):
            content = tw.get_content()
            screen_name = content['user']['screen_name']

            if not screen_name in top_users:
                top_users[screen_name], created = Flooder.objects.get_or_create(username=screen_name)
                top_users[screen_name].tweet_count = 0
                top_users[screen_name].rt_count = 0
                top_users[screen_name].profile_picture = content['user']['profile_image_url']

            if 'retweeted_status' in content:
                top_users[screen_name].rt_count += 1

                # Top tweets
                rt_id = int(content['retweeted_status']['id'])
                if not rt_id in top_tw:
                    top_tw[rt_id], created = Top.objects.get_or_create(status_id=rt_id)
                    top_tw[rt_id].rt_count = 0
                top_tw[rt_id].rt_count = top_tw[rt_id].rt_count + 1
                if not top_tw[rt_id].content:
                    top_tw[rt_id].content = tw.content

            else:
                top_users[screen_name].tweet_count += 1

        for u in top_users.values():
            u.total_count = u.tweet_count + u.rt_count
            u.save()

        for u in top_tw.values():
            u.save()
