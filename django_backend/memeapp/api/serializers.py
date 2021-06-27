from rest_framework import serializers
from django.contrib.auth.models import User


class UserSerializer(serializers.ModelSerializer):
    """
    Django's User Model serializer
    """

    class Meta:
        model = User
        fields = ['password', 'username'] # пока оставим так, если что че-нибудь ещё добавим
