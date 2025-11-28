from rest_framework import serializers

class StockSerializer(serializers.Serializer):
    symbol = serializers.CharField()
    price = serializers.DecimalField(max_digits=15, decimal_places=2)
    high = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    low = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    open = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    previous_close = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
