from rest_framework import serializers
from meals.constants import CUSTOMER_STATUS, DELIVERY_STATUS

from models.models import Run


class DeliveryFeedbackSerializer(serializers.ModelSerializer):
    route = serializers.IntegerField(source='customer.route.id', read_only=True)
    customer = serializers.IntegerField(source='customer.id', read_only=True)
    run_date = serializers.DateField(read_only=True)

    def validate_delivery_status(self, value):
        if value not in DELIVERY_STATUS:
            raise serializers.ValidationError('delivery status not accepted')
        return value 

    def validate_customer_status(self, value):
        if value not in CUSTOMER_STATUS:
            raise serializers.ValidationError('customer status not accepted')
        return value
    class Meta:
        model = Run
        fields = (
            'id',
            'customer',
            'run_date',
            'delivery_status',
            'customer_status',
            'notes',
            'route'
        )
