from django.urls import path

from .views import (
    LegalRuleListView,
    LegalRuleDetailView,
    LegalRuleByCategoryView,
)

app_name = 'laws'

urlpatterns = [
    path('', LegalRuleListView.as_view(), name='list'),
    path('<int:pk>/', LegalRuleDetailView.as_view(), name='detail'),
    path(
        'category/<str:category>/',
        LegalRuleByCategoryView.as_view(),
        name='by-category',
    ),
]
