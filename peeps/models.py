from django.db import models
from django.conf import settings
from django.utils.html import format_html


class Person (models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, default=None, blank=True, null=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=100)
    address1 = models.CharField(max_length=100, blank=True, verbose_name="address")
    address2 = models.CharField(max_length=100, blank=True, verbose_name="address line 2")
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=40, blank=True)
    postcode = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=40, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.CharField(max_length=100, blank=True)
    reg_id = models.CharField(max_length=40, blank=True, verbose_name="Reg ID")
    comment = models.CharField(max_length=100, blank=True)

    def __str__(self):
        if self.reg_id or self.comment:
            return "%s (%s)" % (self.name, ",".join([x for x in (self.reg_id, self.comment) if x]))
        else:
            return self.name

    @property
    def display_name(self):
        return self.name

    def clickable_email(self):
        return format_html('<a href="mailto:{}">{}</a>',
                           self.email, self.email)
    clickable_email.allow_tags = True

    def get_address_lines(self):
        lines = []
        if self.address1:
            lines.append(self.address1)
        if self.address2:
            lines.append(self.address2)
        lines.append(" ".join([x for x in (self.city, self.state, self.postcode) if x]))
        if self.country and self.country != settings.PEEPS_DEFAULT_COUNTRY:
            lines.append(self.country)
        return lines

    def get_mailing_label(self):
        lines = self.get_address_lines()
        return self.name + "\n" + "\n".join(lines)

    class Meta:
        verbose_name_plural = "People"
