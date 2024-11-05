import requests

class DogInformation:
    def __init__(self):
        self.base_url = 'https://dogapi.dog/api/v2'
    
    def get_all_breeds(self):
        """
        Fetches a list of all breeds from the Dog API.
        """
        response = requests.get(f"{self.BASE_URL}/breeds")
        if response.status_code == 200:
            return response.json().get("data", [])
        else:
            print(f"Failed to fetch breeds. Status code: {response.status_code}")
            return []
    
    def get_breed_by_id(self, breed_id):
        """
        Fetches detailed information about a breed by its ID.
        """
        response = requests.get(f"{self.BASE_URL}/breeds/{breed_id}")
        if response.status_code == 200:
            return response.json().get("data", {})
        else:
            print(f"Failed to fetch breed {breed_id}. Status code: {response.status_code}")
            return {}
