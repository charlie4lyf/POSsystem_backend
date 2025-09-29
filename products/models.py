from django.db import models
from django.core.validators import MinValueValidator

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    sku = models.CharField(max_length=100, unique=True)
    current_stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    low_stock_threshold = models.IntegerField(default=10, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} (SKU: {self.sku})"
    
    @property
    def is_low_stock(self):
        return self.current_stock <= self.low_stock_threshold
    
    def stock_status(self):
        """Method for admin display"""
        return "Low Stock" if self.is_low_stock else "Adequate Stock"
    stock_status.short_description = "Stock Status"

class StockTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('purchase', 'Purchase'),
        ('sale', 'Sale'),
        ('adjustment', 'Adjustment'),
        ('return', 'Return'),
    )
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity = models.IntegerField()
    previous_stock = models.IntegerField()
    new_stock = models.IntegerField()
    notes = models.TextField(blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.previous_stock:
            self.previous_stock = self.product.current_stock
        
        if self.transaction_type in ['sale', 'adjustment']:
            self.new_stock = self.previous_stock - self.quantity
        else:  # purchase, return
            self.new_stock = self.previous_stock + self.quantity
            
        if self.unit_price and self.quantity:
            self.total_amount = self.unit_price * self.quantity
            
        super().save(*args, **kwargs)
        
        # Update product stock
        self.product.current_stock = self.new_stock
        self.product.save()
    
    def __str__(self):
        return f"{self.transaction_type} - {self.product.name} - {self.quantity}"