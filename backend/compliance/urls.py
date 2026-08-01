from django.urls import path

from .views import (
    TriggerScanView,
    ScanReportListView,
    ScanReportDetailView,
    WhatIfCheckView,
    ResolveFlagView,
    AccuracyMetricsView,
    DashboardStatsView,
)

app_name = 'compliance'

urlpatterns = [
    path('scan/', TriggerScanView.as_view(), name='scan'),
    path('reports/', ScanReportListView.as_view(), name='report-list'),
    path('reports/<int:pk>/', ScanReportDetailView.as_view(), name='report-detail'),
    path('what-if/', WhatIfCheckView.as_view(), name='what-if'),
    path('flags/<int:pk>/resolve/', ResolveFlagView.as_view(), name='resolve-flag'),
    path('accuracy/', AccuracyMetricsView.as_view(), name='accuracy'),
    path('dashboard/', DashboardStatsView.as_view(), name='dashboard'),
]
