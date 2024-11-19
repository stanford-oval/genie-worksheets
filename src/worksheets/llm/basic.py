import datetime
import os
from typing import Any, Dict, List, Optional, Tuple

from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain.schema import HumanMessage, StrOutputParser, SystemMessage
from langchain_community.callbacks.manager import get_openai_callback
from langchain_community.chat_models.azureml_endpoint import (
    AzureMLChatOnlineEndpoint,
    AzureMLEndpointApiType,
    CustomOpenAIChatContentFormatter,
)
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from langchain_together import ChatTogether
from loguru import logger

current_dir = os.path.dirname(os.path.realpath(__file__))

date_today = datetime.date.today().strftime("%Y-%m-%d")
logfile = os.path.join(current_dir, "..", "..", "logs", f"worksheets-{date_today}.log")

logger.add(logfile)

INSTRUCTION_START = "<|startofinstruction|>"
INSTRUCTION_END = "<|endofinstruction|>"
PROMPT_START = "<|startofinput|>"
PROMPT_END = "<|endofinput|>"
USER_EXAMPLE_START = "<|startofexampleuser|>"
USER_EXAMPLE_END = "<|endofexampleuser|>"
AI_EXAMPLE_START = "<|startofexampleai|>"
AI_EXAMPLE_END = "<|endofexampleai|>"

azure_config_params = {
    "api_key": os.getenv("AZURE_OPENAI_WS_KEY"),
    "azure_endpoint": os.getenv("AZURE_WS_ENDPOINT"),
    "api_version": os.getenv("AZURE_WS_API_VERSION"),
}

llama_config_params = {
    "endpoint_api_key": os.getenv("AZURE_LLAMA_KEY"),
    "endpoint_url": os.getenv("AZURE_LLAMA_ENDPOINT"),
    "endpoint_api_type": AzureMLEndpointApiType.serverless,
    "content_formatter": CustomOpenAIChatContentFormatter(),
}


def load_prompt(prompt_file: str) -> Tuple[str, str]:
    with open(prompt_file, "r") as f:
        text = f.read()
        system_prompt = (
            text.split(INSTRUCTION_START)[1].split(INSTRUCTION_END)[0].strip()
        )
        prompt = text.split(PROMPT_START)[1].split(PROMPT_END)[0].strip()

    return system_prompt, prompt


def get_examples(example_path: str) -> List[Tuple[Any, Any]]:
    if not os.path.exists(example_path):
        return []
    with open(example_path, "r") as f:
        text = f.read()

    # in a file there are multiple examples, each user example is followed by an AI example
    lines = text.split("\n")
    user_examples = []
    user_example_start = False
    for line in lines:
        if USER_EXAMPLE_START in line:
            user_example = line.split(USER_EXAMPLE_START)[1]
            user_example_start = True
        elif USER_EXAMPLE_END in line:
            user_example = user_example + line.split(USER_EXAMPLE_END)[0]
            user_example = user_example.strip()
            user_examples.append(user_example)
            user_example_start = False
        else:
            if user_example_start:
                user_example += "\n" + line

    ai_examples = []
    ai_example_start = False
    for line in lines:
        if AI_EXAMPLE_START in line:
            ai_example = line.split(AI_EXAMPLE_START)[1]
            ai_example_start = True
        elif AI_EXAMPLE_END in line:
            ai_example = ai_example + line.split(AI_EXAMPLE_END)[0]
            ai_example = ai_example.strip()
            ai_examples.append(ai_example)
            ai_example_start = False
        else:
            if ai_example_start:
                ai_example += "\n" + line

    return list(zip(user_examples, ai_examples))


async def llm_generate(
    prompt_path: str,
    prompt_inputs: Dict[str, Any],
    prompt_dir: Optional[str] = None,
    example_path: Optional[str] = None,
    model_name: str = "azure/gpt-4o",
    stream=False,
    **llm_params,
) -> str:
    if prompt_dir is None:
        prompt_dir = os.path.join(current_dir, "..", "prompts")
    if "azure/" in model_name:
        llm = AzureChatOpenAI(
            azure_deployment=model_name.replace("azure/", ""),
            streaming=stream,
            **azure_config_params,
            **llm_params,
        )
    elif "together" in model_name:
        llm = ChatTogether(
            model=model_name.replace("together/", ""),
            streaming=stream,
            **llm_params,
        )
    elif "llama" in model_name:
        llm = AzureMLChatOnlineEndpoint(
            deployment_name=model_name.replace("llama/", ""),
            streaming=stream,
            **llama_config_params,
            **llm_params,
        )
    else:
        llm = ChatOpenAI(
            model=model_name,
            streaming=stream,
            **llm_params,
        )

    system_prompt, prompt = load_prompt(os.path.join(prompt_dir, prompt_path))
    if example_path:
        examples = get_examples(os.path.join(prompt_dir, example_path, prompt_path))
    else:
        examples = []

    messages = [
        SystemMessagePromptTemplate.from_template(
            system_prompt, template_format="jinja2"
        )
    ]

    for example in examples:
        messages.append(HumanMessage(content=example[0]))
        messages.append(SystemMessage(content=example[1]))

    messages.append(
        HumanMessagePromptTemplate.from_template(prompt, template_format="jinja2")
    )

    prompt_template = ChatPromptTemplate.from_messages(messages)

    filled_prompt = await prompt_template.ainvoke(prompt_inputs)
    filled_prompt_str = ""

    for message in filled_prompt.messages:
        filled_prompt_str += message.content + "\n"
    logger.info(f"Prompt===========:\n{filled_prompt_str}")

    chain = prompt_template | llm | StrOutputParser()

    with get_openai_callback() as cb:
        parsed_output = await chain.ainvoke(prompt_inputs)

        logger.info(
            f"Total token usage: prompt tokens: {cb.prompt_tokens}, completion tokens: {cb.completion_tokens}"
        )
        logger.info(f"Total cost: {cb.total_cost:.6f}")

    logger.info(f"Output: {parsed_output}")

    return parsed_output
