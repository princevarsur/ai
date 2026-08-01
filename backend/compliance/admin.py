from django.contrib import admin
from .models import ScanReport, FlaggedIssue


class FlaggedIssueInline(admin.TabularInline):
    model = FlaggedIssue
    extra = 0
    readonly_fields = (
        'legal_rule', 'clause_text', 'clause_index', 'status',
        'severity_score', 'miniml_similarity', 'inlegal_similarity',
        'description', 'created_at',
    )


@admin.register(ScanReport)
class ScanReportAdmin(admin.ModelAdmin):
    list_display = (
        'policy', 'overall_score', 'risk_level',
        'total_clauses', 'flagged_clauses', 'scanned_by', 'scanned_at',
    )
    list_filter = ('risk_level', 'scanned_at')
    search_fields = ('policy__title',)
    readonly_fields = ('scanned_at', 'scan_duration_seconds')
    inlines = [FlaggedIssueInline]


@admin.register(FlaggedIssue)
class FlaggedIssueAdmin(admin.ModelAdmin):
    list_display = (
        'report', 'legal_rule', 'status', 'severity_score',
        'miniml_similarity', 'inlegal_similarity', 'is_resolved',
    )
    list_filter = ('status', 'is_resolved', 'severity_score')
    search_fields = ('clause_text', 'description', 'legal_rule__law_name')
    list_editable = ('is_resolved',)
