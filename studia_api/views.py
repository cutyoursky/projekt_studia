from abc import ABC, abstractmethod
from decimal import Decimal

from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework.decorators import api_view
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import Stock, WalletItem, UserBalance
from .proxy import TransactionProxy
from .serializers import StockSerializer
from .transaction_factory import TransactionFactory
from .transactions import TransactionError, SellStockTransaction


@api_view(['GET'])
def stock_list(request):
    stocks = Stock.objects.all()
    serializer = StockSerializer(stocks, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def register_user(request):
    username = request.data.get('username')
    password = request.data.get('password')

    if User.objects.filter(username=username).exists():
        return Response({'error': 'Użytkownik już istnieje'}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(username=username, password=password)
    UserBalance.objects.create(user=user, balance=100000.00)  # Initial balance
    return Response({'message': 'Użytkownik zarejestrowany'}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def login_user(request):
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(username=username, password=password)
    if user is not None:
        return Response({'message': 'Zalogowano', 'user_id': user.id})
    else:
        return Response({'error': 'Nieprawidłowe dane logowania'}, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['POST'])
def logout_user(request):
    return Response({'message': 'Wylogowano'}, status=200)

@api_view(['POST'])
def buy_stock(request):
    user_id = request.data.get('user_id')
    stock_id = request.data.get('stock_id')
    quantity = request.data.get('quantity')

    if not all([user_id, stock_id, quantity]):
        return Response({'error': 'Brak wymaganych danych.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        transaction = TransactionFactory.create_transaction(
            'buy',
            user_id=request.data['user_id'],
            stock_identifier=request.data['stock_id'],
            quantity=request.data['quantity']
        )
        proxy = TransactionProxy(transaction)
        return proxy.execute()

    except (ValueError, TransactionError) as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_wallet(request):
    user_id = request.GET.get('user_id')
    if not user_id:
        return Response({'error': 'Brak user_id'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'Użytkownik nie istnieje'}, status=status.HTTP_404_NOT_FOUND)

    portfolio = WalletItem.objects.filter(user=user)
    data = [{
        'id': item.id,
        'stock_symbol': item.stock.symbol,
        'stock_name': item.stock.name,
        'stock_price': item.stock.price,
        'quantity': item.quantity
    } for item in portfolio]

    return Response(data)


@api_view(['GET'])
def get_balance(request):
    user_id = request.GET.get('user_id')
    if not user_id:
        return Response({'error': 'Brak user_id'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(id=user_id)
        balance = UserBalance.objects.get(user=user)
    except:
        return Response({'error': 'Nie znaleziono użytkownika'}, status=status.HTTP_404_NOT_FOUND)

    return Response({'balance': balance.balance})

@api_view(['POST'])
def sell_stock(request):
    user_id = request.data.get('user_id')
    stock_symbol = request.data.get('stock_symbol')
    quantity = request.data.get('quantity')

    if not all([user_id, stock_symbol, quantity]):
        return Response({'error': 'Brak wymaganych danych'}, status=400)

    try:
        transaction = TransactionFactory.create_transaction(
            'sell',
            user_id=request.data['user_id'],
            stock_identifier=request.data['stock_symbol'],
            quantity=request.data['quantity']
        )
        proxy = TransactionProxy(transaction)
        return proxy.execute()
    except (ValueError, TransactionError) as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)




