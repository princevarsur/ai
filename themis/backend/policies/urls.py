from django.urls import path

from .views import (
    PolicyUploadView,
    PolicyListView,
    PolicyDetailView,
    PolicyDeleteView,
)

app_name = 'policies'

urlpatterns = [
    path('upload/', PolicyUploadView.as_view(), name='upload'),
    path('', PolicyListView.as_view(), name='list'),
    path('<int:pk>/', PolicyDetailView.as_view(), name='detail'),
    path('<int:pk>/delete/', PolicyDeleteView.as_view(), name='delete'),
]
