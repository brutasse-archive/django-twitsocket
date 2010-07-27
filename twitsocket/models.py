from django.db import models

from django.utils import simplejson as json


class Tweet(models.Model):
    status_id = models.BigIntegerField()
    content = models.TextField(blank=True)

    class Meta:
        ordering = ('-status_id',)

    def get_content(self):
        return json.loads(self.content)
