from rest_framework import serializers
from .models import Policy


class PolicyUploadSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)

    class Meta:
        model = Policy
        fields = ('title', 'file', 'category')


class PolicyListSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.StringRelatedField()

    class Meta:
        model = Policy
        fields = (
            'id', 'title', 'file_type', 'category',
            'clause_count', 'created_at', 'uploaded_by',
        )


class PolicyDetailSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.StringRelatedField()

    class Meta:
        model = Policy
        fields = (
            'id', 'title', 'file', 'file_type', 'category',
            'extracted_text', 'clause_count',
            'created_at', 'uploaded_by',
        )
