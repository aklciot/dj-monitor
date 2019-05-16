from django.conf.urls import url
from django.urls import path

from . import views

app_name='monitor'
urlpatterns = [
    path('', views.index, name='index'),
    path('node/<int:nodeID>/', views.nodeDetail, name='nodeDetail'),
]