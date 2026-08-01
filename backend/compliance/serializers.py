from rest_framework import serializers
from .models import ScanReport, FlaggedIssue
from laws.serializers import LegalRuleListSerializer


class ScanTriggerSerializer(serializers.Serializer):
    policy_id = serializers.IntegerField()


class WhatIfSerializer(serializers.Serializer):
    clause_text = serializers.CharField()


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
        )


class ScanReportListSerializer(serializers.ModelSerializer):
    policy_title = serializers.CharField(source='policy.title', read_only=True)

    class Meta:
        model = ScanReport
        fields = (
            'id', 'policy_title', 'overall_score', 'risk_level',
            'flagged_clauses', 'scanned_at',
        )


class ScanReportDetailSerializer(serializers.ModelSerializer):
    policy_title = serializers.CharField(source='policy.title', read_only=True)
    flagged_issues = FlaggedIssueSerializer(many=True, read_only=True)

    class Meta:
        model = ScanReport
        fields = (
            'id', 'policy', 'policy_title',
            'overall_score', 'risk_level',
            'total_clauses', 'compliant_clauses', 'flagged_clauses',
            'scanned_at', 'scan_duration_seconds',
            'miniml_avg_score', 'inlegal_avg_score',
            'scanned_by', 'flagged_issues',
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
