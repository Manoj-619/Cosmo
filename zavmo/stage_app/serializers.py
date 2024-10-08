from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Profile, ProfileStage, DiscoverStage, DiscussStage, DeliverStage, DemonstrateStage, Org


class OrgSerializer(serializers.ModelSerializer):
    class Meta:
        model = Org
        fields = ['org_id', 'org_name']

class UserSerializer(serializers.ModelSerializer):
    org_id = serializers.CharField(source='org.org_id')  # Assuming a OneToOne relation with Org

    class Meta:
        model = User
        fields = ['email', 'org_id']

    def create(self, validated_data):
        org_id = validated_data.pop('org')['org_id']  # Extracting org_id from the validated data
        user = User.objects.create(**validated_data)
        user.profile.org_id = org_id  
        user.save()
        return user
    
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

    