from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import LearnerJourney, ProfileStage, DiscoverStage, DiscussStage, DeliverStage, DemonstrateStage, Org

User = get_user_model()

class OrgSerializer(serializers.ModelSerializer):
    class Meta:
        model = Org
        fields = '__all__'
        
class UserDetailSerializer(serializers.ModelSerializer):
    date_joined = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = User
        fields = ['email', 'date_joined']        

class BaseStageSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        result = super().to_representation(instance)
        filtered_result = {k: v for k, v in result.items() if (v is not None) and (k != 'id')}
    
        return filtered_result

class ProfileStageSerializer(BaseStageSerializer):
    class Meta:
        model = ProfileStage
        exclude = ('user',)

class DiscoverStageSerializer(BaseStageSerializer):
    class Meta:
        model = DiscoverStage
        exclude = ('user',)

class DiscussStageSerializer(BaseStageSerializer):
    class Meta:
        model = DiscussStage
        exclude = ('user',)

class DeliverStageSerializer(BaseStageSerializer):
    class Meta:
        model = DeliverStage
        exclude = ('user',)

class DemonstrateStageSerializer(BaseStageSerializer):
    class Meta:
        model = DemonstrateStage
        exclude = ('user',)


class LearnerJourneySerializer(serializers.ModelSerializer):
    user = UserDetailSerializer(read_only=True)
    org = OrgSerializer()
    stage_name = serializers.CharField(source='get_stage_display', read_only=True)

    class Meta:
        model = LearnerJourney
        fields = ['user', 'stage', 'stage_name', 'org']
