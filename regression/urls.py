from django.urls import path

from . import views
from .tasks import get_report_list

app_name = 'regression'

urlpatterns = [
    path('getfile/<int:id><path:path>', views.get_file),
    path('sosreport/<int:id>/', views.SosReportListView.as_view()),
    path('localreport/<int:id>/', views.LocalReportListView.as_view()),
    path('sosreport/<int:id>/<int:timestamp>/', views.SosReportDetailView.as_view()),
    path('localreport/<int:id>/<int:timestamp>/', views.LocalReportDetailView.as_view()),
]
