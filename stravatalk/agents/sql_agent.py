"""
Simplified SQL agent for converting natural language queries to SQL.
"""

from typing import Optional, List, Dict, Any
from pydantic import Field

import instructor
from atomic_agents.agents.base_agent import BaseAgent, BaseAgentConfig, BaseIOSchema
from atomic_agents.lib.components.system_prompt_generator import SystemPromptGenerator
from atomic_agents.lib.components.agent_memory import AgentMemory


class TableDefinition(BaseIOSchema):
    """Definition of a table in the database."""

    name: str = Field(..., description="Name of the table")
    columns: List[Dict[str, Any]] = Field(..., description="Columns in the table")


class SQLAgentInput(BaseIOSchema):
    """Simplified input schema for SQL generation."""

    query: str = Field(..., description="Natural language query to convert to SQL")
    table_definitions: List[TableDefinition] = Field(
        ..., description="Database schema information"
    )
    needs_visualization: bool = Field(
        False, description="Whether visualization is needed for this query"
    )


class SQLAgentOutput(BaseIOSchema):
    """Simplified output schema for SQL generation."""

    sql_query: str = Field(..., description="Generated SQL query")
    explanation: str = Field(
        ..., description="Brief explanation of what the query does"
    )


def create_sql_agent(
    client: instructor.client,
    model: str = "gpt-4o-mini",
    memory: Optional[AgentMemory] = None,
):
    """Creates a simplified agent for converting natural language to SQL."""

    return BaseAgent(
        config=BaseAgentConfig(
            client=client,
            model=model,
            memory=memory,
            system_prompt_generator=SystemPromptGenerator(
                background=[
                    "You convert natural language queries about Strava activities into SQL.",
                    "You have access to the database schema to create accurate queries.",
                ],
                steps=[
                    "Analyze the natural language query",
                    "Identify relevant tables and columns from the schema",
                    "Transform units directly in SQL:",
                    "  - Convert distance from meters to kilometers: 'distance / 1000 AS distance_km'",
                    "  - Convert time from seconds to minutes: 'moving_time / 60 AS moving_time_minutes'",
                    "  - Convert elapsed time from seconds to minutes: 'elapsed_time / 60 AS elapsed_time_minutes'",
                    "  - Calculate pace in minutes per mile when both distance and moving_time are available: '(moving_time / 60) / (distance / 1609.34) AS pace_min_mi'",
                    "Create a SQL query that correctly answers the question",
                    "Include relevant additional columns that might be helpful",
                    "For specific distance queries add a +/- 2% margin of error to query",
                ],
                output_instructions=[
                    "Return a valid PostgreSQL query against the Strava database",
                    "Use PostgreSQL syntax and %s parameter placeholders (NOT ? placeholders)",
                    "Do NOT include any WHERE clauses with athlete_id - this will be added automatically",
                    "Always apply unit conversions in your SQL (km, minutes, pace)",
                    "When including distance and moving_time, also calculate pace_min_km",
                    "Use clear column aliases that indicate the unit (e.g., distance_km, moving_time_minutes)",
                    "Provide a brief explanation of what the query does",
                    "Add comments to explain any complex parts of the query",
                ],
            ),
            input_schema=SQLAgentInput,
            output_schema=SQLAgentOutput,
            model_api_parameters={"temperature": 0.1},
        )
    )
