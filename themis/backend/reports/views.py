from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from compliance.models import ScanReport
from .generator import generate_compliance_pdf


from rest_framework.permissions import IsAuthenticated

class PDFReportView(APIView):
    """GET /api/reports/<id>/pdf/ — Download compliance report as PDF."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            if request.user.is_staff or request.user.is_superuser:
                report = ScanReport.objects.get(pk=pk)
            else:
                report = ScanReport.objects.get(
                    pk=pk,
                    scanned_by=request.user,
                )
        except ScanReport.DoesNotExist:
            return Response(
                {"detail": "Report not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            pdf_bytes = generate_compliance_pdf(report.id)
            
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="compliance_report_{report.id}.pdf"'
            
            return response
        
        except Exception as exc:
            return Response(
                {"detail": f"PDF generation failed: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
