"""
URL configuration for DistrictBot project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from chatbot.views import webhook
from chatbot.api_views import (
    api_submit_swali,
    api_get_swali_answer,
    api_submit_malalamiko,
    api_get_malalamiko,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("webhook/", webhook, name="webhook"),
    path("dashboard/", include("chatbot.urls")),
    path("api/swali/", api_submit_swali),
    path("api/swali/<str:question_id>/", api_get_swali_answer),
    path("api/malalamiko/", api_submit_malalamiko),
    path("api/malalamiko/<str:malalamiko_id>/", api_get_malalamiko),
]
