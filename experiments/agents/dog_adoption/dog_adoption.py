import asyncio
import os
import random
from uuid import uuid4
import requests

from suql.agent import postprocess_suql

from worksheets.agent import Agent
from worksheets.environment import get_genie_fields_from_ws
from worksheets.interface_utils import conversation_loop
from worksheets.knowledge import SUQLKnowledgeBase, SUQLParser, SUQLReActParser

# Define your APIs
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

adoption_search_client = AdoptionSearch()

# Define path to the prompts

current_dir = os.path.dirname(os.path.realpath(__file__))
prompt_dir = os.path.join(current_dir, "prompts")

# Define Knowledge Base
# TODO - define knowledge base

# Define the agent
dog_adoption_bot = Agent(
    botname="Dog Adoption Assistant",
    description="You are a dog adoptionassistant. You can help future dog owners with deciding a dog breed suited to their needs and finding nearby adoption postings",
    prompt_dir=prompt_dir,
    starting_prompt="""Hello! I'm the Dog Adoption Assistant. I can help you with :
- Finding a suitable dog breed: just say find me dog breeds
- Searching for dog adoption listings nearby. 
- Asking me any question related to dog breeds and adopting a new dog.

How can I help you today? 
""",
    args={},
    api=[adoption_search_client.get_matching_breeds, adoption_search_client.get_pet_details],
    #knowledge_base=suql_knowledge, — TODO
    #knowledge_parser=suql_parser, — TODO
).load_from_gsheet(
    gsheet_id="TODO", # TODO
)

# Run the conversation loop
asyncio.run(conversation_loop(dog_adoption_bot, "dog_adoption_bot.json"))
