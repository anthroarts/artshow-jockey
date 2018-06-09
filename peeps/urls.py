from django.conf.urls import url
from django.views.generic import DetailView
from .models import Person

urlpatterns = [
    url(r'^mailing_label/(?P<pk>\d+)/$',
        DetailView.as_view(model=Person,
                           template_name="peeps/mailing-label.html",
                           context_object_name="person"),
        name="person-mailing-label"),
]
