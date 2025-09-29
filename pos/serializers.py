from rest_framework import serializers
from django.db import transaction
from .models import Sale, SaleItem
from products.models import Product, StockTransaction

class SaleItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = SaleItem
        fields = '__all__'
        read_only_fields = ['total_price']

class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True, read_only=True)
    cashier_name = serializers.CharField(source='cashier.username', read_only=True)
    
    class Meta:
        model = Sale
        fields = '__all__'
        read_only_fields = ['sale_number', 'created_at', 'updated_at']

class CartItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)

class CreateSaleSerializer(serializers.Serializer):
    items = CartItemSerializer(many=True)
    tax_amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, default=0)
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, default=0)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one item is required.")
        return value
    
    def validate(self, data):
        items = data['items']
        
        # Check product availability
        for item in items:
            try:
                product = Product.objects.get(id=item['product_id'])
                if product.current_stock < item['quantity']:
                    raise serializers.ValidationError(
                        f"Insufficient stock for {product.name}. Available: {product.current_stock}"
                    )
            except Product.DoesNotExist:
                raise serializers.ValidationError(f"Product with ID {item['product_id']} does not exist.")
        
        return data