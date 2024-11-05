import requests

class AdoptionSearch:
    def __init__(self):
        self.base_url = 'https://api-staging.adoptapet.com/search/'
        self.api_version = '2'
        self.output_format = 'json'

    def get_search_form(self, species='dog'):
        """
        Fetches the search form data for the specified species, including breed listings.
        """
        url = f"{self.base_url}search_form"
        params = {
            'v': self.api_version,
            'output': self.output_format,
            'species': species
        }
        headers = {
            'Accept': 'application/json'
        }

        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()
    
    def get_matching_breeds(self, city_or_zip, geo_range, species='dog', breed_id=None, sex=None, age=None, color_id=None, pet_size_range_id=None):
        """
        Searches for pets based on provided criteria and returns a list of pets.
        """
        url = f"{self.base_url}pet_search"
        params = {
            'v': self.api_version,
            'output': self.output_format,
            'city_or_zip': city_or_zip,
            'geo_range': geo_range,
            'species': species,
            'breed_id': breed_id,
            'sex': sex,
            'age': age,
            'color_id': color_id,
            'pet_size_range_id': pet_size_range_id,
            'start_number': 1,
            'end_number': 50  # Pagination can be adjusted as needed
        }
        headers = {
            'Accept': 'application/json; charset=UTF8'
        }

        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()
    
    def get_pet_details(self, pet_id):
        """
        Retrieves full details for a specific pet.
        """
        url = f"{self.base_url}limited_pet_details"
        params = {
            'key': self.api_key,
            'v': self.api_version,
            'output': self.output_format,
            'pet_id': pet_id
        }
        headers = {
            'Accept': 'application/json'
        }
        
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()
    