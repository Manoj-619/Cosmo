from django.contrib import admin
from .models import Org

@admin.register(Org)
class OrgAdmin(admin.ModelAdmin):
    list_display = ['org_name', 'org_id']  
    search_fields = ['org_name'] 
    list_filter = ['org_name']  