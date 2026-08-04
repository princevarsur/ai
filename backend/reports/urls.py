from django.urls import path
from .views import PDFReportView

app_name = 'reports'

urlpatterns = [
    path('<int:report_id>/pdf/', PDFReportView.as_view(), name='pdf-report'),
]
