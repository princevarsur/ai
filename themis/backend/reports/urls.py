from django.urls import path
from .views import PDFReportView

app_name = 'reports'

urlpatterns = [
    path('<int:pk>/pdf/', PDFReportView.as_view(), name='report-pdf'),
]
