from django.contrib import admin
from .models import (
    Org, 
    FourDSequence,
    UserProfile,
    TNAassessment,
    DiscoverStage, 
    DiscussStage, 
    DeliverStage, 
    DemonstrateStage
)

class TNAassessmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'sequence', 'assessment_area')
    list_filter = ('user', 'sequence')  # Order matters here - user filter will appear first
    search_fields = ('user__email', 'assessment_area', 'sequence__id')
    
    def get_queryset(self, request):
        # Start with all objects
        qs = super().get_queryset(request)
        # If we have a user filter active, we can filter sequences by that user
        user_id = request.GET.get('user__id')
        if user_id:
            return qs.filter(user__id=user_id)
        return qs

class FourDSequenceAdmin(admin.ModelAdmin):
    ordering = ('created_at',)
    list_display = ('user', 'get_sequence', 'current_stage', 'created_at', 'updated_at')
    list_filter = ('user', 'current_stage', 'created_at')
    search_fields = ('user__email', 'id')

    def get_sequence(self, obj):
        return obj.id
    get_sequence.short_description = 'Sequence'  # This sets the column header in the admin

admin.site.register(Org)
admin.site.register(FourDSequence, FourDSequenceAdmin)
admin.site.register(UserProfile)
admin.site.register(TNAassessment, TNAassessmentAdmin)
admin.site.register(DiscoverStage)
admin.site.register(DiscussStage)
admin.site.register(DeliverStage)
admin.site.register(DemonstrateStage)

