from django.conf.urls import url
from django.urls import path

from . import views

app_name='monitor'
urlpatterns = [
    #path('', views.index, name='index'),
    path('', views.IndexView.as_view(), name='index'),
    path('node/<int:node_ref>/', views.nodeDetail, name='node_detail'),
]