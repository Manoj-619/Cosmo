from django.contrib import admin
from .models import Org, ProfileStage, DiscoverStage, DiscussStage, DeliverStage, DemonstrateStage

@admin.register(Org)
class OrgAdmin(admin.ModelAdmin):
    list_display = ['org_name', 'org_id']  
    search_fields = ['org_name'] 
    list_filter = ['org_name']
    
@admin.register(ProfileStage)
class ProfileStageAdmin(admin.ModelAdmin):
    list_display = ['user', 'first_name', 'last_name', 'age', 'edu_level']
    search_fields = ['user__username', 'first_name', 'last_name']
    list_filter = ['edu_level']

@admin.register(DiscoverStage)
class DiscoverStageAdmin(admin.ModelAdmin):
    list_display = ['user', 'learning_goals']
    search_fields = ['user__username']
    
@admin.register(DiscussStage)
class DiscussStageAdmin(admin.ModelAdmin):
    list_display = ['user', 'content_preference', 'structure_preference']
    search_fields = ['user__username']

@admin.register(DeliverStage)
class DeliverStageAdmin(admin.ModelAdmin):
    list_display = ['user', 'modules', 'timeline']
    search_fields = ['user__username']
    
@admin.register(DemonstrateStage)
class DemonstrateStageAdmin(admin.ModelAdmin):
    list_display = ['user', 'current_module', 'completed_modules', 'understanding_level']
    search_fields = ['user__username']

