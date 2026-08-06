from rest_framework import serializers
from .models import ScanReport, FlaggedIssue, AuditFinding, Requirement
from laws.serializers import LegalRuleListSerializer


class ScanTriggerSerializer(serializers.Serializer):
    policy_id = serializers.IntegerField()


class WhatIfSerializer(serializers.Serializer):
    clause_text = serializers.CharField()


class RequirementMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Requirement
        fields = ('id', 'statute_citation', 'title', 'description', 'taxonomy_type', 'penalty_tier', 'domain')


class AuditFindingSerializer(serializers.ModelSerializer):
    requirement = RequirementMiniSerializer(read_only=True)
    requirement_id = serializers.IntegerField(source='requirement.id', read_only=True)
    requirement_type = serializers.CharField(source='requirement.taxonomy_type', read_only=True)
    severity = serializers.FloatField(source='severity_score', read_only=True)
    sub_elements = serializers.JSONField(source='sub_element_status', read_only=True)
    evidence = serializers.JSONField(source='evidence_clauses', read_only=True)

    class Meta:
        model = AuditFinding
        fields = (
            'id', 'requirement_id', 'requirement_type', 'requirement',
            'verdict', 'confidence_tier', 'severity', 'coverage',
            'nli_confidence', 'sub_elements', 'evidence', 'created_at',
        )


class FlaggedIssueSerializer(serializers.ModelSerializer):
    legal_rule = LegalRuleListSerializer(read_only=True)
    template_fix = serializers.CharField(
        source='legal_rule.template_fix', read_only=True
    )

    class Meta:
        model = FlaggedIssue
        fields = (
            'id', 'legal_rule', 'clause_text', 'clause_index',
            'status', 'severity_score',
            'miniml_similarity', 'inlegal_similarity',
            'description', 'is_resolved', 'created_at',
            'template_fix',
            'nli_label', 'quantity_conflict', 'element_results',
            'coverage_fraction', 'user_feedback', 'feedback_note',
        )


class ScanReportListSerializer(serializers.ModelSerializer):
    policy_title = serializers.CharField(source='policy.title', read_only=True)

    class Meta:
        model = ScanReport
        fields = (
            'id', 'policy_title', 'overall_score', 'risk_level',
            'total_clauses', 'compliant_clauses', 'flagged_clauses', 'scanned_at',
        )


class ScanReportDetailSerializer(serializers.ModelSerializer):
    policy_title = serializers.CharField(source='policy.title', read_only=True)
    flagged_issues = FlaggedIssueSerializer(many=True, read_only=True)
    audit_findings = AuditFindingSerializer(source='policy.audit_findings', many=True, read_only=True)

    class Meta:
        model = ScanReport
        fields = (
            'id', 'policy', 'policy_title',
            'overall_score', 'risk_level',
            'total_clauses', 'compliant_clauses', 'flagged_clauses',
            'scanned_at', 'scan_duration_seconds',
            'miniml_avg_score', 'inlegal_avg_score',
            'scanned_by', 'flagged_issues', 'audit_findings',
        )


class AccuracyMetricsSerializer(serializers.Serializer):
    total_cases = serializers.IntegerField()
    should_flag = serializers.IntegerField()
    should_not_flag = serializers.IntegerField()
    accuracy = serializers.FloatField()
    precision = serializers.FloatField()
    recall = serializers.FloatField()
    f1_score = serializers.FloatField()
    method = serializers.CharField()
