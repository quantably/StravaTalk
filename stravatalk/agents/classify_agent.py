"""
Simplified classification agent using instructor directly.
"""

from enum import Enum
from pydantic import BaseModel, Field
import instructor


class QueryType(str, Enum):
    """Classification for SQL queries."""
    TEXT = "text"  # Regular SQL query, text response only
    TEXT_AND_TABLE = "text_and_table"  # SQL query with table display + text
    CLARIFY = "clarify"  # Need more information
    UNSUPPORTED = "unsupported"  # Cannot be answered with SQL


class QueryClassifyOutput(BaseModel):
    """Output schema for classification."""
    query_type: QueryType = Field(..., description="Type of query")
    explanation: str = Field(..., description="Brief explanation of classification")


def create_classification_agent(client: instructor.client, model: str = "gpt-4o-mini", current_date: str = None, **kwargs):
    """Creates a classification agent using instructor directly."""
    
    def classify_query(query: str) -> QueryClassifyOutput:
        """Classify if a query can be answered with SQL."""
        
        # Add current date context if provided
        date_context = ""
        if current_date:
            date_context = f"\nCURRENT DATE: {current_date}\nUse this as the reference point for relative dates like 'last week', 'this month', etc.\n"
        
        system_prompt = f"""You classify user queries about Strava fitness data to determine how they should be answered.
{date_context}

The Strava database has an 'activities' table with these columns: 
- id, name, distance, moving_time, elapsed_time, total_elevation_gain, type, start_date

Classification options:
- TEXT: Queries that likely yield a single metric or summary that works best as conversational text
- TEXT_AND_TABLE: Queries that produce multiple records and would benefit from table display + supporting text
- CLARIFY: Ambiguous queries that need more information to correctly classify
- UNSUPPORTED: Cannot be answered with SQL or available data

Examples:

TEXT queries (single values/summaries):
- "total distance this month" → Single number with context
- "my fastest 5k" → One activity with details
- "how many swims in 2024" → Count with encouragement
- "average running pace last week" → Single calculated value
- "Find my highest elevation cycling activity" → Single activity, no date range but can assume it's across all dates

TEXT_AND_TABLE queries (multiple records):
- "show me last 10 runs" → List of activities with details
- "activities over 10k" → Multiple matching activities
- "all runs in January" → List of runs with dates/distances
- "my cycling activities this year" → Multiple cycling records
- "show my most popular activities" → Can assume across all time periods and popular meaning frequency of activity type

CLARIFY queries:
- "show me my activities" (too vague - which ones?)
- "compare my performance" (compared to what?)
- "what's my longest activity" (this is ambiguous - does longest mean distance or time?)
- "what's my average pace" (too vague - across which activity type(s))

UNSUPPORTED queries:
- Weather, nutrition, non-activity data, unrelated topics
- Queries for sports that are unsupported i.e. NOT mappable to anything in the following list: AlpineSki, BackcountrySki, Badminton, Canoeing, Crossfit, EBikeRide, Elliptical, EMountainBikeRide, Golf, GravelRide, Handcycle, HighIntensityIntervalTraining, Hike, IceSkate, InlineSkate, Kayaking, Kitesurf, MountainBikeRide, NordicSki, Pickleball, Pilates, Racquetball, Ride, RockClimbing, RollerSki, Rowing, Run, Sail, Skateboard, Snowboard, Snowshoe, Soccer, Squash, StairStepper, StandUpPaddling, Surfing, Swim, TableTennis, Tennis, TrailRun, Velomobile, VirtualRide, VirtualRow, VirtualRun, Walk, WeightTraining, Wheelchair, Windsurf, Workout, Yoga

IMPORTANT: If the answer would naturally be multiple rows/records, use TEXT_AND_TABLE. If it's a single value or summary, use TEXT.
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