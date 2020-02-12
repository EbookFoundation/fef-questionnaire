from django.contrib.contenttypes.fields import GenericRelation
from django.db import models

from questionnaire.models import Landing

class Book(models.Model):
    title = models.CharField(max_length=1000, default="")
    landings = GenericRelation(Landing, related_query_name='items')

    def __unicode__(self):
        return self.title

    __str__ = __unicode__
