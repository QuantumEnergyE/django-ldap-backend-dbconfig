from model import *
from rest_framework.serializers import ModelSerializer


class AuthProviderSerializer(ModelSerializer):
    class Meta:
        model = AuthProvider
        fields = '__all__'


class GroupRelationMapSerializer(ModelSerializer):
    """
    map group relation
    """
    class Meta:
        model = GroupRelationMap
        fields = '__all__'