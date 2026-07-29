from rest_framework import serializers
from .models import LegalRule


class LegalRuleListSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalRule
        fields = (
            'id', 'law_name', 'section', 'category',
            'severity_weight', 'is_active',
        )


class LegalRuleDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalRule
        fields = '__all__'
