from django.urls import path

from . import views

urlpatterns = [
    path('authorize', views.AuthorizeView.as_view(),
         name="test-oauth-authorize"),
    path('token', views.TokenView.as_view(),
         name='test-oauth-token'),
    path('api/users/current', views.CurrentUserView.as_view(),
         name='test-oauth-current-user'),
]
