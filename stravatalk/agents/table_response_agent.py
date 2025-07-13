"""
Table response agent for TEXT_AND_TABLE queries using instructor directly.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import instructor


class SQLResult(BaseModel):
    """Schema for SQL execution results."""
    query: str = Field(..., description="Original natural language query")
    sql_query: str = Field(..., description="SQL query that was executed")
    success: bool = Field(..., description="Whether query executed successfully")
    error_message: Optional[str] = Field(None, description="Error message if query failed")
    column_names: Optional[List[str]] = Field(None, description="Names of result columns")
    rows: Optional[List[Dict[str, Any]]] = Field(None, description="Result rows")
    row_count: Optional[int] = Field(None, description="Total number of rows returned")
    has_visualization: bool = Field(False, description="Whether visualization was created")


class TableResponseOutput(BaseModel):
    """Output schema for table response generation."""
    response: str = Field(..., description="Supporting text to accompany the table")


def create_table_response_agent(client: instructor.client, model: str = "gpt-4o-mini", current_date: str = None, **kwargs):
    """Creates a table response agent using instructor directly."""
    
    def generate_table_response(query: str, sql_result: SQLResult) -> TableResponseOutput:
        """Generate supporting text for table data."""
        
        # Add current date context if provided
        date_context = ""
        if current_date:
            date_context = f"\nCURRENT DATE: {current_date}\nUse this as the reference point for relative dates in your responses.\n"
        
        system_prompt = f"""You create concise supporting text for table data from Strava fitness queries.
{date_context}

The table will be displayed to the user alongside your text response. Your job is to:
- Provide context and highlights from the data
- Point out interesting patterns or achievements
- Be encouraging about fitness activities
- Keep it brief since the detailed data is in the table

GUIDELINES:
- Be conversational and encouraging about fitness activities
- Highlight key insights from the data (totals, averages, trends)
- If the query failed, explain what went wrong in simple terms
- If no data was found, explain this clearly and encourage more activity
- Use fitness terminology appropriately
- Keep responses concise - the table shows the details

FORMATTING:
- Use **bold** for key numbers and metrics
- Include units (km, miles, minutes, etc.)
- Format times in readable format (e.g., "2 hours 30 minutes")
- Use bullet points sparingly, only when helpful

TONE:
- Friendly and supportive
- Focus on achievements and progress
- Encourage continued activity
- Avoid being overly technical
"""

        # Build context from SQL result
        context = f"""
Query: "{query}"
SQL: {sql_result.sql_query}
Success: {sql_result.success}
"""

        if sql_result.success:
            context += f"Results: {sql_result.row_count} rows returned\n"
            if sql_result.rows:
                context += f"Column names: {sql_result.column_names}\n"
                # Show first few rows for context
                context += f"Sample data: {sql_result.rows[:3]}\n"
        else:
            context += f"Error: {sql_result.error_message}\n"

        response = client.chat.completions.create(
            model=model,
            response_model=TableResponseOutput,
            temperature=0.3,  # Slightly higher for more natural responses
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Create supporting text for this table query result:\n{context}"}
            ]
        )
        return response
    
    # Return an object that mimics the original agent interface  
    class SimpleAgent:
        def run(self, query: str, sql_result: SQLResult):
            return generate_table_response(query, sql_result)
    
    return SimpleAgent()