import argparse
import asyncio
import json
import os
import random
import sys
from copy import deepcopy
from glob import glob
from queue import PriorityQueue

import openai
from loguru import logger
from tqdm import tqdm, trange

from worksheets.annotation_utils import get_agent_action_schemas, get_context_schema
from worksheets.chat import generate_next_turn
from worksheets.environment import (
    GenieContext,
    GenieRuntime,
    GenieWorksheet,
    get_genie_fields_from_ws,
)
from worksheets.modules import CurrentDialogueTurn

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
sys.path.append(CURRENT_DIR)

from bank_fraud import bank_fraud
from trip import trip
from trivia import trivia

logger.remove()
logger.add(
    os.path.join(CURRENT_DIR, "bank_fraud_report.log"),
    format="{time} {level} {message}",
    level="INFO",
)


def create_parser():
    parser = argparse.ArgumentParser(description="Convert STARv2 data to JSON")
    parser.add_argument(
        "--input",
        type=str,
        help="Path to the STARv2 data directory",
        required=True,
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Path to the output JSON file",
        required=True,
    )
    parser.add_argument(
        "--domain",
        type=str,
        help="Domain of the conversation to run",
        choices=domain_to_load.keys(),
        required=True,
    )
    parser.add_argument(
        "--conv_id",
        type=int,
        help="Conversation ID to run",
        required=False,
    )
    parser.add_argument(
        "--sample",
        type=int,
        help="Number of conversations to run",
        required=False,
    )
    return parser


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


def load_state_bank_fraud(slots: dict, bot: GenieRuntime, *args, **kwargs):
    bot.reset()
    for key, value in slots.items():
        if slots[key] == "forgot":
            slots[key] = "NA"
    first_auth = False
    second_auth = False
    if slots.get("AccountNumber") or slots.get("PIN"):
        first_auth = True

    if (
        slots.get("DateOfBirth")
        or slots.get("SecurityAnswer1")
        or slots.get("SecurityAnswer2")
    ):
        second_auth = True

    name = slots.get("FullName")
    if name is None:
        name = slots.get("Name")
    main = f"""main = Main(
    full_name={repr(name)},
    fraud_report={repr(slots.get("FraudReport"))},
    first_authentication_details={"first_authentication" if first_auth else repr(None)},
    second_authentication_details={"second_authentication" if second_auth else repr(None)},
)
"""

    first_authentication = f"""first_authentication = FirstAuthentication(
    account_number={repr(slots.get("AccountNumber"))},
    pin={repr(slots.get("PIN"))},
    )
"""
    second_authentication = f"""second_authentication = SecondAuthentication(
    date_of_birth={repr(slots.get("DateOfBirth"))},
    security_answer_1={repr(slots.get("SecurityAnswer1"))},
    security_answer_2={repr(slots.get("SecurityAnswer2"))}
)
"""

    slot_to_worksheet = {
        "FullName": main,
        "AccountNumber": first_authentication,
        "PIN": first_authentication,
        "FraudReport": main,
        "DateOfBirth": second_authentication,
        "SecurityAnswer1": second_authentication,
        "SecurityAnswer2": second_authentication,
        "Name": main,
    }

    code_to_execute = []
    for slot in slots:
        if slot_to_worksheet[slot] not in code_to_execute:
            code_to_execute.append(slot_to_worksheet[slot])

    priority_order = [
        first_authentication,
        second_authentication,
        main,
    ]
    q = PriorityQueue()
    for code in code_to_execute:
        q.put((priority_order.index(code), code))

    code_to_execute = []
    while not q.empty():
        code_to_execute.append(q.get()[1])

    code_to_execute = "\n".join(code_to_execute)
    local_context = GenieContext({})
    bot.execute(code_to_execute, local_context=local_context, sp=True)

    for key, value in local_context.context.items():
        if isinstance(value, GenieWorksheet):
            for field in get_genie_fields_from_ws(value):
                if (
                    field.value is not None
                    and field.value != "NA"
                    and not isinstance(field.value, GenieWorksheet)
                ):
                    # field.perform_action(bot, local_context)
                    field.action_performed = True
            if value.is_complete(bot, local_context):
                value.perform_action(bot, local_context)
                value.action_performed = True

    bot.context.update(local_context.context)

    return bot


def load_state_trip(
    slots: dict,
    bot: GenieRuntime,
    next_step: bool | None = None,
    current_step: int | None = None,
    *args,
    **kwargs,
):
    bot.reset()
    travel_information = f"""travel_information = TravelInformation(travel_mode={repr(slots.get("TravelMode"))}, departure_location={repr(slots.get("DepartureLocation"))}, arrival_location={repr(slots.get("ArrivalLocation"))}, departure_time={repr(slots.get("DepartureTime"))})"""

    if next_step is not None:
        continue_details = f"""continue_details = ContinueDetails(show_next_step={repr(next_step)}, current_step={repr(current_step)})"""
    else:
        continue_details = ""

    slot_to_worksheet = {
        "TravelMode": travel_information,
        "DepartureLocation": travel_information,
        "ArrivalLocation": travel_information,
        "DepartureTime": travel_information,
    }

    code_to_execute = []
    for slot in slots:
        if slot_to_worksheet[slot] not in code_to_execute:
            code_to_execute.append(slot_to_worksheet[slot])

    if next_step is not None:
        code_to_execute.append(continue_details)

    priority_order = [travel_information, continue_details]
    q = PriorityQueue()
    for code in code_to_execute:
        q.put((priority_order.index(code), code))

    code_to_execute = []
    while not q.empty():
        code_to_execute.append(q.get()[1])

    code_to_execute = "\n".join(code_to_execute)
    local_context = GenieContext({})
    bot.execute(code_to_execute, local_context=local_context, sp=True)

    local_context_copy = deepcopy(local_context)

    for key, value in local_context_copy.context.items():
        if isinstance(value, GenieWorksheet):
            for field in get_genie_fields_from_ws(value):
                if (
                    field.value is not None
                    and field.value != "NA"
                    and not isinstance(field.value, GenieWorksheet)
                ):
                    # field.perform_action(bot, local_context)
                    field.action_performed = True
            if value.is_complete(bot, local_context):
                value.perform_action(bot, local_context)
                value.action_performed = True

    if "continue_details" in local_context.context and current_step is not None:
        local_context.context["continue_details"].show_next_step = None

    bot.context.update(local_context.context)

    return bot


def load_state_trivia(
    slots: dict,
    bot: GenieRuntime,
    current_q: int | None,
    user_answer: str | None = None,
    continue_trivia: bool | None = None,
    correct_answer: str | None = None,
    *args,
    **kwargs,
):
    bot.reset()
    q = slots.get("QuestionNum")

    main = f"""main = Main(starting_question_number={repr(q)}, current_question_number={current_q}, correct_answers={correct_answer})"""

    if current_q is not None:
        question = trivia.ask_question(int(current_q))["question"]
        question_answer = f"""question_answer = QuestionAnswer(question={repr(question)}, user_answer={repr(user_answer)}, continue_trivia={repr(continue_trivia)})"""
    else:
        question_answer = ""

    slot_to_worksheet = {
        "QuestionNum": main,
    }

    code_to_execute = []
    for slot in slots:
        if slot_to_worksheet[slot] not in code_to_execute:
            code_to_execute.append(slot_to_worksheet[slot])

    if current_q is not None:
        code_to_execute.append(question_answer)

    priority_order = [main, question_answer]
    q = PriorityQueue()
    for code in code_to_execute:
        q.put((priority_order.index(code), code))

    code_to_execute = []
    while not q.empty():
        code_to_execute.append(q.get()[1])

    code_to_execute = "\n".join(code_to_execute)
    local_context = GenieContext({})
    bot.execute(code_to_execute, local_context=local_context, sp=True)

    for key, value in local_context.context.items():
        if isinstance(value, GenieWorksheet):
            for field in get_genie_fields_from_ws(value):
                if (
                    field.value is not None
                    and field.value != "NA"
                    and not isinstance(field.value, GenieWorksheet)
                ):
                    # field.perform_action(bot, local_context)
                    field.action_performed = True
            if value.is_complete(bot, local_context):
                value.perform_action(bot, local_context)
                value.action_performed = True

    if "question_answer" in local_context.context and continue_trivia is not None:
        local_context.context["question_answer"].user_answer = None

    bot.context.update(local_context.context)

    return bot


domain_to_load = {
    "bank_fraud_report": load_state_bank_fraud,
    "trip": load_state_trip,
    "trivia": load_state_trivia,
}


async def run_one_file(file, output_path, domain):
    output_path = os.path.join(output_path, f"{domain}_{os.path.basename(file)}")
    if os.path.exists(output_path):
        return
    with open(file, "r") as f:
        data = json.load(f)

    if domain == "bank_fraud_report":
        bot = bank_fraud.bank_fraud_agent.load_from_gsheet(bank_fraud.gsheet_id)
    elif domain == "trivia":
        bot = trivia.trivia_agent.load_from_gsheet(trivia.gsheet_id)
    elif domain == "trip":
        bot = trip.trip_agent.load_from_gsheet(trip.gsheet_id)

    dlg_history = []

    q_num = None
    user_answer = None
    continue_trivia = None
    num_correct = 0

    next_step = None
    current_step = None

    turn_num = 0
    start_turn = 0
    prev_agent_utterance = None
    current_state = {}
    for event in tqdm(data["Events"], leave=False):
        if event["Action"] == "utter":
            bot = domain_to_load[domain](
                current_state,
                bot=bot,
                next_step=next_step,
                current_step=current_step,
                user_answer=user_answer,
                correct_answer=num_correct,
                current_q=q_num,
                continue_trivia=continue_trivia,
            )

            if turn_num != 0:
                bot.dlg_history.append(
                    CurrentDialogueTurn(system_response=prev_agent_utterance)
                )

            if turn_num >= start_turn:
                await generate_next_turn(event["Text"], bot)

            dlg_history.append(
                {
                    "state": bot.dlg_history[-1] if len(bot.dlg_history) else [],
                    "event": event,
                }
            )

            # specific to trivia
            if "APIName" in event and "Constraints" in event:
                if (
                    len(event["Constraints"]) > 0
                    and "QuestionNum" in event["Constraints"][0]
                ):
                    q_num = event["Constraints"][0]["QuestionNum"]

            if "PredictedBeliefState" in event:
                current_state = event["PredictedBeliefState"]
            turn_num += 1

            # specific to trivia
            if (
                "PrimaryItem" in event
                and "Text" in event
                and event["Text"].lower() in ["incorrect", "correct"]
            ):
                if event["Text"].lower() == "incorrect":
                    user_answer = "incorrect"
                else:
                    user_answer = event["PrimaryItem"]["Answer"]
                    num_correct += 1

            # specific to trip
            if "ActionLabel" in event:
                if "user_trip_directions_continue" in event["ActionLabel"]:
                    next_step = True
                    if current_step is None:
                        current_step = 1
                    current_step += 1
                elif "user_trip_directions_no_continue" in event["ActionLabel"]:
                    next_step = False
                    if current_step is None:
                        current_step = 1

        if event["Agent"] == "Wizard" and "Text" in event:
            prev_agent_utterance = event["Text"]
            if event["Action"] == "pick_suggestion":
                dlg_history[-1]["sys_act"] = event["ActionLabel"]

    dlg_history_jsonified = []
    for turn in dlg_history:
        if "state" in turn:
            state = turn["state"]
            if state:
                state = convert_to_json([state])
            dlg_history_jsonified.append(
                {
                    "state": state,
                    "event": turn["event"],
                    "sys_act": turn.get("sys_act", None),
                }
            )

    with open(output_path, "w") as f:
        json.dump(dlg_history_jsonified, f, indent=2)


async def main(input_path, output_path, domain, conv_id, sample=None):
    files = glob(os.path.join(input_path, "*.json"))

    found_files = []

    if conv_id is not None:
        # conv_id is provided, so we only run one conversation
        with open(os.path.join(input_path, f"{conv_id}.json"), "r") as f:
            data = json.load(f)
        found_files.append(os.path.join(input_path, f"{conv_id}.json"))
    else:
        # conv_id is not provided, collect all conversations from the input path
        for file in files:
            with open(file, "r") as f:
                data = json.load(f)

            if domain.split("_")[0] in data["Scenario"]["Domains"]:
                if len(data["Scenario"]["WizardCapabilities"]) == 1:
                    if domain == "bank_fraud_report":
                        capabilities = data["Scenario"]["WizardCapabilities"][0]
                        if (
                            capabilities["Domain"] == domain.split("_")[0]
                            and capabilities["Task"] == domain
                        ):
                            found_files.append(file)
                    else:
                        found_files.append(file)

        if sample is not None:
            found_files = random.sample(found_files, sample)

        # for file in tqdm(found_files):
        #     try:
        #         await run_one_file(file, output_path, domain)
        #     except openai.BadRequestError:
        #         continue

        batch_size = 10
        for batch in trange(0, len(found_files), batch_size):
            tasks = []
            for file in found_files[batch : batch + batch_size]:
                tasks.append(run_one_file(file, output_path, domain))

            for task in tqdm(
                asyncio.as_completed(tasks), total=len(tasks), leave=False
            ):
                try:
                    await task
                except openai.BadRequestError:
                    continue


if __name__ == "__main__":
    try:
        args = create_parser().parse_args()
        asyncio.run(
            main(args.input, args.output, args.domain, args.conv_id, args.sample)
        )

    except Exception:
        import pdb
        import sys
        import traceback

        extype, value, tb = sys.exc_info()
        traceback.print_exc()
        pdb.post_mortem(tb)
        traceback.print_exc()
        pdb.post_mortem(tb)
