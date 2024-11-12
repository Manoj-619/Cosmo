import uuid  # Add this import at the top
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
        # Convert UUID to string and filter out None values
        filtered_result = {
            k: str(v) if isinstance(v, uuid.UUID) else v 
            for k, v in result.items() 
            if (v is not None) and (k != 'id')
        }
        return filtered_result

class UserProfileSerializer(BaseStageSerializer):
    email    = serializers.CharField(source='user.email', read_only=True)
    org_id   = serializers.PrimaryKeyRelatedField(source='org.org_id', read_only=True)
    org_name = serializers.CharField(source='org.org_name', read_only=True)
    class Meta:
        model = UserProfile
        fields = ['id', 'email', 'org_id', 'org_name', 'first_name', 'last_name', 'age', 'edu_level', 'current_role']
                
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
    uuid_str = serializers.SerializerMethodField()
    stage_name = serializers.CharField(source='stage_display', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)

    def get_uuid_str(self, obj):
        return str(obj.id)  # Ensure UUID is converted to string
    

    class Meta:
        model = FourDSequence
        fields = ['uuid_str', 'created_at', 'updated_at', 'stage_name', 'email']
