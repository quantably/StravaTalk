import os

import openai
import instructor

from agents.classify_agent import (
    create_classification_agent,
    QueryClassifyInput,
)
from agents.response_agent import (
    create_response_agent,
    ResponseAgentInput,
    SQLQueryResult,
)
from agents.sql_agent import (
    create_nl_to_sql_agent,
    NLToSQLAgentInputSchema,
)
from utils.db_utils import get_table_definitions, execute_sql_query


def initialize_agents(shared_memory=None):
    api_key = os.getenv("OPENAI_API_KEY")
    client = instructor.from_openai(openai.OpenAI(api_key=api_key))
    model = "gpt-4o-mini"

    # Create agents with a shared memory
    classify_agent = create_classification_agent(
        client, memory=shared_memory, model=model
    )
    sql_agent = create_nl_to_sql_agent(client, memory=shared_memory, model=model)
    response_agent = create_response_agent(client, memory=shared_memory, model=model)

    return classify_agent, sql_agent, response_agent


def classify_query(classify_agent, query):
    classification_input = QueryClassifyInput(query=query)
    classification = classify_agent.run(classification_input)
    return classification


def convert_to_sql(sql_agent, query):
    custom_instructions = """
    Include a margin of error for distance queries to account for GPS inaccuracies.
    The margin of error should be 1% of the distance in meters or 2% for shorter distances (e.g. 1 mile).
    You only need to do this if the query is about a specific distance.
    """

    tables = get_table_definitions(os.getenv("STRAVA_DB_PATH"))
    sql_input = NLToSQLAgentInputSchema(
        query=query,
        database_type="sqlite",
        table_definitions=tables,
        custom_instructions=custom_instructions,
    )
    sql_conversion = sql_agent.run(sql_input)
    return sql_conversion.sql_query


def run_query(sql_query):
    db_path = os.getenv("STRAVA_DB_PATH")
    return execute_sql_query(db_path, sql_query)


def generate_response(response_agent, query, execution_result):
    """Generate a response based on the SQL execution result."""
    sql_result = SQLQueryResult(
        query=query,
        sql_query=execution_result.get("sql_query", ""),
        success=execution_result["success"],
        error_message=execution_result["error_message"],
        column_names=execution_result["column_names"],
        rows=execution_result["rows"],
        row_count=execution_result["row_count"],
    )

    response_input = ResponseAgentInput(original_query=query, sql_result=sql_result)
    response = response_agent.run(response_input)
    return response.markdown_output, execution_result
