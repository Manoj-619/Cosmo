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

class FourDSequenceAdmin(admin.ModelAdmin):
    ordering = ('-updated_at',)
    list_display = ('id', 'user', 'current_stage', 'created_at', 'updated_at')
    list_filter = ('current_stage', 'created_at')
    search_fields = ('user__email', 'id')

admin.site.register(Org)
admin.site.register(FourDSequence, FourDSequenceAdmin)
admin.site.register(UserProfile)
admin.site.register(TNAassessment)
admin.site.register(DiscoverStage)
admin.site.register(DiscussStage)
admin.site.register(DeliverStage)
admin.site.register(DemonstrateStage)

