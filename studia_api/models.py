from django.contrib.auth.models import User
from django.db import models

class WalletItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    stock_symbol = models.CharField(max_length=50)  # zamiast ForeignKey
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('user', 'stock_symbol')

    def __str__(self):
        return f"{self.user.username} - {self.stock_symbol} x {self.quantity}"

class UserBalance(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=10000.00)

    def __str__(self):
        return f"{self.user.username} - {self.balance}$"
