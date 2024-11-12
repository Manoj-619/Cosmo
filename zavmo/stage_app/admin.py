from django.contrib import admin
from .models import (
    Org, 
    FourDSequence,
    UserProfile, 
    DiscoverStage, 
    DiscussStage, 
    DeliverStage, 
    DemonstrateStage
)

class FourDSequenceAdmin(admin.ModelAdmin):
    ordering = ('-updated_at',)  # Assuming you have an updated_at field
    # If you use a different field name for the update date, replace 'updated_at'
    # with your actual field name (e.g., 'modified_date', 'last_updated', etc.)

admin.site.register(Org)
admin.site.register(FourDSequence, FourDSequenceAdmin)
admin.site.register(UserProfile)
admin.site.register(DiscoverStage)
admin.site.register(DiscussStage)
admin.site.register(DeliverStage)
admin.site.register(DemonstrateStage)

