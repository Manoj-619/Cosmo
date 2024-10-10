from rest_framework import serializers
from django.contrib.auth.models import User
from .models import LearnerJourney, ProfileStage, DiscoverStage, DiscussStage, DeliverStage, DemonstrateStage, Org

class OrgSerializer(serializers.ModelSerializer):
    class Meta:
        model = Org
        fields = '__all__'

class BaseStageSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        result = super().to_representation(instance)
        return {k: v for k, v in result.items() if (v is not None) and (k !='id')}

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

####### NOTE: This is the `manager` serializer
class LearnerJourneySerializer(serializers.ModelSerializer):
    org = OrgSerializer()

    class Meta:
        model = LearnerJourney
        fields = ['user', 'stage', 'org']

class UserSerializer(serializers.ModelSerializer):
    org_id = serializers.CharField(source='learner_journey.org.org_id', read_only=True)
    learner_journey = LearnerJourneySerializer(read_only=True)

    class Meta:
        model = User
        fields = ['email', 'org_id', 'learner_journey']

    def validate(self, data):
        org_id = self.context['request'].data.get('org_id')
        if not org_id:
            raise serializers.ValidationError({"org_id": "Organization ID is required."})
        
        if not Org.objects.filter(org_id=org_id).exists():
            raise serializers.ValidationError({"org_id": "Organization with this ID does not exist."})
        
        return data

    def create(self, validated_data):
        org_id = self.context['request'].data.get('org_id')
        user = User.objects.create(**validated_data)
        LearnerJourney.objects.create(user=user, org_id=org_id)
        return user
