# api/urls.py
from django.urls import path, include

from . import views
from .myJobs import myJobsView
import os

from .deliveryFeedback.deliveryFeedbackView import DeliveryFeedbackViewSet

from rest_framework import routers


#swagger stuff
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView



delivery_feedback = DeliveryFeedbackViewSet.as_view({
    'get': 'list',
    'put': 'update',
})

router = routers.DefaultRouter()

urlpatterns = router.urls
#append all other api urls here.

urlpatterns += [
    path('', views.DenyBasePath),
    path('announcements/', views.ListAnnouncement.as_view()),
    path('missing-delivery-feedback-today/<int:routeId>', views.MissingDeliveryFeedback.as_view()),
    path('route-overview/<int:routeId>/date/<str:input_date>', views.RouteOverview.as_view()),
    path('dj-rest-auth/', include('dj_rest_auth.urls')),
    path('delivery-feedback/', delivery_feedback, name='delivery-feedback'),
    path('my-jobs/', myJobsView.MyJobsViewSet.as_view()),
]

#show swagger documentation only in dev environments.
if "ENV" in os.environ and os.environ["ENV"] == "dev":
   urlpatterns += [
      path('schema/', SpectacularAPIView.as_view(), name='schema'),
      path('schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
      path('schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
   ]


