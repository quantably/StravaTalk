"""
Simplified classification agent using instructor directly.
"""

from enum import Enum
from pydantic import BaseModel, Field
import instructor


class QueryType(str, Enum):
    """Classification for SQL queries."""
    SQL = "sql"  # Regular SQL query, no visualization
    CLARIFY = "clarification"  # Need more information
    UNSUPPORTED = "unsupported"  # Cannot be answered with SQL


class QueryClassifyOutput(BaseModel):
    """Output schema for classification."""
    query_type: QueryType = Field(..., description="Type of query")
    explanation: str = Field(..., description="Brief explanation of classification")


def create_classification_agent(client: instructor.client, model: str = "gpt-4o-mini", **kwargs):
    """Creates a classification agent using instructor directly."""
    
    def classify_query(query: str) -> QueryClassifyOutput:
        """Classify if a query can be answered with SQL."""
        
        system_prompt = """You classify user queries about Strava fitness data to determine if they can be answered with SQL.

The Strava database has an 'activities' table with these columns: 
- id, name, distance, moving_time, elapsed_time, total_elevation_gain, type, start_date

MOST queries about activities, runs, workouts, distance, time, pace can be answered with SQL.

Examples of SQL-answerable queries:
- "show me last 3 runs"
- "my fastest 5k" 
- "total distance this month"
- "activities over 10k"
- "how many swims in 2024"

Classification options:
- SQL: Can be answered with SQL against the activities table
- CLARIFY: More information needed to process the query  
- UNSUPPORTED: Cannot be answered with SQL against Strava data

IMPORTANT: Most activity-related queries should be classified as SQL.
Use UNSUPPORTED only for queries about weather, nutrition, non-activity data, or completely unrelated topics.
"""

        response = client.chat.completions.create(
            model=model,
            response_model=QueryClassifyOutput,
            temperature=0.1,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Classify this query: {query}"}
            ]
        )
        return response
    
    # Return an object that mimics the original agent interface
    class SimpleAgent:
        def run(self, query: str):
            return classify_query(query)
    
    return SimpleAgent()
