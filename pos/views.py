from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.shortcuts import get_object_or_404
from datetime import datetime
import random
import string
from .models import Sale, SaleItem
from products.models import Product, StockTransaction
from .serializers import SaleSerializer, CreateSaleSerializer

class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.all().prefetch_related('items')
    serializer_class = SaleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date and end_date:
            queryset = queryset.filter(created_at__date__range=[start_date, end_date])
            
        return queryset.order_by('-created_at')
    
    def generate_sale_number(self):
        date_str = datetime.now().strftime("%Y%m%d")
        random_str = ''.join(random.choices(string.digits, k=6))
        return f"SALE-{date_str}-{random_str}"
    
    @action(detail=False, methods=['post'])
    def create_sale(self, request):
        serializer = CreateSaleSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    items_data = serializer.validated_data['items']
                    
                    # Calculate totals
                    total_amount = 0
                    sale_items = []
                    
                    for item_data in items_data:
                        product = get_object_or_404(Product, id=item_data['product_id'])
                        item_total = product.price * item_data['quantity']
                        total_amount += item_total
                        
                        sale_items.append({
                            'product': product,
                            'quantity': item_data['quantity'],
                            'unit_price': product.price,
                            'total_price': item_total
                        })
                    
                    # Calculate final amount
                    final_amount = total_amount + serializer.validated_data['tax_amount'] - serializer.validated_data['discount_amount']
                    
                    # Create sale
                    sale = Sale.objects.create(
                        sale_number=self.generate_sale_number(),
                        total_amount=total_amount,
                        tax_amount=serializer.validated_data['tax_amount'],
                        discount_amount=serializer.validated_data['discount_amount'],
                        final_amount=final_amount,
                        cashier=request.user,
                        notes=serializer.validated_data.get('notes', '')
                    )
                    
                    # Create sale items and update stock
                    for item_data in sale_items:
                        SaleItem.objects.create(
                            sale=sale,
                            product=item_data['product'],
                            quantity=item_data['quantity'],
                            unit_price=item_data['unit_price'],
                            total_price=item_data['total_price']
                        )
                        
                        # Create stock transaction for sale
                        StockTransaction.objects.create(
                            product=item_data['product'],
                            transaction_type='sale',
                            quantity=item_data['quantity'],
                            unit_price=item_data['unit_price'],
                            created_by=request.user,
                            notes=f"Sale #{sale.sale_number}"
                        )
                    
                    return Response(SaleSerializer(sale).data, status=status.HTTP_201_CREATED)
                    
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)