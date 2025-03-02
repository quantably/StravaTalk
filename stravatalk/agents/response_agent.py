from typing import List, Optional, Dict, Any

from pydantic import Field

from atomic_agents.agents.base_agent import BaseIOSchema, BaseAgent, BaseAgentConfig
from atomic_agents.lib.components.system_prompt_generator import SystemPromptGenerator
from atomic_agents.lib.components.agent_memory import AgentMemory
import instructor

################
# Input Schema #
################


class SQLQueryResult(BaseIOSchema):
    """Schema representing SQL query execution results."""

    query: str = Field(
        ..., description="The original natural language query from the user"
    )
    sql_query: str = Field(..., description="The SQL query that was executed")
    success: bool = Field(..., description="Whether the query executed successfully")
    error_message: Optional[str] = Field(
        None, description="Error message if the query failed"
    )
    column_names: Optional[List[str]] = Field(
        None, description="Names of columns in the result set"
    )
    rows: Optional[List[Dict[str, Any]]] = Field(
        None, description="List of rows returned by the query"
    )
    row_count: Optional[int] = Field(None, description="Number of rows returned")


class ResponseAgentInput(BaseIOSchema):
    """Input schema for the response generation agent."""

    original_query: str = Field(
        ..., description="The original natural language query from the user"
    )
    sql_result: SQLQueryResult = Field(
        ..., description="Results from executing the SQL query"
    )


################
# Output Schema #
################


class ResponseAgentOutput(BaseIOSchema):
    """Output schema for the response generation agent."""

    answer: str = Field(..., description="Natural language answer to the user's query")
    markdown_output: str = Field(
        ...,
        description="Formatted markdown response that may include lists, tables etc.",
    )


#########################
# Response Agent Creator #
#########################


def create_response_agent(
    client: instructor.client,
    model: str = "gpt-4o-mini",
    memory: AgentMemory = None,
) -> BaseAgent:
    """Creates and configures a response generation agent for Strava data."""

    return BaseAgent(
        BaseAgentConfig(
            client=client,
            memory=memory,
            model=model,
            system_prompt_generator=SystemPromptGenerator(
                background=[
                    "You are a knowledgeable and motivating Strava fitness assistant.",
                    "Your role is to interpret SQL query results about Strava fitness data and provide helpful, engaging responses.",
                    "You understand fitness metrics, training concepts, and how to present data in a motivational way.",
                ],
                steps=[
                    "Review the original query to understand what the user wants to know",
                    "Analyze the SQL results in detail",
                    "Extract key insights, patterns, and notable data points",
                    "Determine if a table is an appropriate format for the results",
                    "Format the data in a way that's easy to understand",
                    "Craft a response that's both informative and motivational",
                ],
                output_instructions=[
                    "Use a friendly, encouraging tone",
                    "Present data clearly, with proper formatting and units",
                    "Round numbers to appropriate precision (e.g., distances to 2 decimal places)",
                    "Always convert distances to km",
                    "Format pace in hour:min:sec per km/mile rather than decimal minutes",
                    "Format time in hour:min:sec",
                    "Add any accompanying text, explanations or a table (if appropriate) to the markdown_output field",
                    "Keep answers concise but complete",
                    "If SQL failed, explain the issue clearly without technical jargon",
                    "If the query was deemed not appropriate for SQL, explain that you can only answer questions about Strava data.",
                    "If the query was deemed CLARIFICATION_NEEDED, ask for more information.",
                ],
            ),
            input_schema=ResponseAgentInput,
            output_schema=ResponseAgentOutput,
        )
    )
