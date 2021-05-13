from django.conf.urls import url
from django.urls import path
from django.contrib.auth import views as auth_views

from . import views, accounts

app_name = "monitor"
urlpatterns = [
    path("", views.index, name="index"),
    path("index_gw/", views.index_gw, name="index_gw"),
    path("node/<int:node_ref>/", views.nodeDetail, name="nodeDetail"),
    path("gateway/<int:gateway_ref>/", views.gatewayDetail, name="gatewayDetail"),
    path("node/update/<int:node_ref>/", views.nodeUpdate, name="nodeUpdate"),
    path("node/modupdate/<int:node_ref>/", views.nodeModNotify, name="nodeModNotify"),
    path(
        "node/modupdateothers/<int:node_ref>/",
        views.nodeModNotifyOthers,
        name="nodeModNotifyOthers",
    ),
    path("node/remove/<int:node_ref>/", views.nodeRemove, name="nodeRemove"),
    path(
        "node/mqttlog/<int:node_ref>/<int:mq_ref>/",
        views.nodeMqttLog,
        name="nodeMqttLog",
    ),
    path(
        "gateway/mqttlog/<int:gateway_ref>/<int:mq_ref>/",
        views.gatewayMqttLog,
        name="gatewayMqttLog",
    ),
    path("node/tb1/<int:node_ref>/", views.tb1, name="tb1"),
    path("node/tb2/<int:node_ref>/", views.tb2, name="tb2"),
    path("index_msg/", views.index_msg, name="index_msg"),
    path("message/<int:msg_ref>/", views.msgDetail, name="msgDetail"),
    path("message/add/", views.msgAdd, name="msgAdd"),
    path("message/update/<int:msg_ref>/", views.msgUpdate, name="msgUpdate"),
    path("node/msgupdate/<int:node_ref>/", views.nodeMsgUpdate, name="nodeMsgUpdate"),
    path("index_prj/", views.index_prj, name="index_prj"),
    path("project/<int:prj_ref>/", views.projectDetail, name="projectDetail"),
    path("project/update/<int:prj_ref>/", views.projectUpdate, name="projectUpdate"),
    path("project/add/", views.projectAdd, name="projectAdd"),
    path("NetworkStatus/", views.dashBoard, name="DashboardStatus"),
    path("index_rp/", views.index_rp, name="index_rp"),
    path("repeater/<int:rp_ref>/", views.repeaterDetail, name="repeaterDetail"),
    path("repeater/update/<int:rp_ref>/", views.repeaterUpdate, name="repeaterUpdate"),
    path("login/", accounts.login, name="login"),
    path("logout/", accounts.logout, name="logout"),
    path("userprofile/", views.userProfile, name="userProfile"),
    path("userupdate/", views.userUpdate, name="userUpdate"),
]
