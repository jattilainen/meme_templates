from django.urls import path
from memeapp import views

urlpatterns = [
    path('', views.index, name='index'),
]
