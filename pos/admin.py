from django.contrib import admin
from .models import Sale, SaleItem

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ['total_price']

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['sale_number', 'total_amount', 'final_amount', 'cashier', 'created_at']
    list_filter = ['created_at', 'cashier']
    search_fields = ['sale_number']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [SaleItemInline]

@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ['sale', 'product', 'quantity', 'unit_price', 'total_price']
    list_filter = ['sale__created_at']
    search_fields = ['sale__sale_number', 'product__name']