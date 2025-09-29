from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from rest_framework_simplejwt.views import TokenRefreshView
from accounts.views import create_initial_users, login, get_current_user
from products.views import CategoryViewSet, ProductViewSet, StockTransactionViewSet
from pos.views import SaleViewSet
from reports.views import ProductReportView, DownloadReportView

router = routers.DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'products', ProductViewSet)
router.register(r'stock-transactions', StockTransactionViewSet)
router.register(r'sales', SaleViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    
    # Authentication
    path('api/auth/create-initial-users/', create_initial_users, name='create_initial_users'),
    path('api/auth/login/', login, name='login'),
    path('api/auth/me/', get_current_user, name='get_current_user'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Reports
    path('api/reports/products/', ProductReportView.as_view(), name='product_reports'),
    path('api/reports/products/<int:product_id>/', ProductReportView.as_view(), name='single_product_report'),
    path('api/reports/download/<str:report_type>/', DownloadReportView.as_view(), name='download_report'),
]