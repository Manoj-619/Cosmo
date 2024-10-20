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

admin.site.register(Org)
admin.site.register(FourDSequence)
admin.site.register(UserProfile)
admin.site.register(DiscoverStage)
admin.site.register(DiscussStage)
admin.site.register(DeliverStage)
admin.site.register(DemonstrateStage)

