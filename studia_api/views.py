import random
from abc import ABC, abstractmethod
from decimal import Decimal

import aiohttp
import asyncio
import requests
from asgiref.sync import async_to_sync
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework.decorators import api_view
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import ReadOnlyModelViewSet
from .models import WalletItem, UserBalance
from .proxy import TransactionProxy
from .serializers import StockSerializer
from .transaction_factory import TransactionFactory
from .transactions import TransactionError, SellStockTransaction

API_TOKEN = "cnd47k9r01qr85dtbrl0cnd47k9r01qr85dtbrlg"

# Lista symboli, które chcemy pobierać
symbols = ["BINANCE:BTCUSDT", "BINANCE:ETHUSDT"]


@api_view(['GET'])
def stock_list(request):
    results = async_to_sync(fetch_stock_data_async_to_list)(symbols)
    return JsonResponse(results, safe=False)

async def fetch_stock_data_async_to_list(symbols):
    results = []
    async for stock in fetch_stock_data(symbols):
        results.append(stock)
    return results

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
    stock = request.data.get('stock')
    quantity = request.data.get('quantity')

    if not all([user_id, stock, quantity]):
        return Response({'error': 'Brak wymaganych danych.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        transaction = TransactionFactory.create_transaction(
            'buy',
            user_id=request.data['user_id'],
            stock=request.data['stock'],
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
    data = []
    for item in portfolio:
        symbol = item.stock_symbol
        try:
            url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={API_TOKEN}"
            response = requests.get(url)
            response.raise_for_status()
            stock_data = response.json()
            price = stock_data.get("c", 0)
        except requests.RequestException:
            price = 0

        data.append({
            'stock_symbol': symbol,
            'stock_price': price,
            'quantity': item.quantity
        })
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
    stock = request.data.get('stock')
    quantity = request.data.get('quantity')

    if not all([user_id, stock, quantity]):
        return Response({'error': 'Brak wymaganych danych'}, status=400)

    try:
        transaction = TransactionFactory.create_transaction(
            'sell',
            user_id=request.data['user_id'],
            stock=request.data['stock'],
            quantity=request.data['quantity']
        )
        proxy = TransactionProxy(transaction)
        return proxy.execute()
    except (ValueError, TransactionError) as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


async def fetch_stock_data(symbols):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_single_stock(session, symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks)
        for result in results:
            yield result

async def fetch_single_stock(session, symbol):
    try:
        url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={API_TOKEN}"
        async with session.get(url, timeout=5) as response:
            data = await response.json()
            return {
                "symbol": symbol,
                "price": data.get("c"),
                "high": data.get("h"),
                "low": data.get("l"),
                "open": data.get("o"),
                "previous_close": data.get("pc")
            }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}