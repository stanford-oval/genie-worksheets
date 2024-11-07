import json
import os
import sys

import chainlit as cl
from loguru import logger

from worksheets.agent import Agent
from worksheets.annotation_utils import get_agent_action_schemas, get_context_schema
from worksheets.chat_chainlit import generate_next_turn_cl
from worksheets.modules import CurrentDialogueTurn

current_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(current_dir, "..", ".."))


from dog_adoption.dog_adoption import (
    AdoptionSearch,
    prompt_dir,
    suql_knowledge,
    suql_parser,
)

logger.remove()

logger.add(
    os.path.join(current_dir, "..", "user_logs", "user_logs.log"), rotation="1 day"
)

# dog adoption bot
unhappy_paths = [
    "**- Once you have selected a restaurant, ask for a different restaurant**",
    "**- Before confirming the booking, create a special request for your booking (e.g., this is for anniversary)**",
    "**- Change your mind about the restaurant criteria (e.g. change the cuisine you want to eat)**",
    "**- Change the restaurant booking details in the middle of the booking (eg. change the restaurant, change the number of people, or change the time)**",
]

unhappy_paths = "\n" + "\n".join(unhappy_paths)


def convert_to_json(dialogue: list[CurrentDialogueTurn]):
    json_dialogue = []
    for turn in dialogue:
        json_turn = {
            "user": turn.user_utterance,
            "bot": turn.system_response,
            "turn_context": get_context_schema(turn.context),
            "global_context": get_context_schema(turn.global_context),
            "system_action": get_agent_action_schemas(turn.system_action),
            "user_target_sp": turn.user_target_sp,
            "user_target": turn.user_target,
            "user_target_suql": turn.user_target_suql,
        }
        json_dialogue.append(json_turn)
    return json_dialogue


@cl.on_chat_start
async def initialize():
    cl.user_session.set(
        "bot",
        Agent(
            botname="DogAdoptionBot",
            description="You an assistant who helps users find a dog breed suitable to their needs and search for dog adoption listings near them. You can ask me anything about dog breeds and search for dog adoption listings.",
            prompt_dir=prompt_dir,
            starting_prompt="""Hello! I'm DogAdoptionBot. I'm here to help you find a furry friend by researching dog breeds for your needs and searching for adoption listings. What would you like to do?""",
            args={},
            api=[AdoptionSearch.get_matching_breeds, AdoptionSearch.get_pet_details],
            knowledge_base=suql_knowledge,
            knowledge_parser=suql_parser,
        ).load_from_gsheet(
            gsheet_id="TODO",
        ),
    )

    if not os.path.exists(os.path.join(current_dir, "user_conversation")):
        os.mkdir(os.path.join(current_dir, "user_conversation"))
    user_id = cl.user_session.get("id")
    logger.info(f"Chat started for user {user_id}")
    if not os.path.exists(os.path.join(current_dir, "user_conversation", user_id)):
        os.mkdir(os.path.join(current_dir, "user_conversation", user_id))
    await cl.Message(
        f"Here is your user id: **{user_id}**\n"
        + cl.user_session.get("bot").starting_prompt
        + f"\n\nPlease be a difficult user who asks several questions, here are some examples: {unhappy_paths}"
    ).send()


@cl.on_message
async def get_user_message(message):
    bot = cl.user_session.get("bot")
    await generate_next_turn_cl(message.content, bot)

    cl.user_session.set("bot", bot)

    response = bot.dlg_history[-1].system_response
    await cl.Message(response).send()


@cl.on_chat_end
def on_chat_end():
    user_id = cl.user_session.get("id")
    if not os.path.exists(
        os.path.join(
            current_dir,
            "user_conversation",
            user_id,
        )
    ):
        os.mkdir(
            os.path.join(
                current_dir,
                "user_conversation",
                user_id,
            )
        )

    bot = cl.user_session.get("bot")
    if len(bot.dlg_history):
        with open(
            os.path.join(
                current_dir,
                "user_conversation",
                user_id,
                "conversation.json",
            ),
            "w",
        ) as f:
            json.dump(convert_to_json(bot.dlg_history), f)
    else:
        os.rmdir(os.path.join(current_dir, "user_conversation", user_id))

    logger.info(f"Chat ended for user {user_id}")
