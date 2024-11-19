import asyncio
import os

import yaml

from worksheets.agent import Agent
from worksheets.interface_utils import conversation_loop

current_dir = os.path.dirname(os.path.abspath(__file__))

with open("model_config_llama.yaml", "r") as f:
    model_config = yaml.load(f, Loader=yaml.FullLoader)


def next_step_instruction(
    current_step, travel_mode, departure_location, arrival_location, departure_time
):
    current_step = int(current_step)
    travel_mode = travel_mode.lower()
    if travel_mode == "transit":
        instructions = [
            "Walk to the bus stop at Forbes and Murray.",
            "Take the 61A until the last stop.",
            "After you get off the stop, turn left and walk down Craig St for 2 blocks.",
            "Your destination will be on the left.",
        ]
    elif travel_mode == "driving":
        instructions = [
            "Go east on Forbes towards Murray",
            "Turn right and drive for 1.6 kilometers and turn left on Murray",
            "Drive for 700 meters until you reach Wilkins Avenue",
            "Your destination will be on the right",
        ]
    elif travel_mode == "walking":
        instructions = [
            "Walk 2 blocks east on Forbes Avenue, towards Murray",
            "Turn right and walk for 3 blocks until you arrive at the church",
            "Turn left and walk for 5 minutes until you see the park on your left.",
            "Your destination will be on the right",
        ]

    if current_step == len(instructions):
        return {"instruction": f"This is the last step: {instructions[-1]}"}
    return {"instruction": instructions[current_step - 1]}


def next_step_detailed(
    current_step, travel_mode, departure_location, arrival_location, departure_time
):
    current_step = int(current_step)
    travel_mode = travel_mode.lower()
    if travel_mode == "transit":
        instructions = [
            "Walk east from your starting location towards the bus stop at Forbes and Murray. You will walk 3 blocks and the stop will be in front of a large brown church.",
            "Take the 61A until the final stop, which will be at Forbes and Craig. It will take approximately 20 minutes and 13 stops.",
            "After you get off the stop, turn right at the Starbucks and walk down Craig St for 2 blocks.",
            "After you pass the Chinese Restaurant (green brick building), your destination will be on the left just before the crosswalk.",
        ]
    elif travel_mode == "driving":
        instructions = [
            "Drive east (towards the tall brown building) on Forbes towards Murray",
            "Turn right at the Starbucks and drive for 1.6 kilometers. Once you see a brown church, turn left on Murray",
            "Drive for 700 meters until you reach Wilkins Avenue. It will be the first traffic light you see.",
            "Your destination will be on the right just after the fire station.",
        ]
    elif travel_mode == "walking":
        instructions = [
            "Walk 2 blocks east on Forbes Avenue towards Murray. You will pass a fire station on your left.",
            "Turn right and walk for 3 blocks until you arrive at the tall brown church. Cross the street after arriving at the church.",
            "Turn left and walk for 5 minutes. You will pass a school on your right. Keep going until you see the park on your left.",
            "Your destination will be on the right besides the Starbucks.",
        ]

    if current_step == len(instructions):
        return {"detailed_instruction": f"This is the last step: {instructions[-1]}"}

    return {"detailed_instruction": instructions[current_step - 1]}


gsheet_id = "12dVJdhCFuIi020r1zgQplfA8He5OxYOzCRWelgCyc0c"

trip_agent = Agent(
    botname="trip_agent",
    description="A trip agent that helps you plan your trip.",
    prompt_dir=os.path.join(current_dir, "prompts"),
    starting_prompt="Hi, I'm a trip agent. How can I help you today?",
    args=model_config,
    api=[],
    knowledge_base=None,
    knowledge_parser=None,
)

if __name__ == "__main__":
    agent = trip_agent.load_from_gsheet(gsheet_id)

    asyncio.run(conversation_loop(agent, "trip_conversation.json"))
