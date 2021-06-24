from memeapp.models import Profile, Meme, ProfileMeme
from memeapp.api.serializers import ProfileSerializer, MemeSerializer, UserSerializer
from rest_framework import generics
from django.contrib.auth.models import User


class UserList(generics.ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class ProfileList(generics.ListCreateAPIView):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer


class MemeList(generics.ListCreateAPIView):
    queryset = Meme.objects.all()
    serializer_class = MemeSerializer

