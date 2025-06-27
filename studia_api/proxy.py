# studia_api/proxy.py

from studia_api.transactions import Transaction, TransactionError
from studia_api.models import User


class TransactionProxy:
    def __init__(self, real_transaction):
        self.real_transaction = real_transaction

    def execute(self):
        try:
            user = User.objects.get(id=self.real_transaction.user_id)
        except User.DoesNotExist:
            raise TransactionError("Użytkownik nie istnieje")
        if not user.is_active:
            raise TransactionError("Użytkownik jest nieaktywny")

        return self.real_transaction.execute()
