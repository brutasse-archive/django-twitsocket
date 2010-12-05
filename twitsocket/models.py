from django.db import models
from django.utils import simplejson as json


class Tweet(models.Model):
    status_id = models.BigIntegerField()
    content = models.TextField(blank=True)

    class Meta:
        ordering = ('-status_id',)

    def get_content(self):
        return json.loads(self.content)


class Top(models.Model):
    """Top tweets: tweets that are retweeted the most"""
    status_id = models.BigIntegerField()
    content = models.TextField(null=True)
    rt_count = models.IntegerField(default=0, db_index=True)

    def __unicode__(self):
        return u'%s, %s rts' % (self.status_id, self.rt_count)

    class Meta:
        ordering = ['-rt_count']

    def get_content(self):
        return json.loads(self.content)


class Flooder(models.Model):
    """People who tweet a lot (too much?) about the topic"""
    username = models.CharField(max_length=255)
    profile_picture = models.CharField(max_length=1023, null=True)
    tweet_count = models.IntegerField(default=0)
    rt_count = models.IntegerField(default=0)
    total_count = models.IntegerField(default=0, db_index=True)

    def __unicode__(self):
        return u'%s, %s, %s, %s' % (self.username, self.tweet_count,
                                    self.rt_count, self.total_count)

    class Meta:
        ordering = ['-total_count']
