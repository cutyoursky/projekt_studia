from abc import abstractmethod, ABC
from decimal import Decimal

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.response import Response

from studia_api.models import Stock, UserBalance, WalletItem


class TransactionError(Exception):
    pass

class Transaction:
    fee = None

    def __init__(self, user_id, stock_id, quantity, valuation_strategy):
        self.user_id = user_id
        self.stock = stock_id
        self._quantity = quantity
        self.valuation_strategy = valuation_strategy

    @classmethod
    def from_dict(cls, user_id, stock_symbol, quantity, valuation_strategy):
        return cls(
            user_id=user_id,
            stock_id=stock_symbol,
            quantity=quantity,
            valuation_strategy=valuation_strategy
        )

    @property
    def quantity(self):
        return self._quantity

    @quantity.setter
    def quantity(self, value):
        if value <= 0:
            raise ValueError("Ilość musi być większa niż 0")
        self._quantity = value

    def execute(self):
        pass

class TransactionHelper:
    @staticmethod
    def calculate_total(price, quantity):
        return price * quantity
    @staticmethod
    def calculate_fee(price, quantity, fee_percentage):
        return (price * quantity) * fee_percentage

class ValuationStrategy(ABC):
    @abstractmethod
    def calculate(self, price: Decimal, quantity: int):
        pass

class SimpleValuation(ValuationStrategy):
    def calculate(self, price, quantity):
        return TransactionHelper.calculate_total(price, quantity)

class FeeValuation(ValuationStrategy):
    def __init__(self, fee_percentage: Decimal):
        self.fee = fee_percentage

    def calculate(self, price, quantity):
        base = TransactionHelper.calculate_total(price, quantity)
        fee  = TransactionHelper.calculate_fee(price, quantity, self.fee)
        return base + fee

class BuyTransaction(Transaction):
    fee = Decimal("0.03")

    def __init__(self, user_id, stock_id, quantity):
        strategy = FeeValuation(fee_percentage=self.fee)
        super().__init__(user_id=user_id, stock_id=stock_id, quantity=quantity, valuation_strategy=strategy)

    # Example fee percentage
    def execute(self):
        try:
            user = User.objects.get(id=self.user_id)
        except User.DoesNotExist:
            raise TransactionError("Użytkownik nie istnieje")

        try:
            stock = Stock.objects.get(id=self.stock)
        except Stock.DoesNotExist:
            raise TransactionError("Akcja nie istnieje")

        quantity = int(self.quantity)
        if quantity <= 0:
            raise TransactionError("Nieprawidłowa ilość akcji do zakupu")

        user_balance = UserBalance.objects.get(user=user)

        if user_balance.balance < stock.price * quantity:
            raise TransactionError("Brak wystarczających środków na koncie użytkownika")

        total = self.valuation_strategy.calculate(stock.price, quantity)
        user_balance.balance -= total
        user_balance.save()

        wallet_item, created = WalletItem.objects.get_or_create(user=user, stock=stock)
        wallet_item.quantity += quantity
        wallet_item.save()

        return Response({'message': 'Zakupiono akcje pomyślnie.', 'new_balance': user_balance.balance}, status=status.HTTP_200_OK)

class SellStockTransaction(Transaction):
    @classmethod
    def from_dict(cls, user_id, stock_symbol, quantity):
        return cls(
            user_id=user_id,
            stock_id=stock_symbol,
            quantity=quantity,
            valuation_strategy=SimpleValuation()
        )

    def execute(self):
        try:
            user = User.objects.get(id=self.user_id)
            stock = Stock.objects.get(symbol=self.stock)
            balance = UserBalance.objects.get(user=user)
            wallet_item = WalletItem.objects.get(user=user, stock=stock)
        except (User.DoesNotExist, Stock.DoesNotExist, UserBalance.DoesNotExist, WalletItem.DoesNotExist):
            raise TransactionError("Nie znaleziono użytkownika, akcji lub portfela")

        try:
            quantity = int(self.quantity)
        except ValueError:
            raise TransactionError("Nieprawidłowa ilość akcji do sprzedaży")

        if quantity <= 0 or quantity > wallet_item.quantity:
            raise TransactionError("Nieprawidłowa ilość akcji do sprzedaży")

        total_value = self.valuation_strategy.calculate(stock.price, quantity)
        wallet_item.quantity -= quantity
        if wallet_item.quantity == 0:
            wallet_item.delete()
        else:
            wallet_item.save()

        balance.balance += total_value
        balance.save()

        return Response({
            'message': 'Sprzedano akcje',
            'new_balance': balance.balance
        }, status=200)