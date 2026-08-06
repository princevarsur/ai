from django.contrib import admin
from .models import (
    ScanReport, FlaggedIssue,
    Requirement, SubElement, ClauseIndex, AuditFinding,
)


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


class SubElementInline(admin.TabularInline):
    model = SubElement
    extra = 1


@admin.register(Requirement)
class RequirementAdmin(admin.ModelAdmin):
    list_display = (
        'statute_citation', 'title', 'taxonomy_type',
        'penalty_tier', 'domain', 'mandatory_weight',
    )
    list_filter = ('taxonomy_type', 'penalty_tier', 'domain')
    search_fields = ('statute_citation', 'title', 'description', 'domain')
    inlines = [SubElementInline]


@admin.register(SubElement)
class SubElementAdmin(admin.ModelAdmin):
    list_display = ('requirement', 'element_key', 'weight', 'gliner_label')
    list_filter = ('gliner_label', 'requirement__domain')
    search_fields = ('element_key', 'element_text', 'requirement__statute_citation')


@admin.register(ClauseIndex)
class ClauseIndexAdmin(admin.ModelAdmin):
    list_display = ('document_name', 'clause_id', 'section_title', 'page_no', 'created_at')
    list_filter = ('document_name', 'page_no')
    search_fields = ('document_name', 'clause_id', 'section_title', 'raw_text')


@admin.register(AuditFinding)
class AuditFindingAdmin(admin.ModelAdmin):
    list_display = (
        'policy', 'requirement', 'verdict',
        'confidence_tier', 'severity_score', 'coverage', 'created_at',
    )
    list_filter = ('verdict', 'confidence_tier', 'requirement__domain')
    search_fields = ('requirement__statute_citation', 'policy__title')
    readonly_fields = ('created_at',)

