"""
Simplified response agent for creating natural language responses from SQL results.
"""

from typing import List, Optional, Dict, Any
from pydantic import Field

import instructor
from atomic_agents.agents.base_agent import BaseIOSchema, BaseAgent, BaseAgentConfig
from atomic_agents.lib.components.system_prompt_generator import SystemPromptGenerator
from atomic_agents.lib.components.agent_memory import AgentMemory


class SQLResult(BaseIOSchema):
    """Schema for SQL execution results."""

    query: str = Field(..., description="Original natural language query")
    sql_query: str = Field(..., description="SQL query that was executed")
    success: bool = Field(..., description="Whether query executed successfully")
    error_message: Optional[str] = Field(
        None, description="Error message if query failed"
    )
    column_names: Optional[List[str]] = Field(
        None, description="Names of result columns"
    )
    rows: Optional[List[Dict[str, Any]]] = Field(
        None, description="Result rows (up to 5 for context)"
    )
    row_count: Optional[int] = Field(None, description="Total number of rows returned")
    has_visualization: bool = Field(
        False, description="Whether results will be visualized"
    )


class ResponseAgentInput(BaseIOSchema):
    """Input schema for response generation."""

    query: str = Field(..., description="Original natural language query")
    sql_result: SQLResult = Field(..., description="SQL execution results")


class ResponseAgentOutput(BaseIOSchema):
    """Output schema for response generation."""

    response: str = Field(..., description="Natural language response to the query")


def create_response_agent(
    client: instructor.client,
    model: str = "gpt-4o-mini",
    memory: Optional[AgentMemory] = None,
) -> BaseAgent:
    """Creates a response agent for Strava queries."""

    return BaseAgent(
        BaseAgentConfig(
            client=client,
            memory=memory,
            model=model,
            system_prompt_generator=SystemPromptGenerator(
                background=[
                    "You create helpful, motivating responses about Strava fitness data.",
                    "You interpret SQL results and present them in a user-friendly way.",
                ],
                steps=[
                    "Review the original query and SQL results",
                    "Extract key insights from the data",
                    "Format the information in a clear, helpful way",
                    "Adjust your response based on whether visualization will be provided",
                ],
                output_instructions=[
                    "Use a friendly, encouraging tone",
                    "Present data clearly with proper units, recognizing column names now include unit information:",
                    "  - Columns ending with _km are in kilometers",
                    "  - Columns ending with _minutes are in minutes",
                    "  - Columns with pace_min_mi are in minutes per mile format",
                    "Format time values in HH:MM:SS format (e.g., 1:23:45 instead of 83.75 minutes)",
                    "Format pace values as MM:SS when presenting them (e.g., 8:30 min/mi rather than 8.5 min/mi)",
                    "If visualization will be shown, focus on insights rather than describing all data points",
                    "Keep answers concise but complete",
                    "If SQL failed, explain the issue in user-friendly terms",
                ],
            ),
            input_schema=ResponseAgentInput,
            output_schema=ResponseAgentOutput,
        )
    )
