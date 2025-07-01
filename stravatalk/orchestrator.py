"""
Orchestrator for the StravaTalk application.
"""

import os
import pandas as pd
import openai
import instructor

from .agents.classify_agent import create_classification_agent, QueryType
from .agents.response_agent import create_response_agent, SQLResult
from .agents.sql_agent import create_sql_agent
from .utils.db_utils import get_table_definitions, execute_sql_query


def initialize_agents(shared_memory=None):
    """Initialize all agents."""
    api_key = os.getenv("OPENAI_API_KEY")
    client = instructor.from_openai(openai.OpenAI(api_key=api_key))
    model = "gpt-4o-mini"

    classify_agent = create_classification_agent(
        client, memory=shared_memory, model=model
    )
    sql_agent = create_sql_agent(client, memory=shared_memory, model=model)
    response_agent = create_response_agent(client, memory=shared_memory, model=model)

    return classify_agent, sql_agent, response_agent


def process_query(classify_agent, sql_agent, response_agent, query, athlete_id=None, debug_container=None):
    """Process a user query through the agent pipeline with optional user filtering."""
    from .utils.debug_utils import show_agent_debug, show_sql_debug, show_orchestrator_debug

    # Step 1: Classify the query
    classification = classify_agent.run(query)

    # Debug: Show classification step
    if debug_container:
        debug_input = {"query": query}
        show_agent_debug("Classification Agent", debug_input, classification, debug_container)

    # Initialize result dictionary
    result = {
        "classification": classification,
        "success": True,
        "response_text": None,
        "data": None,
        "chart_info": None,
        "sql_query": None,
    }

    # Exit early if query isn't appropriate for SQL
    if classification.query_type in [QueryType.CLARIFY, QueryType.UNSUPPORTED]:
        result["response_text"] = classification.explanation
        
        # Debug: Show early exit case
        if debug_container:
            debug_container.info(f"Query classified as {classification.query_type} - no SQL generation needed")
        
        return result

    # Step 2: Generate SQL if appropriate
    tables = get_table_definitions()

    try:
        sql_output = sql_agent.run(query, tables)
        sql_query = sql_output.sql_query
        
        # Basic validation - just check we got a non-empty query
        if not sql_query or len(sql_query.strip()) < 10:
            raise ValueError(f"SQL agent returned invalid query: {sql_query}")
        
    except Exception as e:
        logger.error(f"❌ SQL agent failed: {e}")
        result["success"] = False
        result["response_text"] = f"Sorry, there was an error generating the SQL query: {str(e)}"
        return result

    # Debug: Show SQL generation step
    if debug_container:
        debug_input = {"query": query, "table_definitions": tables}
        show_agent_debug("SQL Agent", debug_input, sql_output, debug_container)

    # Store SQL query in result
    result["sql_query"] = sql_query

    # Debug: Log the generated SQL query
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🔍 Classification result: {classification.query_type}")
    logger.info(f"🔍 Generated SQL Query: {sql_query}")
    logger.info(f"🔍 User filtering with athlete_id: {athlete_id}")

    # Step 3: Execute SQL query with user filtering
    execution_result = execute_sql_query(sql_query, athlete_id=athlete_id)
    execution_result["sql_query"] = sql_query
    
    # Debug: Show SQL execution
    if debug_container:
        show_sql_debug(sql_query, execution_result, debug_container)
    
    # Debug: Print execution result
    print(f"🔍 Query execution success: {execution_result.get('success')}")
    if not execution_result.get('success'):
        print(f"🔍 Query error: {execution_result.get('error_message')}")

    # Handle SQL execution failure
    if not execution_result["success"]:
        result["success"] = False
        sql_result = SQLResult(
            query=query,
            sql_query=sql_query,
            success=False,
            error_message=execution_result["error_message"],
            rows=None,
            column_names=None,
            row_count=0,
            has_visualization=False,
        )
        response_output = response_agent.run(query, sql_result)
        
        # Debug: Show response generation for error case
        if debug_container:
            debug_input = {"query": query, "sql_result": sql_result}
            show_agent_debug("Response Agent (Error)", debug_input, response_output, debug_container)
        
        result["response_text"] = response_output.response
        return result

    # Convert results to DataFrame for easier manipulation
    if execution_result["success"] and execution_result["rows"]:
        df = pd.DataFrame(
            execution_result["rows"], columns=execution_result["column_names"]
        )
        result["data"] = df

    # Step 4: Generate text response
    sql_result = SQLResult(
        query=query,
        sql_query=sql_query,
        success=True,
        error_message=None,
        column_names=execution_result["column_names"],
        rows=execution_result["rows"][:25],
        row_count=execution_result["row_count"],
        has_visualization=False,
    )

    response_output = response_agent.run(query, sql_result)
    
    # Debug: Show response generation for success case
    if debug_container:
        debug_input = {"query": query, "sql_result": sql_result}
        show_agent_debug("Response Agent", debug_input, response_output, debug_container)
    
    # Debug: Show complete pipeline overview
    if debug_container:
        show_orchestrator_debug(query, classification, sql_output, execution_result, response_output, debug_container)
    
    result["response_text"] = response_output.response

    return result
