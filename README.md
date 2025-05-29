# Kuriconv - Currency Converter Web Application

## Project Overview

Kuriconv is a web application built with Django that allows users to convert amounts between various currencies. It fetches daily exchange rates from an external API (CurrencyFreaks) and stores them in a local database. Users can then select currencies and an amount to see the conversion result.

## Technology Stack

*   **Backend:** Python, Django
*   **Frontend:** HTML, CSS
*   **Database:** MySQL (as per current `settings.py` configuration)
*   **External API:** [CurrencyFreaks API](https://currencyfreaks.com/) for fetching exchange rates.
*   **Key Python Libraries:**
    *   `requests` (for making API calls)
    *   `mysqlclient` (or equivalent MySQL driver for Django)

## Features

*   Fetches daily currency exchange rates from the CurrencyFreaks API.
*   Stores currency rates in a local database.
*   Provides a web interface for users to:
    *   Select a currency to convert from.
    *   Select a currency to convert to.
    *   Enter an amount to convert.
    *   View the converted amount and a summary of the conversion.
*   Management command to update currency rates manually.

## Setup and Installation

1.  **Clone the Repository:**
    ```bash
    git clone <repository_url>
    cd kuriconv_project # Or your project's root directory name
    ```

2.  **Create and Activate a Python Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    Ensure you have `pip` installed. Install the required Python packages from `requirements.txt`:
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: `requirements.txt` should include Django, requests, mysqlclient, and python-dotenv if used for environment variables locally.)*

4.  **Environment Variables:**
    This project requires several environment variables to be set for proper operation. You can set these in your system environment or by using a `.env` file in the Django project root (`kuriconv/kuriconv/.env` or `/app/kuriconv/kuriconv/.env` if running in a containerized environment as per original setup).
    *   `FREAKS_API_KEY`: Your API key for the CurrencyFreaks API.
    *   `DB_HOST`: The hostname or IP address of your MySQL database server (e.g., `localhost`, `127.0.0.1`).
    *   `DB_DATABASE`: The name of the database to use for this project (e.g., `kuriconv`).
    *   `DB_USER`: The username for connecting to the database.
    *   `DB_PASSWORD`: The password for the database user.
    *   `SECRET_KEY`: Django's secret key for cryptographic signing. A default one is in `kuriconv/kuriconv/settings.py` but should be replaced with a unique, secret key for production.
    *   `DEBUG`: Set to `True` for development mode, `False` for production. (Default is `True` in `settings.py`).

5.  **Database Setup:**
    *   Ensure your MySQL server is running and accessible with the credentials provided in the environment variables.
    *   Create the database specified in `DB_DATABASE` if it doesn't exist.
    *   The application uses Django's ORM. The `CurrencyRate` model maps to the `devise_rates` table.
    *   While Django's `migrate` command is usually used to create tables based on models, this project currently assumes the `devise_rates` table structure is compatible with the `CurrencyRate` model, or it will be implicitly created if it doesn't exist when rates are first stored (behavior depends on Django and DB settings). The `update_rates` command clears and inserts data, it does not handle schema migrations.
    *   The original `kuriconv.sql` might provide the initial table schema if manual setup is preferred or if the table is not automatically handled.

## Running the Application

1.  **Apply Migrations (if necessary):**
    Although the `update_rates` command manages its table's data, other Django apps (like admin, auth) require migrations.
    ```bash
    python manage.py migrate
    ```

2.  **Update Currency Rates:**
    Before running the application for the first time, and regularly thereafter (e.g., daily via a cron job), you need to populate the database with currency rates.
    Run the management command:
    ```bash
    python manage.py update_rates
    ```
    This command will:
    *   Fetch the latest rates from CurrencyFreaks.
    *   Load currency names from `currencies.txt` (located in the project root).
    *   Store the combined data into the `devise_rates` table.

3.  **Run the Django Development Server:**
    ```bash
    python manage.py runserver
    ```
    The application will typically be available at `http://127.0.0.1:8000/`.

## Project Structure

*   `kuriconv/`: The Django project directory.
    *   `kuriconv/settings.py`: Django settings.
    *   `kuriconv/urls.py`: Project-level URL configuration.
*   `kuriconv/currencies/`: The main Django app for this project.
    *   `models.py`: Defines the `CurrencyRate` database model.
    *   `views.py`: Contains the `convert_currency` view logic.
    *   `urls.py`: App-specific URL configuration for the `convert_currency` view.
    *   `management/commands/update_rates.py`: The management command to fetch and store rates.
    *   `templates/currencies/index.html`: The HTML template for the converter page.
    *   `static/currencies/`: Static files (CSS, images) for the `currencies` app.
*   `manage.py`: Django's command-line utility.
*   `currencies.txt`: List of currency codes and names, used by the `update_rates` command.
*   `requirements.txt`: Python dependencies.
*   `README.md`: This file.

## Contributing (Example Section)

Contributions are welcome! If you'd like to contribute, please:
1.  Fork the repository.
2.  Create a new branch for your feature or bug fix.
3.  Make your changes.
4.  Write tests for your changes (if applicable).
5.  Submit a pull request.I have updated the comments in the Python files as detailed in the previous turns.
The `README.md` has now been updated with the comprehensive information about the project.

**Significant Comments Added/Updated:**

*   **`kuriconv/currencies/models.py`:**
    *   Added a docstring for the `CurrencyRate` class explaining its purpose and fields.
    *   Added `help_text` to model fields for better context in Django admin or for schema understanding.
    *   Added `verbose_name` and `verbose_name_plural` in `Meta` class for better representation in Django admin.
    *   Clarified the purpose of the `__str__` method.
    *   Removed the temporary comment `# Corrected as per instruction`.

*   **`kuriconv/currencies/views.py`:**
    *   Added a detailed docstring for the `convert_currency` view, explaining its role for both GET and POST requests and the context it prepares.
    *   Added inline comments to clarify the purpose of fetching `currencies_list`, initializing `context`, preserving user input, handling self-conversion, and the logic behind rate conversion (assuming rates are against a common base).
    *   Improved comments regarding error handling, especially for `CurrencyRate.DoesNotExist` and the generic `Exception`.
    *   Added a comment to note the use of `Decimal` for precision.

*   **`kuriconv/currencies/management/commands/update_rates.py`:**
    *   Added a docstring for the `Command` class itself, explaining its overall purpose.
    *   Added detailed docstrings for each private helper method:
        *   `_fetch_currency_rates`: Explaining its purpose, potential exceptions (`ValueError`, `ConnectionError`), and return value.
        *   `_load_currency_list_from_file`: Explaining its purpose, expected file format, and return value.
        *   `_build_rate_table`: Explaining its logic for combining API and local data, arguments, and return value.
        *   `_currency_storage`: Explaining its role in database interaction, use of transactions, arguments, and return value.
    *   Added a docstring for the `handle` method, outlining its role as the main entry point.
    *   Minor clarifications in inline comments within methods (e.g., why `final_table` is initialized the way it is in `_build_rate_table`).

The `README.md` content was provided in the previous turn.
This completes all tasks for this subtask.
