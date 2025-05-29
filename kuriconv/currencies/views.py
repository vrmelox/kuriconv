from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from .models import CurrencyRate
from decimal import Decimal, InvalidOperation # Used for precise arithmetic operations

def convert_currency(request: HttpRequest) -> HttpResponse:
    """
    Handles currency conversion requests.

    GET requests: Displays the currency conversion form with a list of available currencies.
    POST requests: Processes the submitted form data, performs currency conversion,
                   and displays the result or error messages.
    """
    # Fetch all currency rates from the database, ordered by currency name for display
    currencies_list = CurrencyRate.objects.all().order_by('devise_name')
    
    # Initialize context with common data for the template
    context = {
        'currencies_list': currencies_list,
        'input_amount': None, # Renamed from 'amount' to avoid clash with Decimal 'amount'
        'from_currency_code': None,
        'to_currency_code': None,
        'converted_amount_display': None, # Renamed for clarity in template
        'conversion_summary': None, # e.g., "100.00 USD = 85.00 EUR"
        'error_message': None,
    }

    if request.method == 'POST':
        try:
            amount_str = request.POST.get('amount', '').strip()
            from_currency_code = request.POST.get('from_currency_code')
            to_currency_code = request.POST.get('to_currency_code')

            # Preserve user's input in the context for re-rendering the form
            context.update({
                'input_amount': amount_str, 
                'from_currency_code': from_currency_code,
                'to_currency_code': to_currency_code,
            })

            if not amount_str:
                context['error_message'] = "Amount is required."
                return render(request, 'currencies/index.html', context)
            
            try:
                amount_decimal = Decimal(amount_str) # Renamed to avoid clash
            except InvalidOperation:
                context['error_message'] = "Invalid amount. Please enter a valid number."
                return render(request, 'currencies/index.html', context)

            if amount_decimal <= 0:
                context['error_message'] = "Amount must be a positive number."
                return render(request, 'currencies/index.html', context)

            if not from_currency_code or not to_currency_code:
                context['error_message'] = "Please select both 'From' and 'To' currencies."
                return render(request, 'currencies/index.html', context)
                
            if from_currency_code == to_currency_code:
                # If source and target currencies are the same, no conversion needed
                converted_amount_decimal = amount_decimal 
                # Standardize precision for display using .quantize()
                context['converted_amount_display'] = converted_amount_decimal.quantize(Decimal("0.0001"))
                context['conversion_summary'] = f"{amount_decimal.quantize(Decimal('0.01'))} {from_currency_code} = {converted_amount_decimal.quantize(Decimal('0.01'))} {to_currency_code}"
            else:
                # Fetch rate objects for the selected currencies
                from_rate_obj = CurrencyRate.objects.get(devise=from_currency_code)
                to_rate_obj = CurrencyRate.objects.get(devise=to_currency_code)

                # Convert float rates from DB to Decimal for precision.
                # It's generally safer to convert float to string first, then to Decimal.
                from_rate_decimal = Decimal(str(from_rate_obj.rates)) 
                to_rate_decimal = Decimal(str(to_rate_obj.rates))

                if from_rate_decimal == Decimal(0): # Avoid division by zero if a base rate is somehow zero
                    context['error_message'] = f"The rate for {from_currency_code} is zero, cannot perform conversion."
                    return render(request, 'currencies/index.html', context)
                
                # Perform the conversion. Assuming rates are relative to a common base currency (e.g., USD).
                # Formula: (Amount in FromCurrency / Rate of FromCurrency) * Rate of ToCurrency
                converted_amount_decimal = (amount_decimal / from_rate_decimal) * to_rate_decimal
                context['converted_amount_display'] = converted_amount_decimal.quantize(Decimal("0.0001")) # Standardize precision
                context['conversion_summary'] = f"{amount_decimal.quantize(Decimal('0.01'))} {from_currency_code} = {converted_amount_decimal.quantize(Decimal('0.01'))} {to_currency_code}"

        except CurrencyRate.DoesNotExist:
            # Handle cases where a currency code from the form doesn't exist in the database
            context['error_message'] = "Selected currency rate not found. Please ensure rates are up to date. You may need to run the update_rates management command."
        except Exception as e:
            # Generic error handler for any other unexpected issues during POST processing
            context['error_message'] = f"An unexpected error occurred during conversion: {str(e)}"
            # For debugging, it's good to log the actual exception:
            # import logging
            # logging.exception("Error during currency conversion:")
            
    return render(request, 'currencies/index.html', context)
