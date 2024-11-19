from pydantic import BaseModel

from worksheets.environment import GenieRuntime
from worksheets.from_spreadsheet import gsheet_to_genie
from worksheets.knowledge import BaseSUQLParser, SUQLKnowledgeBase


class Agent(BaseModel):
    """Agent setting for GenieWorksheets"""

    # name of the agent
    botname: str

    # description of the agent. This is used for generating response
    description: str

    # directory where the prompts are stored
    prompt_dir: str

    # starting prompt for the agent to ask the user
    starting_prompt: str

    # arguments to pass to the agent for configuration
    args: dict

    # list of functions that are available to the agent for execution
    api: list

    # knowledge configuration for the agent to run queries and respond to the user
    knowledge_base: SUQLKnowledgeBase | None

    # semantic parser for knowledge queries
    knowledge_parser: BaseSUQLParser | None

    def load_from_gsheet(self, gsheet_id: str):
        """Load the agent configuration from the google sheet.

        Args:
            gsheet_id (str): The ID of the Google Sheet.

        Returns:
            GenieRuntime: An instance of GenieRuntime configured with the loaded data.
        """

        # Load Genie worksheets, databases, and types from the Google Sheet
        genie_worsheets, genie_dbs, genie_types = gsheet_to_genie(gsheet_id)

        # Create a SUQL runner if knowledge_base is provided. Suql runner is used by the
        # GenieRuntime to run queries against the knowledge base.
        if self.knowledge_base:

            def suql_runner(query, *args, **kwargs):
                return self.knowledge_base.run(query, *args, **kwargs)

        else:
            suql_runner = None

        # Create an instance of GenieRuntime with the loaded configuration
        bot = GenieRuntime(
            name=self.botname,
            prompt_dir=self.prompt_dir,
            starting_prompt=self.starting_prompt,
            description=self.description,
            args=self.args,
            api=self.api,
            suql_runner=suql_runner,
            suql_parser=self.knowledge_parser,
        )

        # Add worksheets, databases, and types to the GenieRuntime instance
        for worksheet in genie_worsheets:
            bot.add_worksheet(worksheet)

        for db in genie_dbs:
            bot.add_db_model(db)

        for genie_type in genie_types:
            bot.add_worksheet(genie_type)

        return bot
