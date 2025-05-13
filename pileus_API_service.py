import json
import subprocess
import platform
import os
import logging
import configparser
from datetime import datetime
from enum import Enum
import requests

# Create a log file for each execution
log_filename = f"pileus_API_service_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        # Logs to a unique file per execution
        logging.FileHandler(log_filename),
        logging.StreamHandler()  # Logs to the console
    ]
)

# Load configuration from file
config = configparser.ConfigParser()
config.read("config.ini")


class AccountType(Enum):
    DEDICATED = "dedicated"
    SHARED = "shared"


class PileusAPIService:
    """Service class for interacting with the Pileus API."""

    BASE_AUTH_URL = "https://tokenizer.mypileus.io/prod/credentials"
    BASE_API_URL = "https://api.mypileus.io/api/v1"
    BASE_API_V2_URL = "https://api.mypileus.io/api/v2"

    def __init__(self, debug=False):
        self.username = config.get(
            "AUTH", "PILEUS_USERNAME", fallback=os.getenv("PILEUS_USERNAME"))
        self.password = config.get(
            "AUTH", "PILEUS_PASSWORD", fallback=os.getenv("PILEUS_PASSWORD"))
        self.auth_token = None
        self.api_key = None
        self.account_api_key = None
        self.debug = debug

    def find_account_by_condition(self, accounts, condition):
        """Find an account that matches a given condition."""
        return next((account for account in accounts if condition(account)), None)

    def authenticate(self):
        """Authenticate and store authorization credentials."""
        if not self.username or not self.password:
            logging.error(
                "Missing credentials. Set them in config.ini or as environment variables.")
            return False

        payload = {"username": self.username, "password": self.password}
        headers = {"Content-Type": "application/json"}
        response = self.send_post_request(self.BASE_AUTH_URL, headers, payload)

        if response:
            self.auth_token = response.get("Authorization")
            self.api_key = response.get("apikey")
            self.account_api_key = self.api_key.replace(
                "-1", "18745:0")  # CloudZone-MOCB

            # users = self.get_list_of_users()
            # if users and "accounts" in users and users["accounts"]:
            #     account = self.find_account_by_condition(
            #         users["accounts"], lambda acc: acc["accountName"] == "CloudZone-MOCB")
            #     print("Account:", account)
            #     if account:
            #         account_key = account.get("accountKey")
            #         division_id = account.get("divisionId")
            #         print("Account Key:", account_key)
            #         print("Division ID:", division_id)
            #         if account_key is not None and division_id is not None:
            #             self.account_api_key = self.api_key.replace(
            #                 "-1", f"{account_key}:{division_id}")

        return bool(self.auth_token and self.api_key)

    def send_post_request(self, url, headers, payload):
        """Send a POST request and handle the response with enhanced error handling."""
        try:
            response = requests.post(
                url, headers=headers, json=payload, timeout=100)
            logging.info("POST Request to %s - Status Code: %s",
                         url, response.status_code)
            if response.status_code != 200:
                logging.error("POST request failed: %s", response.text)
            try:
                return response.json()
            except ValueError:
                return response.text
        except requests.Timeout:
            logging.error("POST request to %s timed out.", url)
        except requests.ConnectionError:
            logging.error(
                "Connection error occurred when sending POST request to %s.", url)
        except requests.RequestException as e:
            logging.error("An unexpected error occurred: %s", e)
        return None

    def send_get_request(self, url, headers):
        """Send a GET request and handle the response with enhanced error handling."""
        try:
            response = requests.get(url, headers=headers, timeout=100)
            logging.info("GET Request to %s - Status Code: %s",
                         url, response.status_code)
            logging.info("POST Request to %s - Response Text: %s",
                         url, response.text)
            if response.status_code != 200:
                logging.error("GET request failed: %s", response.text)
            return response.json() if response.status_code == 200 else None
        except requests.Timeout:
            logging.error("GET request to %s timed out.", url)
        except requests.ConnectionError:
            logging.error(
                "Connection error occurred when sending GET request to %s.", url)
        except requests.RequestException as e:
            logging.error("An unexpected error occurred: %s", e)
        return None

    def get_list_of_users(self):
        """Retrieve a list of users from the API."""
        if not self.auth_token or not self.api_key:
            logging.error(
                "Authentication required. Please authenticate first.")
            return None

        url = f"{self.BASE_API_URL}/users"
        headers = {
            "Authorization": self.auth_token,
            "apikey": self.api_key
        }
        return self.send_get_request(url, headers)

    def get_users_and_roles(self):
        """Retrieve users and their roles from the API."""
        if not self.auth_token or not self.api_key:
            logging.error(
                "Authentication required. Please authenticate first.")
            return None

        url = f"{self.BASE_API_URL}/users/with-roles"
        headers = {
            "Authorization": self.auth_token,
            "apikey": self.api_key
        }
        return self.send_get_request(url, headers)

    def onboard_aws_account(self, account_id, account_name, bucket_name=None, bucket_region="us-east-1"):
        """Onboard an AWS account to Anodot."""
        if not self.auth_token or not self.api_key:
            logging.error(
                "Authentication required. Please authenticate first.")
            return None

        url = f"{self.BASE_API_V2_URL}/onboarding/aws/{account_id}"
        headers = {
            "Authorization": self.auth_token,
            "apikey": self.account_api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "accountName": account_name,
            "bucketName": bucket_name if bucket_name else f"cur-{account_id}",
            "bucketRegion": bucket_region
        }

        return self.send_post_request(url, headers, payload)

    def onboard_aws_account_msp(self, account_id, account_name, bucket_name, bucket_region="us-east-1", account_type=AccountType.DEDICATED.value, reseller_customer_id=None,
                                reseller_customer_name=None, is_customer_self_managed=None, reseller_customer_domain=None,
                                auto_assign_linked_accounts=None, excluded_linked_account_match=None):
        """Onboard an AWS account for an MSP."""
        if not self.auth_token or not self.api_key:
            logging.error(
                "Authentication required. Please authenticate first.")
            return None

        url = f"{self.BASE_API_V2_URL}/onboarding/aws/{account_id}"
        headers = {
            "Authorization": self.auth_token,
            "apikey": self.account_api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "accountName": account_name,
            "bucketName": bucket_name if bucket_name else f"cur-{account_id}",
            "bucketRegion": bucket_region if bucket_region else "us-east-1",
            "accountType": AccountType.DEDICATED.value if int(account_type) else AccountType.SHARED.value,
            "resellerCustomerId": reseller_customer_id or None,
            "resellerCustomerName": reseller_customer_name or None,
            "isCustomerSelfManaged": int(is_customer_self_managed),
            "resellerCustomerDomain": reseller_customer_domain or None,
            "autoAssignLinkedAccounts": int(auto_assign_linked_accounts),
            "excludedLinkedAccountMatch": excluded_linked_account_match or None
        }
        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}
        print(payload)
        response = self.send_post_request(url, headers, payload)

        if response and isinstance(response, str):  # Raw script, not JSON
            folder_name = f"{account_name}_{account_id}"
            os.makedirs(folder_name, exist_ok=True)
            script_path = os.path.join(folder_name, "setup.sh")
            with open(script_path, "w") as script_file:
                script_file.write(response)
            logging.info("Script saved to %s", script_path)

            # Prompt to open folder
            open_prompt = input(
                "Do you want to open the folder? (y/n): ").strip().lower()
            if open_prompt == "y":
                print(f"Opening folder: {folder_name}")
                try:
                    system_platform = platform.system()
                    if system_platform == "Windows":
                        os.startfile(folder_name)
                    elif system_platform == "Darwin":  # macOS
                        subprocess.run(["open", folder_name], check=True)
                    else:  # Linux
                        subprocess.run(["xdg-open", folder_name], check=True)
                    logging.info("Opened folder: %s", folder_name)
                except (subprocess.CalledProcessError, OSError) as e:
                    logging.warning("Could not open folder: %s", e)


def generate_config_file():
    """Generates a default config.ini file if it does not exist."""
    if not os.path.exists("config.ini"):
        config = configparser.ConfigParser()
        config["AUTH"] = {
            "PILEUS_USERNAME": "your_username",
            "PILEUS_PASSWORD": "your_password"
        }
        with open("config.ini", "w") as configfile:
            config.write(configfile)
        logging.info(
            "Generated default config.ini file. Please update it with your credentials.")


def get_valid_input(prompt, valid_options=None, allow_empty=False):
    """Helper function to validate user input."""
    while True:
        user_input = input(prompt).strip()
        if not user_input and not allow_empty:
            print("Input cannot be empty. Please enter a valid value.")
            continue
        if allow_empty and not user_input:
            return None
        if valid_options and user_input not in valid_options:
            print(f"Invalid input. Please enter one of {valid_options}")
        else:
            return user_input


def get_boolean_input(prompt):
    """Helper function to validate boolean input (1=True, 0=False)."""
    while True:
        user_input = input(prompt).strip()
        if user_input in ["1", "0"]:
            return int(user_input)
        print("Invalid input. Please enter 1 for True or 0 for False.")


def main():
    generate_config_file()
    service = PileusAPIService(debug=False)

    if service.authenticate():
        logging.info("Authentication successful.")

        while True:
            print("\nMain Menu:")
            print("1. Onboarding")
            print("2. API ID (with customer Name)")
            print("3. Assets")
            print("4. Alerts")
            print("5. Exit")
            parent_choice = get_valid_input(
                "Enter choice: ", ["1", "2", "3", "4", "5"])

            if parent_choice == "1":
                while True:
                    print("\nOnboarding Menu:")
                    print("1. Get List of Users")
                    print("2. Get Users and Roles")
                    print("3. Onboard AWS Account")
                    print("4. Onboard AWS Account for MSP")
                    print("5. Back to Main Menu")
                    choice = get_valid_input(
                        "Enter choice: ", ["1", "2", "3", "4", "5"])

                    if choice == "1":
                        users = service.get_list_of_users()
                        print(json.dumps(users, indent=4)
                              if users else "Failed to retrieve users.")
                    elif choice == "2":
                        users_with_roles = service.get_users_and_roles()
                        print(json.dumps(users_with_roles, indent=4)
                              if users_with_roles else "Failed to retrieve users with roles.")
                    elif choice == "3":
                        account_id = get_valid_input("Enter Account ID: ")
                        account_name = get_valid_input("Enter Account Name: ")
                        service.onboard_aws_account(account_id, account_name)
                    elif choice == "4":
                        account_id = get_valid_input("Enter Account ID: ")
                        account_name = get_valid_input("Enter Account Name: ")
                        bucket_name = get_valid_input(
                            f"Enter Bucket Name: (default: cur-{account_id}) ", allow_empty=True)
                        bucket_region = get_valid_input(
                            "Enter Bucket Region: (default: us-east-1) ", allow_empty=True)
                        account_type = get_valid_input(
                            "Enter Account Type (dedicated (1) / shared (0)): ", ["1", "0"])
                        reseller_customer_id = get_valid_input(
                            "Enter Reseller Customer ID (optional): ", allow_empty=True)
                        reseller_customer_name = get_valid_input(
                            "Enter Reseller Customer Name: ", allow_empty=False)
                        is_customer_self_managed = get_boolean_input(
                            "Is Customer Self Managed? (1=True / 0=False): ")
                        reseller_customer_domain = get_valid_input(
                            "Enter Reseller Customer Domain (required for self-managed customer): ", allow_empty=not is_customer_self_managed)
                        auto_assign_linked_accounts = get_boolean_input(
                            "Auto Assign Linked Accounts? (1=True / 0=False): ")
                        excluded_linked_account_match = get_valid_input(
                            "Excluded Linked Account Match (optional): ", allow_empty=True)

                        service.onboard_aws_account_msp(
                            account_id, account_name, bucket_name, bucket_region, account_type, reseller_customer_id, reseller_customer_name,
                            is_customer_self_managed, reseller_customer_domain, auto_assign_linked_accounts,
                            excluded_linked_account_match)

                    elif choice == "5":
                        break
            elif parent_choice == "5":
                print("Exiting.")
                break
            else:
                print("Feature not implemented yet.")
    else:
        logging.error("Authentication failed.")


if __name__ == "__main__":
    main()
