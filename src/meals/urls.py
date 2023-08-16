"""meals URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
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
from django.urls import include, path, re_path
from django.views.generic.base import TemplateView  # new
from django.views.i18n import JavaScriptCatalog  # for recurrence forms

import pdfs.cron
from accounts import views

"""
auth.urls includes a list of urls used for authentication
including /login, /logout, password_change

There are also associated views with each of these urls accordingly
named login, logout, password_change
"""

js_info_dict = {
    "packages": ("recurrence",),
}

urlpatterns = [
    re_path(r"^$", views.home, name="home"),
    path('admin/doc/', include('django.contrib.admindocs.urls')),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("staff/", include("staff.urls")),
    path("volunteer/", include("volunteers.urls")),
    path("routes/", include("routes.urls")),
    path("pdfs/", include("pdfs.urls")),
    path("cron/daily/", pdfs.cron.daily_cron, name="cron_daily"),
    path('api/v1/', include('api.urls')),
    path('privacy-policy/', views.privacy_policy, name="privacy_policy"),
    re_path(r"^i18n/", include("django.conf.urls.i18n")),
    re_path(
        r"^jsi18n/$",
        JavaScriptCatalog.as_view(),
        name="javascript-catalog"),
    # path('/', views.home, name='home')
]
