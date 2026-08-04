from rest_framework.generics import ListAPIView, RetrieveAPIView

from .models import LegalRule
from .serializers import LegalRuleListSerializer, LegalRuleDetailSerializer


class LegalRuleListView(ListAPIView):
    """GET /api/laws/ — List all active rules. ?category=labour to filter."""
    serializer_class = LegalRuleListSerializer
    pagination_class = None

    def get_queryset(self):
        qs = LegalRule.objects.filter(is_active=True)
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        return qs


class LegalRuleDetailView(RetrieveAPIView):
    """GET /api/laws/<id>/ — Full details of one rule."""
    queryset = LegalRule.objects.filter(is_active=True)
    serializer_class = LegalRuleDetailSerializer


class LegalRuleByCategoryView(ListAPIView):
    """GET /api/laws/category/<category>/ — Filter rules by category."""
    serializer_class = LegalRuleListSerializer
    pagination_class = None

    def get_queryset(self):
        return LegalRule.objects.filter(
            is_active=True,
            category=self.kwargs['category'],
        )
