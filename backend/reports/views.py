from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework import permissions, status
from rest_framework.response import Response
from compliance.models import ScanReport
from .generator import generate_compliance_pdf


class PDFReportView(APIView):
    """GET /api/reports/<report_id>/pdf/ — Generate and download PDF scan report."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, report_id):
        try:
            report = ScanReport.objects.select_related('scanned_by', 'policy').get(pk=report_id)
        except ScanReport.DoesNotExist:
            return Response({'detail': 'Report not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Restrict download to the creator or administrative roles
        if not (
            request.user.is_superuser or 
            request.user.is_staff or 
            request.user == report.scanned_by or 
            getattr(request.user, 'role', '') in ['admin', 'compliance_officer']
        ):
            return Response(
                {'detail': 'You do not have authorization to access this audit document.'}, 
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            pdf_bytes = generate_compliance_pdf(report_id)
        except Exception as e:
            return Response(
                {'detail': f'Failed to compile PDF report: {e}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        filename = f"THEMIS_Audit_Report_{report.id}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
