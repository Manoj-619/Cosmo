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
        fields = ['first_name', 'last_name', 'email', 'current_role', 'hobbies', 'learning_goals', 'available_study_time']

class DiscoverStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscoverStage
        fields = ['learning_goals', 'related_interests', 'motivation', 'potential_applications', 'current_knowledge_level']

class DiscussStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscussStage
        fields = ['content_preference', 'structure_preference', 'pacing_preference', 'neurodiversity_considerations', 'additional_preferences', 'habit_preferences', 'ideal_learning_time']

class DeliverStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliverStage
        fields = ['modules', 'timeline', 'milestones']

class DemonstrateStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DemonstrateStage
        fields = ['current_module', 'completed_modules', 'understanding_level', 'next_steps']

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
    # Accessing org_id through the Profile model
    org_id = serializers.CharField(source='profile.org.org_id', read_only=True)
    # Add the ProfileSerializer as a nested serializer
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        # Include 'profile' in the fields
        fields = ['email', 'org_id', 'profile']

    def validate(self, data):
        # Ensure org_id is provided in the request data
        org_id = self.context['request'].data.get('org_id')
        if not org_id:
            raise serializers.ValidationError({"org_id": "Organization ID is required."})
        return data

    def create(self, validated_data):
        # Extract org_id from the request data
        org_id = self.context['request'].data.get('org_id')
        user = User.objects.create(**validated_data)
        # Create a Profile instance with the org_id
        Profile.objects.create(user=user, org_id=org_id)
        return user
