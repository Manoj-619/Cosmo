from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Profile, ProfileStage, DiscoverStage, DiscussStage, DeliverStage, DemonstrateStage, Org

class OrgSerializer(serializers.ModelSerializer):
    class Meta:
        model = Org
        fields = ['org_id', 'org_name']

class ProfileStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfileStage
        fields = ['first_name', 'last_name', 'age', 'edu_level']

class DiscoverStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscoverStage
        fields = ['learning_goals']

class DiscussStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscussStage
        fields = ['content_preference', 'structure_preference', 'pacing_preference', 'neurodiversity_considerations']

class DeliverStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliverStage
        fields = ['modules', 'timeline']

class DemonstrateStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DemonstrateStage
        fields = ['current_module', 'completed_modules', 'understanding_level']

class ProfileSerializer(serializers.ModelSerializer):
    profile_stage = ProfileStageSerializer()
    discover_stage = DiscoverStageSerializer()
    discuss_stage = DiscussStageSerializer()
    deliver_stage = DeliverStageSerializer()
    demonstrate_stage = DemonstrateStageSerializer()
    org = OrgSerializer()

    class Meta:
        model = Profile
        fields = ['user', 'stage', 'profile_stage', 'discover_stage', 'discuss_stage', 'deliver_stage', 'demonstrate_stage', 'org']

class UserSerializer(serializers.ModelSerializer):
    org_id = serializers.CharField(source='profile.org.org_id', read_only=True)
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['email', 'org_id', 'profile']

    def validate(self, data):
        org_id = self.context['request'].data.get('org_id')
        if not org_id:
            raise serializers.ValidationError({"org_id": "Organization ID is required."})
        
        # Check if the organization exists
        if not Org.objects.filter(org_id=org_id).exists():
            raise serializers.ValidationError({"org_id": "Organization with this ID does not exist."})
        
        return data

    def create(self, validated_data):
        org_id = self.context['request'].data.get('org_id')
        user = User.objects.create(**validated_data)
        Profile.objects.create(user=user, org_id=org_id)
        return user
