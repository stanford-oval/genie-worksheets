import asyncio
import os
from uuid import uuid4

import yaml

from worksheets.agent import Agent
from worksheets.interface_utils import conversation_loop

current_dir = os.path.dirname(os.path.abspath(__file__))

with open("model_config_llama.yaml", "r") as f:
    model_config = yaml.load(f, Loader=yaml.FullLoader)


def bank_fraud_report(full_name, fraud_report, **kwargs):
    return {
        "status": "success",
        "error": None,
        "report_id": str(uuid4()),
    }


gsheet_id = "1Ia-IQJhNYUsTbob8eaVd7vwdZfHDLXzvWuogthPa8gA"

bank_fraud_agent = Agent(
    botname="bank_fraud_agent",
    description="A bank agent that customers can talk to to report fraud or suspicious activity.",
    prompt_dir=os.path.join(current_dir, "prompts"),
    starting_prompt="Hi, I'm a bank fraud agent. How can I help you today?",
    args=model_config,
    api=[],
    knowledge_base=None,
    knowledge_parser=None,
)

if __name__ == "__main__":
    agent = bank_fraud_agent.load_from_gsheet(gsheet_id)

    asyncio.run(conversation_loop(agent, "bank_fraud.json"))
