from django.contrib import admin
from django.db import models
from .models import Category, Product, StockTransaction

class LowStockFilter(admin.SimpleListFilter):
    title = 'low stock status'
    parameter_name = 'low_stock'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Low Stock'),
            ('no', 'Adequate Stock'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(current_stock__lte=models.F('low_stock_threshold'))
        if self.value() == 'no':
            return queryset.filter(current_stock__gt=models.F('low_stock_threshold'))
        return queryset

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'category', 'current_stock', 'price', 'stock_status', 'is_active']
    list_filter = ['category', 'is_active', LowStockFilter]
    search_fields = ['name', 'sku']
    readonly_fields = ['created_at', 'updated_at', 'stock_status']
    
    def stock_status(self, obj):
        return obj.stock_status()
    stock_status.short_description = 'Stock Status'

@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ['product', 'transaction_type', 'quantity', 'previous_stock', 'new_stock', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    readonly_fields = ['created_at']
    search_fields = ['product__name', 'product__sku']