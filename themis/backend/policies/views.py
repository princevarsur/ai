import os

from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Policy
from .serializers import (
    PolicyUploadSerializer,
    PolicyListSerializer,
    PolicyDetailSerializer,
)
from ml_engine.text_extractor import extract_text
from ml_engine.clause_extractor import extract_clauses, get_clause_stats


class PolicyUploadView(APIView):
    """POST /api/policies/upload/ — Upload a policy document."""
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = PolicyUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Save policy with uploader
        policy = serializer.save(uploaded_by=request.user)

        # Extract text immediately
        try:
            result = extract_text(policy.file.path)
            policy.extracted_text = result['text']
            policy.file_type = result['file_type']

            # Count clauses
            clauses = extract_clauses(result['text'])
            stats = get_clause_stats(clauses)
            policy.clause_count = stats['total_clauses']
            policy.save(update_fields=[
                'extracted_text', 'file_type', 'clause_count',
            ])
        except Exception as exc:
            # File saved but extraction failed — still return policy
            policy.file_type = os.path.splitext(
                policy.file.name
            )[1].lstrip('.')
            policy.save(update_fields=['file_type'])

            return Response(
                {
                    "policy": PolicyDetailSerializer(policy).data,
                    "extraction_warning": str(exc),
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {
                "policy": PolicyDetailSerializer(policy).data,
                "extraction_stats": {
                    "word_count": result['word_count'],
                    "page_count": result['page_count'],
                    "clause_count": stats['total_clauses'],
                    "warnings": result['warnings'],
                },
            },
            status=status.HTTP_201_CREATED,
        )


class PolicyListView(ListAPIView):
    """GET /api/policies/ — List current user's policies."""
    serializer_class = PolicyListSerializer

    def get_queryset(self):
        return Policy.objects.filter(
            uploaded_by=self.request.user
        ).order_by('-created_at')


class PolicyDetailView(RetrieveAPIView):
    """GET /api/policies/<id>/ — Full policy details."""
    serializer_class = PolicyDetailSerializer

    def get_queryset(self):
        return Policy.objects.filter(uploaded_by=self.request.user)


class PolicyDeleteView(APIView):
    """DELETE /api/policies/<id>/ — Delete policy and its file."""

    def delete(self, request, pk):
        try:
            policy = Policy.objects.get(
                pk=pk, uploaded_by=request.user
            )
        except Policy.DoesNotExist:
            return Response(
                {"detail": "Policy not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Delete the physical file
        if policy.file and os.path.isfile(policy.file.path):
            os.remove(policy.file.path)

        policy.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
