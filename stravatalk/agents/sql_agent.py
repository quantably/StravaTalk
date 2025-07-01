"""
Simplified SQL agent using instructor directly.
"""

from typing import List, Dict, Any
from pydantic import BaseModel, Field
import instructor


# No longer need input schema - using simple function parameters


class SQLAgentOutput(BaseModel):
    """Output schema for SQL generation."""
    sql_query: str = Field(..., description="Generated SQL query")
    explanation: str = Field(..., description="Brief explanation of what the query does")


def create_sql_agent(client: instructor.client, model: str = "gpt-4o-mini", **kwargs):
    """Creates a simplified SQL generation function using instructor directly."""
    
    def generate_sql(query: str, table_definitions: List[Dict[str, Any]]) -> SQLAgentOutput:
        """Generate SQL query from natural language."""
        
        # Build schema description
        schema_description = ""
        for table in table_definitions:
            schema_description += f"\nTable: {table['name']}\n"
            schema_description += f"Description: {table['description']}\n"
            schema_description += "Columns:\n"
            for col in table['columns']:
                schema_description += f"  - {col['name']} ({col['type']}): {col['description']}\n"
        
        system_prompt = f"""You convert natural language queries about Strava activities into SQL.

DATABASE SCHEMA:
{schema_description}

RULES:
- Use the exact column names from the schema above
- Generate complete PostgreSQL queries with NO parameter placeholders
- Do NOT include athlete_id filters - these are added automatically  
- For count queries, use COUNT(*) or COUNT(column_name)
- For date filtering, use start_date with proper date comparisons
- Activity types are strings like 'Run', 'Swim', 'Ride'

UNIT CONVERSIONS (when appropriate):
- Distance: meters to km with 'distance / 1000 AS distance_km'
- Time: seconds to minutes with 'moving_time / 60 AS moving_time_minutes'

EXAMPLES:
- "How many runs this year?" → SELECT COUNT(*) FROM activities WHERE type = 'Run' AND start_date >= '2025-01-01'
- "My swim activities" → SELECT * FROM activities WHERE type = 'Swim'
"""

        response = client.chat.completions.create(
            model=model,
            response_model=SQLAgentOutput,
            temperature=0.1,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Convert this natural language query to SQL: {query}"}
            ]
        )
        return response
    
    # Return an object that mimics the original agent interface
    class SimpleAgent:
        def run(self, query: str, table_definitions: List[Dict[str, Any]]):
            return generate_sql(query, table_definitions)
    
    return SimpleAgent()
