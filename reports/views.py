from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from django.db.models import Sum, Count, F, DecimalField
from django.db.models.functions import TruncDate
from datetime import datetime, timedelta
import pandas as pd
from io import BytesIO
from products.models import Product, StockTransaction
from pos.models import Sale, SaleItem

class ProductReportView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, product_id=None):
        if product_id:
            # Single product report
            return self.get_single_product_report(request, product_id)
        else:
            # All products report
            return self.get_all_products_report(request)
    
    def get_single_product_report(self, request, product_id):
        product = Product.objects.get(id=product_id)
        transactions = StockTransaction.objects.filter(product=product).select_related('created_by')
        
        # Calculate summary
        total_purchased = transactions.filter(transaction_type='purchase').aggregate(Sum('quantity'))['quantity__sum'] or 0
        total_sold = transactions.filter(transaction_type='sale').aggregate(Sum('quantity'))['quantity__sum'] or 0
        
        data = {
            'product': {
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
                'current_stock': product.current_stock,
                'price': str(product.price),
            },
            'summary': {
                'total_purchased': total_purchased,
                'total_sold': total_sold,
                'net_movement': total_purchased - total_sold,
            },
            'transactions': [
                {
                    'date': transaction.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'type': transaction.transaction_type,
                    'quantity': transaction.quantity,
                    'unit_price': str(transaction.unit_price) if transaction.unit_price else None,
                    'total_amount': str(transaction.total_amount) if transaction.total_amount else None,
                    'previous_stock': transaction.previous_stock,
                    'new_stock': transaction.new_stock,
                    'created_by': transaction.created_by.username if transaction.created_by else 'System',
                    'notes': transaction.notes,
                }
                for transaction in transactions.order_by('-created_at')
            ]
        }
        
        return Response(data)
    
    def get_all_products_report(self, request):
        products = Product.objects.filter(is_active=True)
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        # Filter transactions by date if provided
        transactions = StockTransaction.objects.all()
        if start_date and end_date:
            transactions = transactions.filter(created_at__date__range=[start_date, end_date])
        
        product_data = []
        for product in products:
            product_transactions = transactions.filter(product=product)
            total_purchased = product_transactions.filter(transaction_type='purchase').aggregate(Sum('quantity'))['quantity__sum'] or 0
            total_sold = product_transactions.filter(transaction_type='sale').aggregate(Sum('quantity'))['quantity__sum'] or 0
            
            product_data.append({
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
                'category': product.category.name if product.category else 'N/A',
                'current_stock': product.current_stock,
                'price': str(product.price),
                'total_purchased': total_purchased,
                'total_sold': total_sold,
                'net_movement': total_purchased - total_sold,
            })
        
        return Response({'products': product_data})

class DownloadReportView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, report_type):
        if report_type == 'product':
            return self.download_product_report(request)
        elif report_type == 'sales':
            return self.download_sales_report(request)
        elif report_type == 'inventory':
            return self.download_inventory_report(request)
        else:
            return Response({'error': 'Invalid report type'}, status=400)
    
    def download_product_report(self, request):
        product_id = request.GET.get('product_id')
        
        if product_id:
            # Single product report
            view = ProductReportView()
            response = view.get_single_product_report(request, product_id)
            data = response.data
            
            # Create Excel file
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Summary sheet
                summary_data = {
                    'Metric': ['Product Name', 'SKU', 'Current Stock', 'Total Purchased', 'Total Sold', 'Net Movement'],
                    'Value': [
                        data['product']['name'],
                        data['product']['sku'],
                        data['product']['current_stock'],
                        data['summary']['total_purchased'],
                        data['summary']['total_sold'],
                        data['summary']['net_movement']
                    ]
                }
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
                
                # Transactions sheet
                transactions_df = pd.DataFrame(data['transactions'])
                if not transactions_df.empty:
                    transactions_df.to_excel(writer, sheet_name='Transactions', index=False)
            
            output.seek(0)
            response = HttpResponse(
                output.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="product_report_{product_id}.xlsx"'
            return response
        
        else:
            # All products report
            view = ProductReportView()
            response = view.get_all_products_report(request)
            data = response.data
            
            df = pd.DataFrame(data['products'])
            output = BytesIO()
            df.to_excel(output, index=False, engine='openpyxl')
            output.seek(0)
            
            response = HttpResponse(
                output.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename="all_products_report.xlsx"'
            return response
    
    def download_sales_report(self, request):
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        sales = Sale.objects.all()
        if start_date and end_date:
            sales = sales.filter(created_at__date__range=[start_date, end_date])
        
        sales_data = []
        for sale in sales.prefetch_related('items'):
            sales_data.append({
                'Sale Number': sale.sale_number,
                'Date': sale.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'Total Amount': float(sale.total_amount),
                'Tax Amount': float(sale.tax_amount),
                'Discount Amount': float(sale.discount_amount),
                'Final Amount': float(sale.final_amount),
                'Cashier': sale.cashier.username if sale.cashier else 'N/A',
                'Number of Items': sale.items.count(),
            })
        
        df = pd.DataFrame(sales_data)
        output = BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="sales_report.xlsx"'
        return response
    
    def download_inventory_report(self, request):
        products = Product.objects.filter(is_active=True).select_related('category')
        
        inventory_data = []
        for product in products:
            inventory_data.append({
                'Product Name': product.name,
                'SKU': product.sku,
                'Category': product.category.name if product.category else 'N/A',
                'Current Stock': product.current_stock,
                'Low Stock Threshold': product.low_stock_threshold,
                'Price': float(product.price),
                'Cost Price': float(product.cost_price),
                'Status': 'Low Stock' if product.is_low_stock else 'Adequate',
                'Last Updated': product.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            })
        
        df = pd.DataFrame(inventory_data)
        output = BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="inventory_report.xlsx"'
        return response