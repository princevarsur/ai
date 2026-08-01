import json
import logging
from pathlib import Path

from django.core.cache import cache
from django.db.models import Avg, Count, Q

from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ScanReport, FlaggedIssue
from .serializers import (
    ScanTriggerSerializer,
    WhatIfSerializer,
    ScanReportListSerializer,
    ScanReportDetailSerializer,
    FlaggedIssueSerializer,
)
from policies.models import Policy

logger = logging.getLogger(__name__)


class TriggerScanView(APIView):
    """POST /api/compliance/scan/ — Run full compliance scan on a policy."""

    def post(self, request):
        serializer = ScanTriggerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        policy_id = serializer.validated_data['policy_id']

        # Validate policy exists and belongs to user
        try:
            policy = Policy.objects.get(
                id=policy_id, uploaded_by=request.user
            )
        except Policy.DoesNotExist:
            return Response(
                {"detail": "Policy not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not policy.extracted_text:
            return Response(
                {"detail": "Policy has no extracted text. Re-upload the file."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Run scan
        try:
            from compliance.engine import run_compliance_scan
            report = run_compliance_scan(policy_id, request.user)
        except Exception as exc:
            logger.exception("Scan failed for policy %d", policy_id)
            return Response(
                {"detail": f"Scan failed: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            ScanReportDetailSerializer(report).data,
            status=status.HTTP_201_CREATED,
        )


class ScanReportListView(ListAPIView):
    """GET /api/compliance/reports/ — List scan reports for current user."""
    serializer_class = ScanReportListSerializer

    def get_queryset(self):
        return ScanReport.objects.filter(
            scanned_by=self.request.user
        ).order_by('-scanned_at')


class ScanReportDetailView(RetrieveAPIView):
    """GET /api/compliance/reports/<id>/ — Full report with flagged issues."""
    serializer_class = ScanReportDetailSerializer

    def get_queryset(self):
        return ScanReport.objects.filter(
            scanned_by=self.request.user
        ).prefetch_related('flagged_issues__legal_rule')


class WhatIfCheckView(APIView):
    """
    POST /api/compliance/what-if/
    Check a clause against all laws without saving.
    Body: {"clause_text": "..."}
    """

    def post(self, request):
        serializer = WhatIfSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        clause_text = serializer.validated_data['clause_text']

        try:
            from ml_engine.semantic_matcher import (
                precompute_law_embeddings,
                match_clause_against_laws,
            )
            from ml_engine.rule_checker import _safe_regex_search
            from laws.models import LegalRule

            rules = LegalRule.objects.filter(is_active=True)
            law_data = [
                {"id": r.id, "text": r.requirement_text} for r in rules
            ]
            law_cache = precompute_law_embeddings(law_data)
            rule_lookup = {r.id: r for r in rules}

            matches = match_clause_against_laws(clause_text, law_cache)

            results = []
            for m in matches[:10]:  # top 10
                rule = rule_lookup.get(m['legal_rule_id'])
                if not rule:
                    continue

                # Check keyword presence
                kw_match = _safe_regex_search(
                    rule.keywords_regex, clause_text
                )

                results.append({
                    "law_name": rule.law_name,
                    "section": rule.section,
                    "category": rule.category,
                    "severity_weight": rule.severity_weight,
                    "requirement_text": rule.requirement_text[:200],
                    "template_fix": rule.template_fix[:200],
                    "miniml_similarity": m['miniml_similarity'],
                    "inlegal_similarity": m['inlegal_similarity'],
                    "combined_score": m['combined_score'],
                    "is_potential_conflict": m['is_potential_conflict'],
                    "keyword_found": kw_match is not None,
                })

        except Exception as exc:
            logger.exception("What-if check failed")
            return Response(
                {"detail": f"Analysis failed: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({"clause_text": clause_text, "matches": results})


class ResolveFlagView(APIView):
    """PATCH /api/compliance/flags/<id>/resolve/ — Mark issue as resolved."""

    def patch(self, request, pk):
        try:
            issue = FlaggedIssue.objects.get(
                pk=pk,
                report__scanned_by=request.user,
            )
        except FlaggedIssue.DoesNotExist:
            return Response(
                {"detail": "Flagged issue not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        issue.is_resolved = True
        issue.save(update_fields=['is_resolved'])
        return Response(FlaggedIssueSerializer(issue).data)


class AccuracyMetricsView(APIView):
    """
    GET /api/compliance/accuracy/
    Run benchmark and return accuracy metrics. Cached for 1 hour.
    """

    def get(self, request):
        cached = cache.get('themis_accuracy_metrics')
        if cached:
            return Response(cached)

        try:
            from ml_engine.accuracy_benchmark import (
                compute_metrics,
                rule_check_targeted,
            )
            from ml_engine.semantic_matcher import (
                precompute_law_embeddings,
                match_clause_against_laws,
            )
            from laws.models import LegalRule

            data_path = (
                Path(__file__).resolve().parent.parent
                / 'data' / 'test_clauses.json'
            )
            with open(data_path, 'r', encoding='utf-8') as f:
                test_cases = json.load(f)

            rules = list(LegalRule.objects.filter(is_active=True))
            law_data = [
                {"id": r.id, "text": r.requirement_text} for r in rules
            ]
            law_cache = precompute_law_embeddings(law_data)
            rule_lookup = {(r.law_name, r.section): r for r in rules}

            y_true = [tc['ground_truth_label'] for tc in test_cases]

            # Rule-based predictions
            rule_preds = [
                rule_check_targeted(
                    tc['clause_text'],
                    tc['should_match_law'],
                    tc['should_match_section'],
                    rules,
                )
                for tc in test_cases
            ]

            # InLegal-SBERT predictions
            inlegal_scores = []
            for tc in test_cases:
                matches = match_clause_against_laws(
                    tc['clause_text'], law_cache
                )
                target_rule = rule_lookup.get(
                    (tc['should_match_law'], tc['should_match_section'])
                )
                target_id = target_rule.id if target_rule else None
                score = 0.0
                for m in matches:
                    if m['legal_rule_id'] == target_id:
                        score = m['inlegal_similarity']
                        break
                inlegal_scores.append(score)

            # Combined
            combined_preds = [
                rule_preds[i] or inlegal_scores[i] < 0.5
                for i in range(len(test_cases))
            ]

            rule_m = compute_metrics(y_true, rule_preds)
            combined_m = compute_metrics(y_true, combined_preds)

            result = {
                "total_cases": len(test_cases),
                "should_flag": sum(y_true),
                "should_not_flag": len(y_true) - sum(y_true),
                "rule_based": {
                    "accuracy": rule_m['accuracy'],
                    "precision": rule_m['precision'],
                    "recall": rule_m['recall'],
                    "f1_score": rule_m['f1'],
                },
                "combined": {
                    "accuracy": combined_m['accuracy'],
                    "precision": combined_m['precision'],
                    "recall": combined_m['recall'],
                    "f1_score": combined_m['f1'],
                    "method": "Rule + InLegal-SBERT (threshold=0.5)",
                },
            }

            cache.set('themis_accuracy_metrics', result, 3600)
            return Response(result)

        except Exception as exc:
            logger.exception("Accuracy benchmark failed")
            return Response(
                {"detail": f"Benchmark failed: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DashboardStatsView(APIView):
    """GET /api/compliance/dashboard/ — Aggregated compliance stats."""

    def get(self, request):
        user = request.user

        reports = ScanReport.objects.filter(scanned_by=user)
        issues = FlaggedIssue.objects.filter(report__scanned_by=user)

        # Aggregates
        total_policies = reports.values('policy').distinct().count()
        avg_score = reports.aggregate(avg=Avg('overall_score'))['avg'] or 0
        total_issues = issues.count()
        resolved_issues = issues.filter(is_resolved=True).count()
        unresolved_issues = total_issues - resolved_issues

        # Score by category
        category_stats = {}
        for issue in issues.values('legal_rule__category').annotate(
            count=Count('id')
        ):
            cat = issue['legal_rule__category']
            category_stats[cat] = issue['count']

        # Recent scans
        recent = ScanReportListSerializer(
            reports.order_by('-scanned_at')[:5], many=True
        ).data

        return Response({
            "total_policies_scanned": total_policies,
            "average_compliance_score": round(avg_score, 2),
            "total_flagged_issues": total_issues,
            "resolved_issues": resolved_issues,
            "unresolved_issues": unresolved_issues,
            "issues_by_category": category_stats,
            "recent_scans": recent,
        })
