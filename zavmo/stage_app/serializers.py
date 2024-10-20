from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UserProfile, DiscoverStage, DiscussStage, DeliverStage, DemonstrateStage, Org, FourDSequence

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

class UserProfileSerializer(BaseStageSerializer):
    class Meta:
        model = UserProfile
        exclude = ('user',)

class DiscoverStageSerializer(BaseStageSerializer):
    class Meta:
        model = DiscoverStage
        exclude = ('sequence',)

class DiscussStageSerializer(BaseStageSerializer):
    class Meta:
        model = DiscussStage
        exclude = ('sequence',)

class DeliverStageSerializer(BaseStageSerializer):
    class Meta:
        model = DeliverStage
        exclude = ('sequence',)

class DemonstrateStageSerializer(BaseStageSerializer):
    class Meta:
        model = DemonstrateStage
        exclude = ('sequence',)

class FourDSequenceSerializer(serializers.ModelSerializer):
    stage_name = serializers.CharField(source='get_current_stage_display', read_only=True)

    class Meta:
        model = FourDSequence
        fields = ['id', 'user', 'org', 'title', 'created_at', 'updated_at', 'current_stage', 'stage_name']

class DetailedFourDSequenceSerializer(FourDSequenceSerializer):
    discover_stage = DiscoverStageSerializer(read_only=True)
    discuss_stage = DiscussStageSerializer(read_only=True)
    deliver_stage = DeliverStageSerializer(read_only=True)
    demonstrate_stage = DemonstrateStageSerializer(read_only=True)

    class Meta(FourDSequenceSerializer.Meta):
        fields = FourDSequenceSerializer.Meta.fields + ['discover_stage', 'discuss_stage', 'deliver_stage', 'demonstrate_stage']
