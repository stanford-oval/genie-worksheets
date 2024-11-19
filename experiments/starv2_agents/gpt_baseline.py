import argparse
import asyncio
import json
import os
import random
from glob import glob

import openai
from bs4 import BeautifulSoup
from loguru import logger
from mappings import star_acts
from sklearn.metrics import classification_report, f1_score
from tqdm import tqdm, trange

from worksheets.llm import llm_generate

logger.remove()

current_dir = os.path.dirname(os.path.abspath(__file__))

domain = "bank_fraud"


def get_policy(domain):
    if domain == "bank_fraud_report":
        return """This outlines the policy for reporting bank fraud and handling authentication during the process:

1. **Initial Request for Information**:
   - The process begins with a request for the user's **Full Name**, **Account Number**, and **PIN**.
   - If the user is unable to provide these details, they are prompted for **additional information**:
     - **Full Name**
     - **Date of Birth**
     - **Security Answer 1** (e.g., Mother's maiden name)
     - **Security Answer 2** (e.g., Name of childhood pet)

2. **User Information Submission**:
   - If the user provides the requested information, the process continues.
   - If the user fails to provide the required information, they are again prompted, and the process either proceeds or halts based on the completeness of their response.

3. **Request for Fraud Details**:
   - Upon successful submission of initial authentication details, the system requests specific details for the fraud report.

4. **Querying the Bank Fraud Report**:
   - The system queries the **Bank Fraud Report** database to validate the user's information and report the fraud.

5. **Outcome**:
   - **Success**: If the user's details are authenticated successfully, they are informed that their fraud report has been recorded.
   - **Authentication Failure**: If the system cannot authenticate the user's information, they are informed that their identity could not be verified, and the process terminates.

This policy ensures that users go through appropriate security checks before being able to report fraud, maintaining the integrity and security of sensitive user data.
"""
    elif domain == "trip":
        return """Here is a natural language version of the policy described in the flowchart:

1. **Initial Request**:
   - The user provides essential travel information including:
     - Mode of travel (e.g., car, bus, walking).
     - Departure location.
     - Arrival location.
     - Desired departure time.

2. **Query Process**:
   - The system queries the **TripDirections** service to retrieve the required travel route and directions.

3. **Inform and Confirm**:
   - The system shares the **next simple step** of the directions with the user, one step at a time.
   - The user is asked to confirm if it is okay to proceed to the next step.
     - If the user agrees, move to the next step.
     - If the user does not agree, repeat the previous step in more **detailed instructions**.

4. **Completion**:
   - If the last step of the directions is reached, the system informs the user that the directions are complete and the process is done.
"""
    elif domain == "trivia":
        return """The image shows a flowchart for a trivia quiz process. Below is the policy for conducting this trivia game:

**Trivia Game Process Policy**

1. **Starting Point**: Request the player to provide the question number they would like to start from.

2. **Fetching a Question**: Query the trivia database for the next question based on the starting number or the current progression of the game.

3. **Question Presentation**: Present the fetched trivia question to the player.

4. **Answer Verification**:
   - Receive the player's answer.
   - Compare it with the correct answer from the trivia database.
   - Inform the player if their answer is correct or incorrect.
   
5. **Continuation Decision**:
   - Ask the player if they would like to proceed to the next question.
   - If they respond positively, repeat the process from the "Fetching a Question" step.
   - If they decide not to continue, move to the scoring step.

6. **Scoring**:
   - Once the player chooses not to continue, inform them of their final score.
   - Share the total number of questions they answered correctly and the number they got wrong.

This policy ensures an interactive, continuous, and user-driven trivia experience, allowing participants to track their performance and choose when to stop playing.
"""

    else:
        raise ValueError(f"Domain {domain} not supported")


async def run_one_file(file, output_path, domain):
    output_path = os.path.join(output_path, f"{domain}_{os.path.basename(file)}")

    if os.path.exists(output_path):
        return
    with open(file, "r") as f:
        data = json.load(f)

    acts = star_acts(domain)
    policy = get_policy(domain)

    dlg_history = []

    turn_num = 0
    start_turn = 0
    prev_agent_utterance = None
    current_state = {}
    for event in tqdm(data["Events"], leave=False):
        if event["Action"] == "utter" and event["Agent"] == "User":
            if turn_num >= start_turn:
                user_utterance = event["Text"]

                agent_acts = await llm_generate(
                    prompt_path="generate_acts.prompt",
                    prompt_dir=os.path.join(current_dir, "prompts"),
                    prompt_inputs={
                        "policy": policy,
                        "acts": acts,
                        "user_utterance": user_utterance,
                        "dialog_state": current_state,
                        "previous_agent_utterance": prev_agent_utterance,
                    },
                    model_name="llama/Meta-Llama-3-1-70B-Instruct-qszz",
                )

                soup = BeautifulSoup(agent_acts, "html.parser")
                agent_acts = soup.find_all("agent_act")[0].text.strip()

            dlg_history.append(
                {
                    "state": current_state,
                    "event": event,
                    "predicted_act": agent_acts,
                }
            )

            if "PredictedBeliefState" in event:
                current_state = event["PredictedBeliefState"]
            turn_num += 1

        if event["Agent"] == "Wizard" and "Text" in event:
            prev_agent_utterance = event["Text"]
            if event["Action"] == "pick_suggestion":
                dlg_history[-1]["sys_act"] = event["ActionLabel"]

    with open(output_path, "w") as f:
        json.dump(dlg_history, f, indent=2)


async def main(input_path, output_path, domain, sample=None):
    files = glob(os.path.join(input_path, "*.json"))
    found_files = []
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

    batch_size = 10
    for batch in trange(0, len(found_files), batch_size):
        tasks = []
        for file in found_files[batch : batch + batch_size]:
            tasks.append(run_one_file(file, output_path, domain))

        for task in tqdm(asyncio.as_completed(tasks), total=len(tasks), leave=False):
            try:
                await task
            except openai.BadRequestError:
                continue


def run_eval(input_path, domain):
    files = glob(os.path.join(input_path, f"{domain}_*.json"))

    predicted = []
    actual = []
    for file in files:
        with open(file, "r") as f:
            data = json.load(f)

        for dlg in data:
            if "predicted_act" in dlg and "sys_act" in dlg:
                if domain == "trivia":
                    if dlg["predicted_act"] == "query":
                        dlg["predicted_act"] = "trivia_ask_question"
                predicted.append(dlg["predicted_act"])
                actual.append(dlg["sys_act"])

    print(classification_report(actual, predicted))
    print(f1_score(actual, predicted, average="weighted"))
    print(f1_score(actual, predicted, average="micro"))


if __name__ == "__main__":

    def create_parser():
        parser = argparse.ArgumentParser()
        parser.add_argument("--input_path", type=str, required=True)
        parser.add_argument("--output_path", type=str, required=False)
        parser.add_argument("--domain", type=str, required=True)
        parser.add_argument("--sample", type=int, default=None)
        parser.add_argument("--run_eval", action="store_true")
        return parser

    args = create_parser().parse_args()
    if args.run_eval:
        run_eval(args.input_path, args.domain)
    else:
        asyncio.run(main(args.input_path, args.output_path, args.domain, args.sample))
