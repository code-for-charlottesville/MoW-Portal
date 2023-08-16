from django.shortcuts import get_object_or_404

from rest_framework import viewsets, mixins
from api.deliveryFeedback.deliveryFeedbackSerializer import DeliveryFeedbackSerializer

from models.models import Run

from django_filters import rest_framework as filters

from rest_framework.permissions import IsAuthenticated


from drf_spectacular.utils import extend_schema, OpenApiParameter, extend_schema_view
from drf_spectacular.types import OpenApiTypes

class CustomerFilter(filters.FilterSet):
    route = filters.NumberFilter(field_name='customer__route', required=True)
    run_date = filters.DateFilter(field_name='run_date')
    run_date_after = filters.DateFilter(field_name='run_date', lookup_expr='gte')
    run_date_before = filters.DateFilter(field_name='run_date',lookup_expr='lt')
    customer = filters.NumberFilter(field_name='customer')
    class Meta:
        model = Run
        fields = {'customer', 'run_date'}


@extend_schema_view(
    update=extend_schema(parameters=[
          OpenApiParameter("route", OpenApiTypes.INT, OpenApiParameter.QUERY, required=True),
          OpenApiParameter("run_date", OpenApiTypes.STR, OpenApiParameter.QUERY),
          OpenApiParameter("run_date_after", OpenApiTypes.STR, OpenApiParameter.QUERY),
          OpenApiParameter("run_date_before", OpenApiTypes.STR, OpenApiParameter.QUERY),
          OpenApiParameter("customer", OpenApiTypes.INT, OpenApiParameter.QUERY),
        ])
)

class DeliveryFeedbackViewSet(mixins.UpdateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Run.objects.all()
    serializer_class = DeliveryFeedbackSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = CustomerFilter

    def get_object(self):
        """
        Returns the object the view is displaying.

        You may want to override this if you need to provide non-standard
        queryset lookups.  Eg if objects are referenced using multiple
        keyword arguments in the url conf.
        """
        queryset = self.filter_queryset(self.get_queryset())

        obj = get_object_or_404(queryset)

        self.check_object_permissions(self.request, obj)

        return obj

