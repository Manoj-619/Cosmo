from django.contrib import admin
from .models import (
    Org, 
    LearnerJourney,
    ProfileStage, 
    DiscoverStage, 
    DiscussStage, 
    DeliverStage, 
    DemonstrateStage
)

admin.site.register(Org)
admin.site.register(LearnerJourney)
admin.site.register(ProfileStage)
admin.site.register(DiscoverStage)
admin.site.register(DiscussStage)
admin.site.register(DeliverStage)
admin.site.register(DemonstrateStage)

