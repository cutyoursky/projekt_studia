from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import stock_list, register_user, login_user, logout_user, buy_stock, get_wallet, get_balance, sell_stock

urlpatterns = [
    path('api/stocks/', stock_list, name='stock-list'),
    path('api/register/', register_user, name='register-user'),
    path('api/login/', login_user, name='login-user'),
    path('api/logout/', logout_user),
    path('api/stocks/buy/', buy_stock, name='buy-stock'),
    path('api/wallet/', get_wallet, name='get-portfolio'),
    path('api/balance/', get_balance, name='get-balance'),
    path('api/stocks/sell/', sell_stock, name='sell-stock'),
]