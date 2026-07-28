from django.contrib import admin
from .models import Policy


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'file_type', 'clause_count', 'uploaded_by', 'created_at')
    list_filter = ('category', 'file_type', 'created_at')
    search_fields = ('title', 'extracted_text')
    readonly_fields = ('clause_count', 'extracted_text', 'created_at')
