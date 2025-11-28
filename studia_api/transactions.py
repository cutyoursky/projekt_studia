from abc import abstractmethod, ABC
from decimal import Decimal
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.response import Response
from .models import UserBalance, WalletItem

class TransactionError(Exception):
    pass

class Transaction:
    fee = None

    def __init__(self, user_id, stock, quantity, valuation_strategy):
        self.user_id = user_id
        self.stock = stock
        self._quantity = quantity
        self.valuation_strategy = valuation_strategy

    @classmethod
    def from_dict(cls, user_id, stock, quantity, valuation_strategy):
        return cls(
            user_id=user_id,
            stock=stock,
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

    def __init__(self, user_id, stock, quantity):
        strategy = FeeValuation(fee_percentage=self.fee)
        super().__init__(user_id=user_id, stock=stock, quantity=quantity, valuation_strategy=strategy)

    def execute(self):
        try:
            user = User.objects.get(id=self.user_id)
        except User.DoesNotExist:
            raise TransactionError("Użytkownik nie istnieje")

        quantity = int(self.quantity)
        if quantity <= 0:
            raise TransactionError("Nieprawidłowa ilość akcji do zakupu")

        user_balance = UserBalance.objects.get(user=user)

        stock_price = Decimal(self.stock['price'])
        total = self.valuation_strategy.calculate(stock_price, quantity)

        if user_balance.balance < total:
            raise TransactionError("Brak wystarczających środków na koncie użytkownika")

        user_balance.balance -= total
        user_balance.save()

        wallet_item, created = WalletItem.objects.get_or_create(
            user=user, stock_symbol=self.stock['symbol']
        )
        wallet_item.quantity += quantity
        wallet_item.save()

        return Response({'message': 'Zakupiono akcje pomyślnie.', 'new_balance': user_balance.balance}, status=status.HTTP_200_OK)


class SellStockTransaction(Transaction):
    @classmethod
    def from_dict(cls, user_id, stock, quantity):
        return cls(
            user_id=user_id,
            stock=stock,
            quantity=quantity,
            valuation_strategy=SimpleValuation()
        )

    def execute(self):
        try:
            user = User.objects.get(id=self.user_id)
            print(self.stock)
            wallet_item = WalletItem.objects.get(user=user, stock_symbol=self.stock['stock_symbol'])
            balance = UserBalance.objects.get(user=user)
        except (User.DoesNotExist, WalletItem.DoesNotExist, UserBalance.DoesNotExist):
            raise TransactionError("Nie znaleziono użytkownika lub akcji w portfelu")

        quantity = int(self.quantity)
        if quantity <= 0 or quantity > wallet_item.quantity:
            raise TransactionError("Nieprawidłowa ilość akcji do sprzedaży")

        stock_price = Decimal(self.stock['stock_price'])
        total_value = self.valuation_strategy.calculate(stock_price, quantity)

        wallet_item.quantity -= quantity
        if wallet_item.quantity == 0:
            wallet_item.delete()
        else:
            wallet_item.save()

        balance.balance += total_value
        balance.save()

        return Response({'message': 'Sprzedano akcje', 'new_balance': balance.balance}, status=200)
