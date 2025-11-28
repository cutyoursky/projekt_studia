# factories/transaction_factory.py

from studia_api.transactions import BuyTransaction, SellStockTransaction, TransactionError


class TransactionFactory:
    @staticmethod
    def create_transaction(type, user_id, stock, quantity):

        if type == 'buy':
            return BuyTransaction(user_id, stock, quantity)
        elif type == 'sell':
            return SellStockTransaction.from_dict(user_id, stock, quantity)
        else:
            raise TransactionError(f"Nieznany typ transakcji: {type}")
