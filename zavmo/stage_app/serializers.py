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
        
        # Add the summary to the filtered result
        filtered_result['summary'] = self.get_markdown_summary(instance)
        
        return filtered_result

    def get_markdown_summary(self, instance):
        model_name = instance._meta.verbose_name.title()
        summary = f"# {model_name}\n\n"
        
        for field_name, value in self.to_representation(instance).items():
            if field_name != 'summary':  # Avoid recursive inclusion of summary
                field = instance._meta.get_field(field_name)
                human_readable_name = field.verbose_name.title() if field.verbose_name != field_name else field_name.replace('_', ' ').title()
                summary += f"**{human_readable_name}**: {value}\n"
        
        return summary.strip()

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
