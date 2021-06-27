from memeapp.models import Template
from memeapp.api.serializers import UserSerializer
from rest_framework import generics
from django.contrib.auth.models import User

class UserList(generics.ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

