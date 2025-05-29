from django.test import TestCase
from django.urls import reverse
from decimal import Decimal, InvalidOperation
from unittest.mock import patch, call # For mocking API calls and file reading

from .models import CurrencyRate

# Task 2: Test CurrencyRate Model
class CurrencyRateModelTest(TestCase):
    def test_currency_rate_str(self):
        """Test the string representation of the CurrencyRate model."""
        currency = CurrencyRate.objects.create(devise="USD", devise_name="US Dollar", rates=1.0)
        self.assertEqual(str(currency), "USD")

# Task 3: Test convert_currency View
class ConvertCurrencyViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        """Set up non-modified objects used by all test methods."""
        CurrencyRate.objects.create(devise="USD", devise_name="US Dollar", rates=1.0)
        CurrencyRate.objects.create(devise="EUR", devise_name="Euro", rates=0.9)
        CurrencyRate.objects.create(devise="GBP", devise_name="British Pound", rates=0.8)
        # Add a currency with a rate of 0 for testing specific error cases
        CurrencyRate.objects.create(devise="ZERO", devise_name="Zero Rate Currency", rates=0.0)


    def test_convert_currency_view_get(self):
        """Test the GET request for the convert_currency view."""
        response = self.client.get(reverse('currencies:convert_currency'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'currencies/index.html')
        
        self.assertIn('currencies_list', response.context)
        currencies_in_context = response.context['currencies_list']
        self.assertEqual(currencies_in_context.count(), 4) # USD, EUR, GBP, ZERO
        
        # Check if specific currencies are present by their devise code
        devise_codes_in_context = [c.devise for c in currencies_in_context]
        self.assertIn("USD", devise_codes_in_context)
        self.assertIn("EUR", devise_codes_in_context)

    def test_convert_currency_view_post_successful_conversion(self):
        """Test a POST request with a successful currency conversion."""
        response = self.client.post(reverse('currencies:convert_currency'), {
            'amount': '100',
            'from_currency_code': 'USD',
            'to_currency_code': 'EUR',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('conversion_summary', response.context)
        # Expected: (100 / 1.0) * 0.9 = 90.0
        # The summary formats to two decimal places for amount and result
        self.assertEqual(response.context['conversion_summary'], "100.00 USD = 90.00 EUR")
        self.assertEqual(response.context['input_amount'], '100')
        self.assertEqual(response.context['from_currency_code'], 'USD')
        self.assertEqual(response.context['to_currency_code'], 'EUR')
        # Check converted_amount_display as well, which has more precision
        self.assertEqual(response.context['converted_amount_display'], Decimal('90.0000'))
        self.assertIsNone(response.context.get('error_message'))


    def test_convert_currency_view_post_self_conversion(self):
        """Test a POST request converting a currency to itself."""
        response = self.client.post(reverse('currencies:convert_currency'), {
            'amount': '50',
            'from_currency_code': 'GBP',
            'to_currency_code': 'GBP',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('conversion_summary', response.context)
        self.assertEqual(response.context['conversion_summary'], "50.00 GBP = 50.00 GBP")
        self.assertEqual(response.context['converted_amount_display'], Decimal('50.0000'))
        self.assertIsNone(response.context.get('error_message'))

    def test_convert_currency_view_post_invalid_amount_non_numeric(self):
        """Test POST with a non-numeric amount."""
        response = self.client.post(reverse('currencies:convert_currency'), {
            'amount': 'abc',
            'from_currency_code': 'USD',
            'to_currency_code': 'EUR',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('error_message', response.context)
        self.assertEqual(response.context['error_message'], "Invalid amount. Please enter a valid number.")

    def test_convert_currency_view_post_invalid_amount_negative(self):
        """Test POST with a negative amount."""
        response = self.client.post(reverse('currencies:convert_currency'), {
            'amount': '-100',
            'from_currency_code': 'USD',
            'to_currency_code': 'EUR',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('error_message', response.context)
        self.assertEqual(response.context['error_message'], "Amount must be a positive number.")
        
    def test_convert_currency_view_post_zero_amount(self):
        """Test POST with zero amount."""
        response = self.client.post(reverse('currencies:convert_currency'), {
            'amount': '0',
            'from_currency_code': 'USD',
            'to_currency_code': 'EUR',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('error_message', response.context)
        self.assertEqual(response.context['error_message'], "Amount must be a positive number.")

    def test_convert_currency_view_post_empty_amount(self):
        """Test POST with an empty amount."""
        response = self.client.post(reverse('currencies:convert_currency'), {
            'amount': '',
            'from_currency_code': 'USD',
            'to_currency_code': 'EUR',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('error_message', response.context)
        self.assertEqual(response.context['error_message'], "Amount is required.")

    def test_convert_currency_view_post_missing_currency(self):
        """Test POST with a missing 'from' or 'to' currency selection."""
        response_from = self.client.post(reverse('currencies:convert_currency'), {
            'amount': '100',
            'from_currency_code': '', # Missing from_currency
            'to_currency_code': 'EUR',
        })
        self.assertEqual(response_from.status_code, 200)
        self.assertIn('error_message', response_from.context)
        self.assertEqual(response_from.context['error_message'], "Please select both 'From' and 'To' currencies.")

        response_to = self.client.post(reverse('currencies:convert_currency'), {
            'amount': '100',
            'from_currency_code': 'USD',
            'to_currency_code': '', # Missing to_currency
        })
        self.assertEqual(response_to.status_code, 200)
        self.assertIn('error_message', response_to.context)
        self.assertEqual(response_to.context['error_message'], "Please select both 'From' and 'To' currencies.")


    def test_convert_currency_view_post_currency_not_found_in_db(self):
        """Test POST with a currency code not present in the database."""
        response = self.client.post(reverse('currencies:convert_currency'), {
            'amount': '100',
            'from_currency_code': 'USD',
            'to_currency_code': 'XYZ', # XYZ is not in setUpTestData
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('error_message', response.context)
        self.assertEqual(response.context['error_message'], "Selected currency rate not found. Please ensure rates are up to date. You may need to run the update_rates management command.")

    def test_convert_currency_view_post_from_currency_rate_zero(self):
        """Test POST where the 'from' currency has a rate of 0."""
        response = self.client.post(reverse('currencies:convert_currency'), {
            'amount': '100',
            'from_currency_code': 'ZERO', # ZERO has rate 0.0
            'to_currency_code': 'USD',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('error_message', response.context)
        self.assertEqual(response.context['error_message'], "The rate for ZERO is zero, cannot perform conversion.")

# Task 4: Test update_rates Management Command (using mocking)
from django.core.management import call_command
from io import StringIO # To capture command output

class UpdateRatesCommandTest(TestCase):

    @patch('kuriconv.currencies.management.commands.update_rates.Command._fetch_currency_rates')
    @patch('kuriconv.currencies.management.commands.update_rates.Command._load_currency_list_from_file')
    def test_update_rates_command_success(self, mock_load_list, mock_fetch_rates):
        """Test the update_rates command with mocked API and file data."""
        # Configure mock return values
        mock_fetch_rates.return_value = {
            "USD": 1.0,
            "EUR": 0.9,
            "JPY": 110.0
        }
        mock_load_list.return_value = [
            ["USD", "US Dollar"],
            ["EUR", "Euro"],
            # JPY is in API but not in this list, should still be processed with None name if not excluded
            # Let's assume JPY is an exclusion in _build_rate_table or we want to test its handling
        ]
        # Expected data in _build_rate_table (api_rates, currency_definitions)
        # _build_rate_table will create a structure like:
        # {'USD': ['US Dollar', 1.0], 'EUR': ['Euro', 0.9], 'JPY': None} (if JPY not excluded)

        # Call the command
        out = StringIO() # Capture stdout
        err = StringIO() # Capture stderr
        call_command('update_rates', stdout=out, stderr=err)
        
        # Assertions
        self.assertIn("Successfully deleted", out.getvalue()) # Check for deletion message
        self.assertIn("new rate(s) successfully created.", out.getvalue())
        
        # Check database content
        self.assertTrue(CurrencyRate.objects.filter(devise="USD", devise_name="US Dollar", rates=1.0).exists())
        self.assertTrue(CurrencyRate.objects.filter(devise="EUR", devise_name="Euro", rates=0.9).exists())
        
        # JPY was in API response but not in currency_definitions from file.
        # The _build_rate_table sets value to None if not in definitions and not an exclusion
        # The _currency_storage skips entries where value_list is None or malformed.
        # So JPY should not be in the database unless _build_rate_table handles it differently.
        # Based on current _build_rate_table, final_table['JPY'] would be None.
        # _currency_storage skips if value_list is None.
        self.assertFalse(CurrencyRate.objects.filter(devise="JPY").exists())
        
        # Total rates stored should be 2 (USD, EUR)
        self.assertEqual(CurrencyRate.objects.count(), 2)
        
        # Check mocks were called
        mock_fetch_rates.assert_called_once()
        mock_load_list.assert_called_once()

    @patch('kuriconv.currencies.management.commands.update_rates.Command._fetch_currency_rates')
    @patch('kuriconv.currencies.management.commands.update_rates.Command._load_currency_list_from_file')
    def test_update_rates_command_api_error(self, mock_load_list, mock_fetch_rates):
        """Test the command when API fetching fails."""
        mock_fetch_rates.side_effect = ConnectionError("Mocked API connection error")
        mock_load_list.return_value = [["USD", "US Dollar"]] # Needs to return something

        out = StringIO()
        err = StringIO()
        call_command('update_rates', stdout=out, stderr=err)

        self.assertIn("Network Error: Mocked API connection error", err.getvalue())
        self.assertEqual(CurrencyRate.objects.count(), 0) # No rates should be stored

    @patch('kuriconv.currencies.management.commands.update_rates.Command._fetch_currency_rates')
    @patch('kuriconv.currencies.management.commands.update_rates.Command._load_currency_list_from_file')
    def test_update_rates_command_file_not_found(self, mock_load_list, mock_fetch_rates):
        """Test the command when currencies.txt is not found (mocked)."""
        mock_fetch_rates.return_value = {"USD": 1.0} # API call is fine
        mock_load_list.side_effect = FileNotFoundError("Mocked FileNotFoundError") # Simulate file not found
        # The command's _load_currency_list_from_file already catches FileNotFoundError and prints to stderr
        # and returns []. This test ensures the command proceeds and handles the empty list.

        out = StringIO()
        err = StringIO()
        call_command('update_rates', stdout=out, stderr=err)

        # The command's _load_currency_list_from_file itself writes to stderr.
        # The handle() method doesn't write an additional error for this specific case,
        # but the command should complete, possibly with warnings or fewer items processed.
        self.assertIn("Error: currencies.txt not found at", err.getvalue()) # From _load_currency_list_from_file
        
        # Since file loading failed, currency_definitions_list will be empty.
        # _build_rate_table will process API rates, but they will all have None as value_list
        # because no names are provided. _currency_storage will skip all of them.
        self.assertIn("Skipping entry for key 'USD' due to missing/malformed data: None", out.getvalue())
        self.assertEqual(CurrencyRate.objects.count(), 0) # No rates should be stored


    def test_build_rate_table_logic(self):
        """Directly test the _build_rate_table method's logic."""
        # This is an example of testing a helper method if full command mocking is complex.
        # We need an instance of the command to call its methods.
        command = Command()

        api_rates = {"USD": 1.0, "EUR": 0.9, "XYZ": 150.0, "SOLVBTC": 0.00001}
        currency_definitions = [["USD", "US Dollar"], ["EUR", "Euro"]]
        
        # Expected: SOLVBTC excluded, XYZ included as None if not in definitions
        expected_table = {
            "USD": ["US Dollar", 1.0],
            "EUR": ["Euro", 0.9],
            "XYZ": None # XYZ is in api_rates but not in currency_definitions
        }
        # Note: SOLVBTC is an explicit exclusion in _build_rate_table.
        
        result_table = command._build_rate_table(api_rates, currency_definitions)
        self.assertEqual(result_table, expected_table)

        # Test with no currency_definitions
        expected_table_no_defs = {"USD": None, "EUR": None, "XYZ": None}
        result_table_no_defs = command._build_rate_table(api_rates, [])
        self.assertEqual(result_table_no_defs, expected_table_no_defs)

        # Test with empty api_rates
        expected_table_no_api = {}
        result_table_no_api = command._build_rate_table({}, currency_definitions)
        self.assertEqual(result_table_no_api, expected_table_no_api)

```

This initial `tests.py` includes:
*   **`CurrencyRateModelTest`**: Tests the `__str__` method.
*   **`ConvertCurrencyViewTest`**:
    *   `setUpTestData` for common currency objects.
    *   `test_convert_currency_view_get`: Tests GET request, template, and context.
    *   `test_convert_currency_view_post_successful_conversion`: Tests a valid POST.
    *   `test_convert_currency_view_post_self_conversion`: Tests conversion to the same currency.
    *   Tests for invalid amounts (non-numeric, negative, zero, empty).
    *   Test for missing currency selections.
    *   Test for currency not found in DB.
    *   Test for 'from' currency having a rate of 0.
*   **`UpdateRatesCommandTest`**:
    *   `test_update_rates_command_success`: Mocks API and file loading for a successful run, checks DB content and mock calls.
    *   `test_update_rates_command_api_error`: Tests command handling of API error.
    *   `test_update_rates_command_file_not_found`: Tests command handling of missing `currencies.txt`.
    *   `test_build_rate_table_logic`: A direct test for the helper method `_build_rate_table` as suggested in the prompt, showing an alternative if full command mocking becomes too complex.

This covers Tasks 1, 2, 3, and a good portion of Task 4 using mocking. The structure is in place.
I will now submit this content.I have created the initial content for `kuriconv/currencies/tests.py` which includes:
*   Basic model test for `CurrencyRate`.
*   Comprehensive tests for the `convert_currency` view, covering GET requests, successful POST conversions, self-conversions, various invalid amount scenarios, missing currency selections, currency not found in the database, and handling of a zero rate for the 'from' currency.
*   Tests for the `update_rates` management command using mocking for `_fetch_currency_rates` and `_load_currency_list_from_file`. This includes testing a successful command run, a scenario where the API call fails, and a scenario where `currencies.txt` is not found (mocked).
*   A direct unit test for the `_build_rate_table` helper method within the management command, demonstrating how to test complex internal logic separately.

This addresses tasks 1, 2, 3, and 4 (using the mocking option for the management command). Task 5 is to provide the full content, which I've just generated.

The file content is as follows:
```python
from django.test import TestCase
from django.urls import reverse
from decimal import Decimal, InvalidOperation
from unittest.mock import patch, call # For mocking API calls and file reading

from .models import CurrencyRate

# Task 2: Test CurrencyRate Model
class CurrencyRateModelTest(TestCase):
    def test_currency_rate_str(self):
        """Test the string representation of the CurrencyRate model."""
        currency = CurrencyRate.objects.create(devise="USD", devise_name="US Dollar", rates=1.0)
        self.assertEqual(str(currency), "USD")

# Task 3: Test convert_currency View
class ConvertCurrencyViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        """Set up non-modified objects used by all test methods."""
        CurrencyRate.objects.create(devise="USD", devise_name="US Dollar", rates=1.0)
        CurrencyRate.objects.create(devise="EUR", devise_name="Euro", rates=0.9)
        CurrencyRate.objects.create(devise="GBP", devise_name="British Pound", rates=0.8)
        # Add a currency with a rate of 0 for testing specific error cases
        CurrencyRate.objects.create(devise="ZERO", devise_name="Zero Rate Currency", rates=0.0)


    def test_convert_currency_view_get(self):
        """Test the GET request for the convert_currency view."""
        response = self.client.get(reverse('currencies:convert_currency'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'currencies/index.html')
        
        self.assertIn('currencies_list', response.context)
        currencies_in_context = response.context['currencies_list']
        self.assertEqual(currencies_in_context.count(), 4) # USD, EUR, GBP, ZERO
        
        # Check if specific currencies are present by their devise code
        devise_codes_in_context = [c.devise for c in currencies_in_context]
        self.assertIn("USD", devise_codes_in_context)
        self.assertIn("EUR", devise_codes_in_context)

    def test_convert_currency_view_post_successful_conversion(self):
        """Test a POST request with a successful currency conversion."""
        response = self.client.post(reverse('currencies:convert_currency'), {
            'amount': '100',
            'from_currency_code': 'USD',
            'to_currency_code': 'EUR',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('conversion_summary', response.context)
        # Expected: (100 / 1.0) * 0.9 = 90.0
        # The summary formats to two decimal places for amount and result
        self.assertEqual(response.context['conversion_summary'], "100.00 USD = 90.00 EUR")
        self.assertEqual(response.context['input_amount'], '100')
        self.assertEqual(response.context['from_currency_code'], 'USD')
        self.assertEqual(response.context['to_currency_code'], 'EUR')
        # Check converted_amount_display as well, which has more precision
        self.assertEqual(response.context['converted_amount_display'], Decimal('90.0000'))
        self.assertIsNone(response.context.get('error_message'))


    def test_convert_currency_view_post_self_conversion(self):
        """Test a POST request converting a currency to itself."""
        response = self.client.post(reverse('currencies:convert_currency'), {
            'amount': '50',
            'from_currency_code': 'GBP',
            'to_currency_code': 'GBP',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('conversion_summary', response.context)
        self.assertEqual(response.context['conversion_summary'], "50.00 GBP = 50.00 GBP")
        self.assertEqual(response.context['converted_amount_display'], Decimal('50.0000'))
        self.assertIsNone(response.context.get('error_message'))

    def test_convert_currency_view_post_invalid_amount_non_numeric(self):
        """Test POST with a non-numeric amount."""
        response = self.client.post(reverse('currencies:convert_currency'), {
            'amount': 'abc',
            'from_currency_code': 'USD',
            'to_currency_code': 'EUR',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('error_message', response.context)
        self.assertEqual(response.context['error_message'], "Invalid amount. Please enter a valid number.")

    def test_convert_currency_view_post_invalid_amount_negative(self):
        """Test POST with a negative amount."""
        response = self.client.post(reverse('currencies:convert_currency'), {
            'amount': '-100',
            'from_currency_code': 'USD',
            'to_currency_code': 'EUR',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('error_message', response.context)
        self.assertEqual(response.context['error_message'], "Amount must be a positive number.")
        
    def test_convert_currency_view_post_zero_amount(self):
        """Test POST with zero amount."""
        response = self.client.post(reverse('currencies:convert_currency'), {
            'amount': '0',
            'from_currency_code': 'USD',
            'to_currency_code': 'EUR',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('error_message', response.context)
        self.assertEqual(response.context['error_message'], "Amount must be a positive number.")

    def test_convert_currency_view_post_empty_amount(self):
        """Test POST with an empty amount."""
        response = self.client.post(reverse('currencies:convert_currency'), {
            'amount': '',
            'from_currency_code': 'USD',
            'to_currency_code': 'EUR',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('error_message', response.context)
        self.assertEqual(response.context['error_message'], "Amount is required.")

    def test_convert_currency_view_post_missing_currency(self):
        """Test POST with a missing 'from' or 'to' currency selection."""
        response_from = self.client.post(reverse('currencies:convert_currency'), {
            'amount': '100',
            'from_currency_code': '', # Missing from_currency
            'to_currency_code': 'EUR',
        })
        self.assertEqual(response_from.status_code, 200)
        self.assertIn('error_message', response_from.context)
        self.assertEqual(response_from.context['error_message'], "Please select both 'From' and 'To' currencies.")

        response_to = self.client.post(reverse('currencies:convert_currency'), {
            'amount': '100',
            'from_currency_code': 'USD',
            'to_currency_code': '', # Missing to_currency
        })
        self.assertEqual(response_to.status_code, 200)
        self.assertIn('error_message', response_to.context)
        self.assertEqual(response_to.context['error_message'], "Please select both 'From' and 'To' currencies.")


    def test_convert_currency_view_post_currency_not_found_in_db(self):
        """Test POST with a currency code not present in the database."""
        response = self.client.post(reverse('currencies:convert_currency'), {
            'amount': '100',
            'from_currency_code': 'USD',
            'to_currency_code': 'XYZ', # XYZ is not in setUpTestData
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('error_message', response.context)
        self.assertEqual(response.context['error_message'], "Selected currency rate not found. Please ensure rates are up to date. You may need to run the update_rates management command.")

    def test_convert_currency_view_post_from_currency_rate_zero(self):
        """Test POST where the 'from' currency has a rate of 0."""
        response = self.client.post(reverse('currencies:convert_currency'), {
            'amount': '100',
            'from_currency_code': 'ZERO', # ZERO has rate 0.0
            'to_currency_code': 'USD',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('error_message', response.context)
        self.assertEqual(response.context['error_message'], "The rate for ZERO is zero, cannot perform conversion.")

# Task 4: Test update_rates Management Command (using mocking)
from django.core.management import call_command
from io import StringIO # To capture command output
# Need to import the Command class to access its methods for the direct helper test
from kuriconv.currencies.management.commands.update_rates import Command 

class UpdateRatesCommandTest(TestCase):

    @patch('kuriconv.currencies.management.commands.update_rates.Command._fetch_currency_rates')
    @patch('kuriconv.currencies.management.commands.update_rates.Command._load_currency_list_from_file')
    def test_update_rates_command_success(self, mock_load_list, mock_fetch_rates):
        """Test the update_rates command with mocked API and file data."""
        # Configure mock return values
        mock_fetch_rates.return_value = {
            "USD": 1.0,
            "EUR": 0.9,
            "JPY": 110.0 # This currency is in API but not in our file list below
        }
        mock_load_list.return_value = [
            ["USD", "US Dollar"],
            ["EUR", "Euro"],
        ]
        
        # Call the command
        out = StringIO() 
        err = StringIO() 
        call_command('update_rates', stdout=out, stderr=err)
        
        # Assertions
        self.assertIn("Successfully deleted", out.getvalue()) 
        self.assertIn("2 new rate(s) successfully created.", out.getvalue()) # USD and EUR
        # JPY should be skipped because it's not in currency_definitions and thus value_list becomes None
        self.assertIn("Skipping entry for key 'JPY' due to missing/malformed data: None", out.getvalue())
        
        self.assertTrue(CurrencyRate.objects.filter(devise="USD", devise_name="US Dollar", rates=1.0).exists())
        self.assertTrue(CurrencyRate.objects.filter(devise="EUR", devise_name="Euro", rates=0.9).exists())
        self.assertFalse(CurrencyRate.objects.filter(devise="JPY").exists()) # JPY should not be stored
        self.assertEqual(CurrencyRate.objects.count(), 2)
        
        mock_fetch_rates.assert_called_once()
        mock_load_list.assert_called_once()

    @patch('kuriconv.currencies.management.commands.update_rates.Command._fetch_currency_rates')
    @patch('kuriconv.currencies.management.commands.update_rates.Command._load_currency_list_from_file')
    def test_update_rates_command_api_error(self, mock_load_list, mock_fetch_rates):
        """Test the command when API fetching fails."""
        mock_fetch_rates.side_effect = ConnectionError("Mocked API connection error")
        mock_load_list.return_value = [["USD", "US Dollar"]] 

        out = StringIO()
        err = StringIO()
        call_command('update_rates', stdout=out, stderr=err)

        self.assertIn("Network Error: Mocked API connection error", err.getvalue())
        self.assertEqual(CurrencyRate.objects.count(), 0)

    @patch('kuriconv.currencies.management.commands.update_rates.Command._fetch_currency_rates')
    @patch('kuriconv.currencies.management.commands.update_rates.Command._load_currency_list_from_file')
    def test_update_rates_command_file_not_found(self, mock_load_list, mock_fetch_rates):
        """Test the command when currencies.txt is not found (mocked)."""
        mock_fetch_rates.return_value = {"USD": 1.0} 
        # Simulate _load_currency_list_from_file's behavior when FileNotFoundError occurs:
        # it prints to stderr and returns an empty list.
        mock_load_list.side_effect = lambda: (
            Command().stderr.write(Command().style.ERROR(f"Error: currencies.txt not found at mock_path.")),
            []
        )[1]


        out = StringIO()
        err = StringIO()
        call_command('update_rates', stdout=out, stderr=err)
        
        self.assertIn("Error: currencies.txt not found at mock_path.", err.getvalue())
        self.assertIn("Skipping entry for key 'USD' due to missing/malformed data: None", out.getvalue())
        self.assertEqual(CurrencyRate.objects.count(), 0)


    def test_build_rate_table_logic(self):
        """Directly test the _build_rate_table method's logic."""
        command_instance = Command()

        api_rates = {"USD": 1.0, "EUR": 0.9, "XYZ": 150.0, "SOLVBTC": 0.00001}
        currency_definitions = [["USD", "US Dollar"], ["EUR", "Euro"]]
        
        expected_table = {
            "USD": ["US Dollar", 1.0],
            "EUR": ["Euro", 0.9],
            "XYZ": None 
        }
        # SOLVBTC is excluded by the method's logic.
        
        result_table = command_instance._build_rate_table(api_rates, currency_definitions)
        self.assertEqual(result_table, expected_table)

        # Test with no currency_definitions
        expected_table_no_defs = {"USD": None, "EUR": None, "XYZ": None}
        result_table_no_defs = command_instance._build_rate_table(api_rates, [])
        self.assertEqual(result_table_no_defs, expected_table_no_defs)

        # Test with empty api_rates
        expected_table_no_api = {}
        result_table_no_api = command_instance._build_rate_table({}, currency_definitions)
        self.assertEqual(result_table_no_api, expected_table_no_api)

```
I've also corrected a small oversight in the `UpdateRatesCommandTest`:
*   Imported the `Command` class directly (`from kuriconv.currencies.management.commands.update_rates import Command`) to be able to instantiate it for `test_build_rate_table_logic`.
*   Adjusted `mock_load_list.side_effect` in `test_update_rates_command_file_not_found` to more accurately simulate the original method's behavior of printing to stderr and returning an empty list.
*   Refined assertions in `test_update_rates_command_success` for JPY handling based on the logic of `_build_rate_table` and `_currency_storage`.

I am now ready to submit.
