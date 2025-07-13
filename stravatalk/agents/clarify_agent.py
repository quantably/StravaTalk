"""
Clarification agent for CLARIFY queries using instructor directly.
"""

from pydantic import BaseModel, Field
import instructor


class ClarificationOutput(BaseModel):
    """Output schema for clarification generation."""
    response: str = Field(..., description="Clarification questions to ask the user")


def create_clarification_agent(client: instructor.client, model: str = "gpt-4o-mini", current_date: str = None, **kwargs):
    """Creates a clarification agent using instructor directly."""
    
    def generate_clarification(query: str) -> ClarificationOutput:
        """Generate clarification questions for ambiguous queries."""
        
        # Add current date context if provided
        date_context = ""
        if current_date:
            date_context = f"\nCURRENT DATE: {current_date}\nUse this as the reference point for relative dates when suggesting time periods.\n"
        
        system_prompt = f"""You help users clarify ambiguous queries about their Strava fitness data.
{date_context}

When a query is too vague, missing important details, or just ambiguous, ask specific questions to help the user get the information they want.

The Strava database has an 'activities' table with these columns:
- id, name, distance, moving_time, elapsed_time, total_elevation_gain, type, start_date

GUIDELINES:
- Ask at most 2-3 specific questions maximum
- Be friendly and helpful
- Suggest common options when appropriate
- Focus on the most important missing information
- Help users understand what data is available

EXAMPLES:

Query: "show me my activities"
Response: "I'd be happy to show your activities! To give you the most relevant results, could you let me know:
- What type of activities? (runs, cycling, swimming, etc.)
- Any particular time period? (this week, last month, this year)
- How many activities would you like to see?"

Query: "compare my performance"
Response: "I can help you compare your performance! To provide a useful comparison, I need to know:
- What activity type do you want to compare? (runs, cycling, etc.)
- What would you like to compare to? (your previous activities, a specific time period, or distance?)
- What metrics are you interested in? (pace, distance, elevation gain, etc.)"

Query: "What's my longest activity"
Response: "I'd be happy to help with that. Could you clarify if by longest you mean in distance or time?"

TONE:
- Friendly and encouraging
- Concise but helpful
- Make it easy for the user to provide the needed information
"""

        response = client.chat.completions.create(
            model=model,
            response_model=ClarificationOutput,
            temperature=0.3,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Generate clarification questions for this query: {query}"}
            ]
        )
        return response
    
    # Return an object that mimics the original agent interface  
    class SimpleAgent:
        def run(self, query: str):
            return generate_clarification(query)
    
    return SimpleAgent()