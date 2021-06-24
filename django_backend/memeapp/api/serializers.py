from rest_framework import serializers
from memeapp.models import Profile, Meme, ProfileMeme
from django.contrib.auth.models import User


class UserSerializer(serializers.ModelSerializer):
    """
    Django's User Model serializer
    """

    class Meta:
        model = User
        fields = ['password', 'username'] # пока оставим так, если что че-нибудь ещё добавим


class ProfileSerializer(serializers.ModelSerializer):
    auth_user = UserSerializer()

    def create(self, validated_data):
        user = User.objects.create(**validated_data['auth_user'])
        user.save()
        return user.profile

    class Meta:
        model = Profile
        fields = '__all__'


class MemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meme
        fields = '__all__'

