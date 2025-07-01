"""
Simplified response agent using instructor directly.
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


class ResponseAgentOutput(BaseModel):
    """Output schema for response generation."""
    response: str = Field(..., description="Natural language response to user")


def create_response_agent(client: instructor.client, model: str = "gpt-4o-mini", **kwargs):
    """Creates a response agent using instructor directly."""
    
    def generate_response(query: str, sql_result: SQLResult) -> ResponseAgentOutput:
        """Generate natural language response from SQL results."""
        
        system_prompt = """You create natural language responses from SQL query results for Strava fitness data.

GUIDELINES:
- Be conversational and encouraging about fitness activities
- Format numbers clearly (use commas for large numbers)
- Include relevant context from the data
- If the query failed, explain what went wrong in simple terms
- If no data was found, explain this clearly
- Use fitness terminology appropriately
- Be concise but informative

FORMATTING:
- Use **bold** for key numbers and metrics
- Use bullet points for lists when appropriate
- Include units (km, miles, minutes, etc.)
- Format times in readable format (e.g., "2 hours 30 minutes")

TONE:
- Friendly and supportive
- Focus on achievements and progress
- Encourage continued activity
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
                context += f"Sample data: {sql_result.rows[:3]}\n"  # First 3 rows
        else:
            context += f"Error: {sql_result.error_message}\n"

        response = client.chat.completions.create(
            model=model,
            response_model=ResponseAgentOutput,
            temperature=0.3,  # Slightly higher for more natural responses
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Create a response for this query result:\n{context}"}
            ]
        )
        return response
    
    # Return an object that mimics the original agent interface  
    class SimpleAgent:
        def run(self, query: str, sql_result: SQLResult):
            return generate_response(query, sql_result)
    
    return SimpleAgent()