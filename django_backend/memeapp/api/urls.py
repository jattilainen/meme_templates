from rest_framework import routers
from memeapp.api import views
from django.urls import path

urlpatterns = [
    path('users/', views.UserList.as_view())
]
