import asyncio
import os
import random

import yaml

from worksheets.agent import Agent
from worksheets.interface_utils import conversation_loop

current_dir = os.path.dirname(os.path.abspath(__file__))

with open("model_config_llama.yaml", "r") as f:
    model_config = yaml.load(f, Loader=yaml.FullLoader)


def ask_question(question_number: int):
    question_number = int(question_number)
    questions = [
        ["A ____ atom in an atomic clock beats 9,192,631,770 times a second", "cesium"],
        ["A ____ is the blue field behind the stars", "canton"],
        ["A ____ takes 33 hours to crawl one mile", "snail"],
        ["A ____ written to celebrate a wedding is called a epithalamium", "poem"],
        ["A 'sirocco' refers to a type of ____", "wind"],
        ["A 3 1/2' floppy disk measures ____ & 1/2 inches across", "three"],
        [
            "A 300,000 pound wedding dress made of platinum was once exhibited, and in the instructions from the designer was a warning. What was it",
            "do not iron",
        ],
        ["A bird in the hand is worth ____", "two in the bush"],
        ["A block of compressed coal dust used as fuel", "briquette"],
        ["A blockage in a pipe caused by a trapped bubble of air", "airlock"],
        ["A blunt thick needle for sewing with thick thread or tape", "bodkin"],
    ]

    if question_number > len(questions):
        return {"question": "No more questions available"}

    return {"question": questions[question_number - 1][0]}


def check_user_answer(question_number: int, answer: str):
    question_number = int(question_number)
    questions = [
        ["A ____ atom in an atomic clock beats 9,192,631,770 times a second", "cesium"],
        ["A ____ is the blue field behind the stars", "canton"],
        ["A ____ takes 33 hours to crawl one mile", "snail"],
        ["A ____ written to celebrate a wedding is called a epithalamium", "poem"],
        ["A 'sirocco' refers to a type of ____", "wind"],
        ["A 3 1/2' floppy disk measures ____ & 1/2 inches across", "three"],
        [
            "A 300,000 pound wedding dress made of platinum was once exhibited, and in the instructions from the designer was a warning. What was it?",
            "do not iron",
        ],
        ["A bird in the hand is worth ____", "two in the bush"],
        ["What is a block of compressed coal dust used as fuel called?", "briquette"],
        [
            "What is a blockage in a pipe caused by a trapped bubble of air called?",
            "airlock",
        ],
        [
            "What is a blunt thick needle for sewing with thick thread or tape?",
            "bodkin",
        ],
    ]

    # current_dir = os.path.dirname(os.path.realpath(__file__))
    # prompt_dir = os.path.join(current_dir, "prompts")

    # genieworksheets doesn't support async calls
    # response =llm_generate(
    #     "check_answer.prompt",
    #     {
    #         "question": questions[question_number - 1][0],
    #         "answer": questions[question_number - 1][1],
    #         "user_response": answer,
    #     },
    #     prompt_dir,
    #     model_name="azure/gpt-4o",
    #     max_tokens=100,
    #     temperature=0.0,
    # )

    # answer = re.findall(r"<answer>(.*?)</answer>", response, re.DOTALL)
    answer = random.choice(["true", "false"])
    if answer:
        answer = True if answer[0].strip().lower() == "true" else False

        return {"correct": answer}

    return {"correct": False, "correct_answer": questions[question_number - 1][1]}


gsheet_id = "1oo7tasfwNDKQp6HO2BSsXKBKikrX7ubw6qEyzT9bMuM"

trivia_agent = Agent(
    botname="trivia_agent",
    description="A trivia agent that helps you answer trivia questions.",
    prompt_dir=os.path.join(current_dir, "prompts"),
    starting_prompt="Hi, I'm a trivia agent. How can I help you today?",
    args=model_config,
    api=[],
    knowledge_base=None,
    knowledge_parser=None,
)

if __name__ == "__main__":
    agent = trivia_agent.load_from_gsheet(gsheet_id)

    asyncio.run(conversation_loop(agent, "trivia_conversation.json"))
