"""
Simplified SQL agent using instructor directly.
"""

from typing import List, Dict, Any
from pydantic import BaseModel, Field
import instructor


class SQLAgentOutput(BaseModel):
    """Output schema for SQL generation."""
    sql_query: str = Field(..., description="Generated SQL query")
    explanation: str = Field(..., description="Brief explanation of what the query does")


def create_sql_agent(client: instructor.client, model: str = "gpt-4o-mini", current_date: str = None, **kwargs):
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
        
        # Add current date context if provided
        date_context = ""
        if current_date:
            date_context = f"\nCURRENT DATE: {current_date}\nUse this as the reference point for relative dates like 'last week', 'this month', etc.\n"

        system_prompt = f"""You convert natural language queries about Strava activities into SQL.
{date_context}
DATABASE SCHEMA:
{schema_description}

RULES:
- Use the exact column names from the schema above
- Generate complete PostgreSQL queries with NO parameter placeholders
- For count queries, use COUNT(*) or COUNT(column_name)
- For date filtering, use start_date with proper date comparisons
- Activity types are strings like 'Run', 'Swim', 'Ride'
- For activity distance queries e.g. show my 5k runs. Acccount for the fact that GPS is innacurate and 1% in either direction e.g. 4950m to 5050m
- If no time period is mentioned, assume it's across all the data

UNIT CONVERSIONS (when appropriate):
- Distance: meters to km with 'distance / 1000 AS distance_km'
- Time: seconds to minutes with 'moving_time / 60 AS moving_time_minutes'
- Pace: different units for different activities. Running = min/km. Everything else = km/h.

EXAMPLES:
- "How many runs this year?" → SELECT COUNT(*) FROM activities WHERE type = 'Run' AND start_date >= '2025-01-01'
- "My swim activities" → SELECT * FROM activities WHERE type = 'Swim'
- "Average run pace in Nov 23" → SELECT FLOOR(AVG(moving_time/distance*1000)/60)||':'||LPAD(ROUND(MOD(AVG(moving_time/distance*1000)::numeric,60))::text,2,'0')||'/km' FROM activities WHERE type='Run' AND start_date>='2023-11-01' AND start_date<'2023-12-01' AND distance>0;
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
