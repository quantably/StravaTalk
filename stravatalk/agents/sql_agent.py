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


class NLToSQLAgentInputSchema(BaseIOSchema):
    """Input schema for the NL-to-SQL agent."""

    query: str = Field(..., description="Natural language query to convert to SQL")
    database_type: str = Field(
        "sqlite", description="Database type (sqlite, postgresql, mysql, etc.)"
    )
    table_definitions: List[TableDefinition] = Field(
        ..., description="Database schema information"
    )
    custom_instructions: Optional[str] = Field(
        None, description="Additional instructions for SQL generation"
    )


class NLToSQLAgentOutputSchema(BaseIOSchema):
    """Output schema for the NL-to-SQL agent."""

    sql_query: str = Field(..., description="The generated SQL query")
    explanation: str = Field(
        ..., description="Plain language explanation of what the SQL query does"
    )
    confidence_score: float = Field(
        ..., description="Confidence score of the conversion (0-1)"
    )
    warnings: Optional[List[str]] = Field(
        None, description="Potential issues or assumptions made"
    )


def create_nl_to_sql_agent(
    client: instructor.client,
    model: str = "gpt-4o-mini",
    memory: Optional[AgentMemory] = None,
):
    """
    Creates a specialized agent for converting natural language to SQL.
    """
    # Create system prompt for the agent
    system_prompt = SystemPromptGenerator(
        background=[
            "You are an expert SQL developer who specializes in converting natural language to SQL.",
            "Your task is to take a natural language query and convert it into a valid SQL query.",
            "You have access to the database schema to ensure your SQL is correct and optimized.",
            "If custom instructions are provided, you must follow them while generating SQL.",
        ],
        steps=[
            "1. Check for any custom instructions that need to be followed",
            "2. Analyze the natural language query to understand the intent",
            "3. Identify relevant tables and columns from the provided schema",
            "4. Structure a syntactically correct SQL query using proper joins and conditions",
            "5. Verify that the SQL query accurately captures the intent of the natural language query",
            "6. Ensure the query follows any provided custom instructions",
            "7. Add comments to explain complex parts of the query",
        ],
        output_instructions=[
            "Return a valid SQL query that matches the database schema",
            "Provide a plain language explanation of what the query does",
            "Include a confidence score from 0-1 on how well the conversion matches the intent",
            "List any assumptions or potential issues with the conversion as warnings",
        ],
    )

    # Create and return the agent
    return BaseAgent(
        config=BaseAgentConfig(
            client=client,
            model=model,
            memory=memory,
            system_prompt_generator=system_prompt,
            input_schema=NLToSQLAgentInputSchema,
            output_schema=NLToSQLAgentOutputSchema,
            model_api_parameters={
                "temperature": 0.1
            },  # Lower temperature for more deterministic SQL generation
        )
    )
