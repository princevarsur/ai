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
    flagged_issues = serializers.SerializerMethodField()
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

    def get_flagged_issues(self, obj):
        from compliance.models import AuditFinding
        from laws.models import LegalRule
        findings = AuditFinding.objects.filter(policy=obj.policy).exclude(verdict='COMPLIANT')
        issues = []
        for f in findings:
            # Fuzzy match to find the corresponding LegalRule for template fix
            template_fix = ""
            best_match_score = 0
            
            # Words to match from the requirement
            req_text = f"{f.requirement.statute_citation} {f.requirement.title}".lower()
            import re
            req_words = set(re.findall(r'\w+', req_text))
            
            for rule in LegalRule.objects.all():
                rule_text = f"{rule.law_name} {rule.section} {rule.requirement_text}".lower()
                rule_words = set(re.findall(r'\w+', rule_text))
                
                score = len(req_words.intersection(rule_words))
                if score > best_match_score and score >= 3: # Require at least 3 matching words
                    best_match_score = score
                    template_fix = rule.template_fix or ""
            
            clause_text = " | ".join(c.get("raw_text", "") if isinstance(c, dict) else str(c) for c in f.evidence_clauses) if f.evidence_clauses else "No explicit clause found."
            
            if f.verdict == 'MISSING':
                description = f"Missing provision for {f.requirement.statute_citation} ({f.requirement.title}). The policy fails to address this requirement. The law requires: \"{f.requirement.description}\" (Coverage: {int(f.coverage * 100)}%) (Caught by: threshold/existence omission)"
            else:
                verdict_str = f.verdict.capitalize()
                snippet = clause_text[:120] + "..." if len(clause_text) > 120 else clause_text
                req_snippet = f.requirement.description[:120] + "..." if len(f.requirement.description) > 120 else f.requirement.description
                description = f"{verdict_str} detected with {f.requirement.statute_citation} ({f.requirement.title}). The policy states: \"{snippet}\" However, the law requires: \"{req_snippet}\" (Semantic similarity: {int(f.nli_confidence * 100)}%) (Caught by: element-level contradiction)"
            
            issues.append({
                "id": f.id,
                "template_fix": template_fix,
                "legal_rule": {
                    "law_name": f.requirement.title,
                    "section": f.requirement.statute_citation,
                    "requirement_text": f.requirement.description,
                    "template_fix": template_fix
                },
                "clause_text": clause_text,
                "clause_index": 0,
                "status": f.verdict,
                "severity_score": f.severity_score,
                "miniml_similarity": f.nli_confidence,
                "inlegal_similarity": f.coverage,
                "description": description,
                "is_resolved": False,
                "nli_label": f.verdict,
                "created_at": f.created_at.isoformat()
            })
        return issues


class AccuracyMetricsSerializer(serializers.Serializer):
    total_cases = serializers.IntegerField()
    should_flag = serializers.IntegerField()
    should_not_flag = serializers.IntegerField()
    accuracy = serializers.FloatField()
    precision = serializers.FloatField()
    recall = serializers.FloatField()
    f1_score = serializers.FloatField()
    method = serializers.CharField()
