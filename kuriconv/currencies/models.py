from django.db import models

class CurrencyRate(models.Model):
    """
    Represents a currency and its exchange rate, typically against a base currency (e.g., USD).
    The rates are fetched from an external API and stored in the database.
    """
    devise = models.CharField(max_length=10, primary_key=True, help_text="Currency code (e.g., USD, EUR)")
    devise_name = models.CharField(max_length=255, help_text="Full name of the currency (e.g., United States Dollar)")
    rates = models.FloatField(help_text="Exchange rate relative to a base currency")

    class Meta:
        db_table = 'devise_rates' # Maps to the existing 'devise_rates' table
        verbose_name = "Currency Rate"
        verbose_name_plural = "Currency Rates"

    def __str__(self):
        return self.devise # Returns the currency code for string representation
