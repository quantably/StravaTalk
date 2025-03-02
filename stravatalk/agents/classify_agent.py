"""
Classification agent for determining if queries are appropriate for SQL processing.
Specialized for Strava activity data queries.

This agent is responsible for classifying queries related to Strava activities.
"""

from enum import Enum
from typing import List, Optional
from atomic_agents.agents.base_agent import BaseIOSchema, BaseAgent, BaseAgentConfig
from atomic_agents.lib.components.system_prompt_generator import SystemPromptGenerator
from atomic_agents.lib.components.agent_memory import AgentMemory
from pydantic import Field
import instructor


################
# Input Schema #
################


class QueryClassifyInput(BaseIOSchema):
    """Input schema for the classification agent."""

    query: str = Field(..., description="The natural language query to classify")
    context: Optional[str] = Field(
        None,
        description="Optional additional context about the conversation or user's intent",
    )


################
# Output Schema #
################


class QueryClassify(str, Enum):
    """Classifications for queries."""

    SQL_APPROPRIATE = "sql_appropriate"
    NOT_SQL_APPROPRIATE = "not_sql_appropriate"
    CLARIFICATION_NEEDED = "clarification_needed"


class QueryClassifyOutput(BaseIOSchema):
    """Output schema for the classification agent."""

    classification: QueryClassify = Field(
        ..., description="The classification of the query"
    )
    confidence: float = Field(..., description="Confidence in the classification (0-1)")
    reasoning: str = Field(
        ..., description="Detailed explanation of the classification decision"
    )
    strava_tables: Optional[List[str]] = Field(
        None,
        description="Relevant Strava data tables for this query if SQL-appropriate",
    )
    reformulation: Optional[str] = Field(
        None,
        description="Suggested reformulation if query could be made SQL-appropriate",
    )
    data_needed: Optional[List[str]] = Field(
        None, description="Types of data needed to answer this query"
    )


#######################
# SQL Classification Agent #
#######################


def create_classification_agent(
    client: instructor.client, memory: AgentMemory, model: str = "gpt-4o-mini"
) -> BaseAgent:
    """Creates and configures a query classification agent for Strava data."""

    return BaseAgent(
        config=BaseAgentConfig(
            client=client,
            model=model,
            memory=memory,
            system_prompt_generator=SystemPromptGenerator(
                background=[
                    "You are a specialized agent for classifying user queries about Strava fitness data.",
                    "Your job is to determine if a query can be answered using SQL against a Strava database.",
                    "You have deep knowledge about fitness activities, training metrics, and Strava's data model.",
                ],
                steps=[
                    "Analyze the query to understand the user's intent",
                    "Determine if the query is asking for factual data that exists in the Strava database",
                    "Consider if the query requires calculations or aggregations that SQL can perform",
                    "Identify if the query needs information outside the database schema",
                    "Determine which Strava database tables would be relevant for answering the query",
                    "Consider any ambiguities or clarifications needed",
                ],
                output_instructions=[
                    "Classify the query as SQL_APPROPRIATE, NOT_SQL_APPROPRIATE, or CLARIFICATION_NEEDED",
                    "Provide a confidence score between 0 and 1",
                    "Explain your reasoning in detail",
                    "If SQL_APPROPRIATE, list the relevant Strava tables needed",
                    "If NOT_SQL_APPROPRIATE or CLARIFICATION_NEEDED, suggest a reformulation if possible",
                    "List types of data needed to answer the query",
                ],
            ),
            input_schema=QueryClassifyInput,
            output_schema=QueryClassifyOutput,
        )
    )
