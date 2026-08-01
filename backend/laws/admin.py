from django.contrib import admin
from .models import LegalRule


@admin.register(LegalRule)
class LegalRuleAdmin(admin.ModelAdmin):
    list_display = ('law_name', 'section', 'category', 'severity_weight', 'is_active', 'embedding_cached')
    list_filter = ('category', 'severity_weight', 'is_active', 'embedding_cached')
    search_fields = ('law_name', 'section', 'requirement_text', 'keywords_regex')
    list_editable = ('is_active',)
    ordering = ('category', 'law_name', 'section')
