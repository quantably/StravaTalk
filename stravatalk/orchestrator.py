"""
Orchestrator for the StravaTalk application.
"""

import os
import pandas as pd
import openai
import instructor

from agents.classify_agent import (
    create_classification_agent,
    QueryClassifyInput,
    QueryType,
)
from agents.response_agent import create_response_agent, ResponseAgentInput, SQLResult
from agents.sql_agent import create_sql_agent, SQLAgentInput
from utils.db_utils import get_table_definitions, execute_sql_query


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


def process_query(classify_agent, sql_agent, response_agent, query):
    """Process a user query through the agent pipeline."""

    # Step 1: Classify the query
    classification = classify_agent.run(QueryClassifyInput(query=query))

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
        return result

    # Step 2: Generate SQL if appropriate
    needs_viz = classification.query_type == QueryType.VIZ
    tables = get_table_definitions(os.getenv("STRAVA_DB_PATH"))

    sql_input = SQLAgentInput(
        query=query, table_definitions=tables, needs_visualization=needs_viz
    )

    sql_output = sql_agent.run(sql_input)
    sql_query = sql_output.sql_query

    # Store SQL query in result
    result["sql_query"] = sql_query

    # Step 3: Execute SQL query
    execution_result = execute_sql_query(os.getenv("STRAVA_DB_PATH"), sql_query)
    execution_result["sql_query"] = sql_query

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
        response_input = ResponseAgentInput(query=query, sql_result=sql_result)
        response_output = response_agent.run(response_input)
        result["response_text"] = response_output.response
        return result

    # Convert results to DataFrame for easier manipulation
    if execution_result["success"] and execution_result["rows"]:
        df = pd.DataFrame(
            execution_result["rows"], columns=execution_result["column_names"]
        )
        result["data"] = df

        # Step 4: Prepare visualization data if needed
        if needs_viz and df is not None and not df.empty:
            # Verify that the column exists in the result set
            available_columns = df.columns.tolist()

            # Use the classification agent's suggested columns, but check they exist
            # First, try to use the transformed column version if requested a raw column
            x_column = classification.x_column
            # Try to find transformed version of the column if available
            if x_column not in available_columns:
                if x_column == "distance" and "distance_km" in available_columns:
                    x_column = "distance_km"
                elif (
                    x_column == "moving_time"
                    and "moving_time_minutes" in available_columns
                ):
                    x_column = "moving_time_minutes"
                elif (
                    x_column == "elapsed_time"
                    and "elapsed_time_minutes" in available_columns
                ):
                    x_column = "elapsed_time_minutes"
                else:
                    x_column = available_columns[0]  # Fallback

            y_columns = []
            if classification.y_columns:
                for y_col in classification.y_columns:
                    # Try to find transformed version of the column if available
                    if y_col not in available_columns:
                        if y_col == "distance" and "distance_km" in available_columns:
                            y_columns.append("distance_km")
                        elif (
                            y_col == "moving_time"
                            and "moving_time_minutes" in available_columns
                        ):
                            y_columns.append("moving_time_minutes")
                        elif (
                            y_col == "elapsed_time"
                            and "elapsed_time_minutes" in available_columns
                        ):
                            y_columns.append("elapsed_time_minutes")
                        elif y_col == "pace" and "pace_min_mi" in available_columns:
                            y_columns.append("pace_min_mi")
                    else:
                        y_columns.append(y_col)

            # If no y_columns found, use a reasonable default
            if not y_columns:
                # Prioritize transformed columns
                transformed_cols = [
                    col
                    for col in available_columns
                    if "distance_km" in col
                    or "time_minutes" in col
                    or "pace_min_mi" in col
                ]

                if transformed_cols:
                    y_columns = [transformed_cols[0]]
                else:
                    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
                    if numeric_cols:
                        y_columns = [numeric_cols[0]]
                    else:
                        # If no numeric columns, use the second column if available
                        y_columns = [
                            available_columns[1]
                            if len(available_columns) > 1
                            else available_columns[0]
                        ]

            # For running activities, add pace if available
            if (
                "type" in df.columns
                and "Run" in df["type"].values
                and "pace_min_mi" in available_columns
            ):
                if "pace_min_mi" not in y_columns:
                    y_columns.append("pace_min_mi")

            result["chart_info"] = {
                "x_column": x_column,
                "y_columns": y_columns,
                "chart_type": classification.chart_type or "line",
            }

    # Step 5: Generate text response
    sql_result = SQLResult(
        query=query,
        sql_query=sql_query,
        success=True,
        error_message=None,
        column_names=execution_result["column_names"],
        rows=execution_result["rows"][:25],
        row_count=execution_result["row_count"],
        has_visualization=needs_viz,
    )

    response_input = ResponseAgentInput(query=query, sql_result=sql_result)
    response_output = response_agent.run(response_input)
    result["response_text"] = response_output.response

    return result
