"""
Simplified classification agent for determining if queries are appropriate for SQL processing
and if visualization is needed.
"""

from enum import Enum
from typing import Optional, List
from pydantic import Field

import instructor
from atomic_agents.agents.base_agent import BaseIOSchema, BaseAgent, BaseAgentConfig
from atomic_agents.lib.components.system_prompt_generator import SystemPromptGenerator
from atomic_agents.lib.components.agent_memory import AgentMemory


# Simplified Classification Enum
class QueryType(str, Enum):
    """Classification for SQL queries."""

    SQL = "sql"  # Regular SQL query, no visualization
    VIZ = "visualization"  # SQL query with visualization
    CLARIFY = "clarification"  # Need more information
    UNSUPPORTED = "unsupported"  # Cannot be answered with SQL


class QueryClassifyInput(BaseIOSchema):
    """Input schema for classification."""

    query: str = Field(..., description="The natural language query to classify")


class QueryClassifyOutput(BaseIOSchema):
    """Output schema for classification."""

    query_type: QueryType = Field(..., description="Type of query")
    explanation: str = Field(..., description="Brief explanation of classification")
    # Only used for visualization queries
    x_column: Optional[str] = Field(
        None, description="Column for x-axis if visualization needed"
    )
    y_columns: Optional[List[str]] = Field(
        None, description="Columns for y-axis if visualization needed"
    )
    chart_type: Optional[str] = Field(
        None, description="Suggested chart type (line, bar, scatter, etc.)"
    )


def create_classification_agent(
    client: instructor.client,
    memory: Optional[AgentMemory] = None,
    model: str = "gpt-4o-mini",
) -> BaseAgent:
    """Creates a classification agent for Strava queries."""

    return BaseAgent(
        config=BaseAgentConfig(
            client=client,
            model=model,
            memory=memory,
            system_prompt_generator=SystemPromptGenerator(
                background=[
                    "You classify user queries about Strava fitness data to determine if they can be answered with SQL.",
                    "You also identify if a query would benefit from visualization. Look for words like plot, visualise, chart, graph, etc.",
                    "The Strava database has an 'activities' table with these columns: id, name, distance, moving_time, elapsed_time, total_elevation_gain, type, start_date.",
                    "SQL transforms raw values to user-friendly units:",
                    "  - distance_km: distance in kilometers (converted from meters)",
                    "  - moving_time_minutes: moving time in minutes (converted from seconds)",
                    "  - elapsed_time_minutes: elapsed time in minutes (converted from seconds)",
                    "  - pace_min_mi: pace in minutes per mile (calculated from moving_time and distance)",
                    "When suggesting columns for visualizations, prefer these transformed columns with proper units.",
                ],
                steps=[
                    "Analyze the query to understand what the user is asking",
                    "Determine if the query can be answered using SQL against a Strava database",
                    "Check if visualization would help answer the query better",
                    "If visualization is needed, select ONLY the relevant columns for visualization - do not include all columns",
                    "Pay attention to any visualization preferences expressed by the user (chart type, etc.)",
                ],
                output_instructions=[
                    "Classify the query as one of the following:",
                    "- SQL: Can be answered with SQL, no visualization needed",
                    "- VIZ: Can be answered with SQL and would benefit from visualization",
                    "- CLARIFY: More information needed to process the query",
                    "- UNSUPPORTED: Cannot be answered with SQL against Strava data",
                    "If visualization is needed:",
                    "  - Use transformed columns with proper units when available:",
                    "    * distance_km instead of distance",
                    "    * moving_time_minutes instead of moving_time",
                    "    * elapsed_time_minutes instead of elapsed_time",
                    "    * pace_min_mi when pace information is relevant",
                    "  - For y-columns, choose ONLY the specific metrics mentioned in the query",
                    "  - Do NOT include multiple metrics with different scales (like distance and elevation) in the same plot",
                    "  - Limit to 1-2 y-columns maximum that are directly relevant to the query",
                    "  - If the query asks to compare specific metrics, only include those metrics",
                    "  - If the query doesn't specify metrics, choose the most relevant single metric",
                    "  - For tracking specific data points over time, use 'scatter' chart type (points) instead of 'line'",
                    "  - For queries related to distances e.g. plot all my 5k runs, use time on the y-axis and date on the x-axis",
                    "  - For running queries, include pace_min_mi when available",
                    "  - Pay attention to user preferences about chart types (e.g., if they ask for a scatter plot, bar chart, etc.)",
                    "Provide a brief explanation of your classification",
                ],
            ),
            input_schema=QueryClassifyInput,
            output_schema=QueryClassifyOutput,
            model_api_parameters={"temperature": 0.1},
        )
    )
