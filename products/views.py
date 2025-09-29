from django.db import models
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.shortcuts import get_object_or_404
from .models import Category, Product, StockTransaction
from .serializers import (
    CategorySerializer, 
    ProductSerializer, 
    StockTransactionSerializer,
    RestockSerializer
)

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.query_params.get('category', None)
        low_stock = self.request.query_params.get('low_stock', None)
        
        if category:
            queryset = queryset.filter(category_id=category)
        if low_stock == 'true':
            queryset = queryset.filter(current_stock__lte=models.F('low_stock_threshold'))
            
        return queryset
    
    @action(detail=False, methods=['post'])
    def restock(self, request):
        serializer = RestockSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    product = get_object_or_404(Product, id=serializer.validated_data['product_id'])
                    
                    # Create stock transaction
                    StockTransaction.objects.create(
                        product=product,
                        transaction_type='purchase',
                        quantity=serializer.validated_data['quantity'],
                        unit_price=serializer.validated_data['unit_price'],
                        notes=serializer.validated_data.get('notes', ''),
                        created_by=request.user
                    )
                    
                    # Refresh product data
                    product.refresh_from_db()
                    
                    return Response(ProductSerializer(product).data, status=status.HTTP_200_OK)
                    
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class StockTransactionViewSet(viewsets.ModelViewSet):
    queryset = StockTransaction.objects.all().select_related('product', 'created_by')
    serializer_class = StockTransactionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        product_id = self.request.query_params.get('product', None)
        
        if product_id:
            queryset = queryset.filter(product_id=product_id)
            
        return queryset.order_by('-created_at')