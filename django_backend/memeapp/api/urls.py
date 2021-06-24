from rest_framework import routers
from memeapp.api import views
from django.urls import path

urlpatterns = [
    path('memes/', views.MemeList.as_view()),
    path('profiles/', views.ProfileList.as_view()),
    path('users/', views.UserList.as_view())
]
