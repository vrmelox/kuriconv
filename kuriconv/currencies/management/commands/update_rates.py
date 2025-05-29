import os
import requests
# No longer needed: import mysql.connector as MC
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction, IntegrityError, DataError
from kuriconv.currencies.models import CurrencyRate # Import the CurrencyRate model

class Command(BaseCommand):
    """
    Django management command to update currency exchange rates.

    This command fetches the latest currency rates from the CurrencyFreaks API,
    reads a list of supported currencies and their names from 'currencies.txt',
    combines this information, and then updates the CurrencyRate model
    in the database with the new rates.
    """
    help = 'Fetches currency rates from API and local file, then stores them in the database using Django ORM.'

    def _fetch_currency_rates(self):
        """
        Fetches the latest currency exchange rates from the CurrencyFreaks API.

        Raises:
            ValueError: If the 'FREAKS_API_KEY' environment variable is not set,
                        or if the API response cannot be decoded as JSON.
            ConnectionError: If there's an issue connecting to or fetching data from the API.

        Returns:
            dict: A dictionary containing currency codes as keys and their rates as values.
                  Returns an empty dictionary if the 'rates' key is not in the API response.
        """
        api_key = os.getenv("FREAKS_API_KEY")
        if not api_key:
            raise ValueError("API key 'FREAKS_API_KEY' not found in environment variables.")
        
        surl = "https://api.currencyfreaks.com/v2.0/rates/latest"
        params = {"apikey": api_key}
        
        try:
            response = requests.get(surl, params)
            response.raise_for_status()  # Raise an exception for bad status codes (4XX or 5XX)
            data = response.json()
            rates = data.get("rates", {})
            self.stdout.write(self.style.SUCCESS(f"Successfully fetched {len(rates)} rates from API."))
            return rates
        except requests.exceptions.RequestException as e:
            # More specific error handling for network issues, timeouts, etc.
            raise ConnectionError(f"API request failed: {e}")
        except ValueError as e:
            # Handles JSON decoding errors if the response isn't valid JSON (e.g., API returns non-JSON text)
            raise ValueError(f"Failed to decode API response: {e}")


    def _load_currency_list_from_file(self):
        """
        Loads currency codes and their names from the 'currencies.txt' file.

        The file is expected to be in the root directory of the Django project.
        Each line in the file should be in the format "CODE - Currency Name".

        Returns:
            list: A list of lists, where each inner list contains [currency_code, currency_name].
                  Returns an empty list if the file is not found or is improperly formatted.
        """
        # Path to currencies.txt in the project root (where manage.py is)
        # settings.BASE_DIR should point to the 'kuriconv' directory (one level up from where manage.py is if manage.py is inside kuriconv_project)
        # If manage.py is at the root of the repo, then BASE_DIR is that root.
        # Assuming manage.py is in kuriconv/ (the Django project directory)
        # and currencies.txt is in the repository root, one level above kuriconv/
        
        # Let's assume BASE_DIR is the Django project root (kuriconv/kuriconv in this structure, or just kuriconv/ if manage.py is there)
        # The problem states "root directory of the project (same level as manage.py)"
        # In the current structure, manage.py is in kuriconv/manage.py
        # So, currencies.txt should be at the same level as the 'kuriconv' directory, i.e., settings.BASE_DIR.parent / 'currencies.txt'
        # However, the original script expected currencies.txt in the same dir it ran from.
        # For a management command, it's better to use an absolute path or path relative to a known location.
        
        # The prompt says "root directory of the project (same level as manage.py)"
        # settings.BASE_DIR is typically the directory containing manage.py or its parent if settings.py is nested deeper.
        # If manage.py is at /app/kuriconv/manage.py, then BASE_DIR is /app/kuriconv
        # currencies.txt is at /app/currencies.txt
        # So, the path should be os.path.join(settings.BASE_DIR.parent, 'currencies.txt') if BASE_DIR is kuriconv/
        # Or if BASE_DIR is already /app/, then os.path.join(settings.BASE_DIR, 'currencies.txt')
        
        # Given the file structure `kuriconv/manage.py`, `settings.BASE_DIR` is likely `kuriconv/`.
        # The file `currencies.txt` is at the root, one level above `kuriconv/`. So, `settings.BASE_DIR.parent`.
        
        # Let's check where settings.BASE_DIR points to. Usually it's the project root.
        # If the Django project is 'kuriconv', then settings.BASE_DIR is the path to the 'kuriconv' directory.
        # The file currencies.txt is outside this, in the main repo root.
        # Path to currencies.txt: os.path.join(settings.BASE_DIR.parent, 'currencies.txt')

        file_path = os.path.join(settings.BASE_DIR.parent, 'currencies.txt')
        # If manage.py is in the root of the repository, then it would be:
        # file_path = os.path.join(settings.BASE_DIR, 'currencies.txt')
        # Based on the ls output, manage.py is in /kuriconv/, and currencies.txt is in the root.

        try:
            with open(file_path, 'r') as currencies_file:
                total_content = currencies_file.read()
            lines = total_content.split("\n")
            currency_pairs = []
            for line in lines:
                if line.strip(): 
                    parts = line.split("-", 1)
                    if len(parts) == 2:
                        currency_pairs.append([parts[0].strip(), parts[1].strip()])
            
            if not currency_pairs:
                 self.stdout.write(self.style.WARNING("currencies.txt is empty or incorrectly formatted. No definitions loaded."))
            else:
                self.stdout.write(self.style.SUCCESS(f"Loaded {len(currency_pairs)} currency definitions from {file_path}."))
            return currency_pairs
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"Error: currencies.txt not found at {file_path}."))
            return [] # Return empty list if file not found
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error reading currencies.txt: {e}"))
            return []


    def _build_rate_table(self, api_rates: dict, currency_definitions: list) -> dict:
        """
        Combines API rates with local currency definitions.

        It creates a table that includes all rates from the API (excluding specified
        exclusions like "SOLVBTC", "USD0"). For currencies defined in 'currencies.txt'
        and present in api_rates, it stores a list: [currency_name_from_file, rate_from_api].
        For other API rates not in 'currencies.txt', their value remains None.

        Args:
            api_rates (dict): Dictionary of rates from the API (e.g., {'USD': 1.0, 'EUR': 0.85}).
            currency_definitions (list): List of [code, name] from 'currencies.txt'.

        Returns:
            dict: A dictionary where keys are currency codes and values are either
                  [currency_name, rate] lists or None if the currency is not in definitions.
        """
        final_table = {}
        # Initialize with all API rates (except exclusions), setting them to None initially.
        # This ensures that even if a currency is not in currencies.txt, it's still in the table if from API.
        for code in api_rates.keys():
            if code != "SOLVBTC" and code != "USD0": # Exclusions from original script
                final_table[code] = None

        # Update the table with details from currency_definitions for matching API rates
        for definition in currency_definitions:
            file_currency_code = definition[0]
            file_currency_name = definition[1]
            if file_currency_code in api_rates and file_currency_code in final_table:
                final_table[file_currency_code] = [file_currency_name, api_rates[file_currency_code]]
        
        valid_entries_count = sum(1 for v in final_table.values() if v is not None)
        self.stdout.write(f"Built rate table. {valid_entries_count} currencies have full data for storage.")
        return final_table

    def _currency_storage(self, currency_data_map: dict) -> bool:
        """
        Stores the processed currency rate data into the database using the CurrencyRate model.

        This function clears all existing rates from the 'devise_rates' table and then
        populates it with new rates from the currency_data_map. It operates within
        a database transaction to ensure atomicity.

        Args:
            currency_data_map (dict): A dictionary where keys are currency codes and values
                                      are lists of [currency_name, rate] or None.

        Returns:
            bool: True if the storage was successful (or if no data needed storing),
                  False if there were errors during storage that prevented data insertion.
        """
        try:
            # Use a transaction to ensure all database operations are atomic
            with transaction.atomic():
                # Clear all existing currency rates from the table
                num_deleted, _ = CurrencyRate.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f"Successfully deleted {num_deleted} old rate(s) from devise_rates table."))

                created_count = 0
                skipped_count = 0
                for key, value_list in currency_data_map.items():
                    if value_list and isinstance(value_list, list) and len(value_list) == 2:
                        devise = key
                        devise_name = value_list[0]
                        try:
                            rate_value = float(value_list[1])
                            CurrencyRate.objects.create(
                                devise=devise,
                                devise_name=devise_name,
                                rates=rate_value
                            )
                            created_count += 1
                        except ValueError:
                            self.stderr.write(self.style.WARNING(f"Could not convert rate '{value_list[1]}' to float for {devise}. Skipping."))
                            skipped_count +=1
                        except (IntegrityError, DataError) as db_err:
                            self.stderr.write(self.style.ERROR(f"Database error for {devise} ('{value_list[1]}'): {db_err}. Skipping."))
                            skipped_count += 1
                    else:
                        # This case means the entry in currency_data_map was None or malformed
                        # (e.g. API provided a currency code but it wasn't in our currencies.txt)
                        self.stdout.write(self.style.NOTICE(f"Skipping entry for key '{key}' due to missing/malformed data: {value_list}"))
                        skipped_count += 1
            
            if created_count > 0:
                self.stdout.write(self.style.SUCCESS(f"{created_count} new rate(s) successfully created."))
            if skipped_count > 0:
                self.stdout.write(self.style.WARNING(f"{skipped_count} rate(s) skipped due to errors or missing data."))
            if created_count == 0 and skipped_count == 0 and not currency_data_map:
                 self.stdout.write(self.style.NOTICE("No currency data provided to store (currency_data_map was empty)."))
            elif created_count == 0 and skipped_count > 0 :
                 self.stderr.write(self.style.ERROR("No new rates were stored due to errors."))
                 return False

            return True # Indicate success if we reach here

        except IntegrityError as e: # Catch issues with transaction or other DB constraints
            self.stderr.write(self.style.ERROR(f"Database Integrity Error during storage: {e}"))
            return False
        except Exception as e: # Catch any other unexpected errors
            self.stderr.write(self.style.ERROR(f"An unexpected error occurred during currency storage: {e}"))
            import traceback
            self.stderr.write(self.style.ERROR(traceback.format_exc()))
            return False

    def handle(self, *args, **options):
        """
        The main entry point for the management command.

        Orchestrates the fetching, processing, and storing of currency rates.
        Handles overall error reporting for the command's execution.
        """
        self.stdout.write(self.style.SUCCESS("Starting currency data processing command (using Django ORM)..."))
        
        try:
            api_rates_data = self._fetch_currency_rates()
            currency_definitions_list = self._load_currency_list_from_file()
            
            final_rate_table = self._build_rate_table(api_rates_data, currency_definitions_list)
            
            if not final_rate_table:
                 self.stdout.write(self.style.WARNING("No data to store after building table. Exiting."))
                 return

            success = self._currency_storage(final_rate_table)
            if success:
                self.stdout.write(self.style.SUCCESS("Currency data processing command completed successfully."))
            else:
                self.stderr.write(self.style.ERROR("Currency data processing command failed during storage."))

        except ValueError as ve: # For API key missing or JSON decoding issues
            self.stderr.write(self.style.ERROR(f"Configuration or Data Error: {ve}"))
        except ConnectionError as ce: # For API connection problems
            self.stderr.write(self.style.ERROR(f"Network Error: {ce}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"An unexpected error occurred: {e}"))
            import traceback
            self.stderr.write(self.style.ERROR(traceback.format_exc()))
```
