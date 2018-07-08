from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.utils import timezone


class AnnouncementManager(models.Manager):

    def active(self):
        now = timezone.now()
        query = self.get_queryset().filter(Q(created__lt=now),
                                           (Q(expires__isnull=True) |
                                            Q(expires__gt=now)))
        return query


class Announcement(models.Model):

    objects = AnnouncementManager()

    subject = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    important = models.BooleanField(default=False)
    created = models.DateTimeField()
    expires = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'tinyannounce'

    def is_seen_by(self, user):
        return self.announcementseen_set.filter(user=user).exists()

    def mark_seen(self, user):
        try:
            self.announcementseen_set.get(user=user)
        except AnnouncementSeen.DoesNotExist:
            ann_seen = AnnouncementSeen(announcement=self, user=user)
            ann_seen.save()

    def __str__(self):
        return "%s by %s" % (self.subject, self.author)


class AnnouncementSeen(models.Model):

    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    seen_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'tinyannounce'
        unique_together = (('announcement', 'user'))

    def __str__(self):
        return "%s seen by %s" % (self.announcement.subject, self.user)
