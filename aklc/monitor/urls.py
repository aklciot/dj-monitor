from django.conf.urls import url
from django.urls import path

from . import views

app_name='monitor'
urlpatterns = [
    #path('', views.index, name='index'), 
    path('', views.IndexView.as_view(), name='index'),
    path('node/<int:node_ref>/', views.nodeDetail, name='nodeDetail'),
    path('gateway/<int:gateway_ref>/', views.gatewayDetail, name='gatewayDetail'),
    path('node/update/<int:node_ref>/', views.nodeUpdate, name='nodeUpdate'),
    path('node/modupdate/<int:node_ref>/', views.nodeModNotify, name='nodeModNotify'),
    path('node/remove/<int:node_ref>/', views.nodeRemove, name='nodeRemove'),
    path('node/tb1/<int:node_ref>/', views.tb1, name='tb1'),
    path('node/tb2/<int:node_ref>/', views.tb2, name='tb2'),
]