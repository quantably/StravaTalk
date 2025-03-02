import os

from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

import openai
import instructor

from atomic_agents.lib.components.agent_memory import AgentMemory
from atomic_agents.agents.base_agent import BaseAgentInputSchema, BaseAgentOutputSchema
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
    The margin of error should be 1% of the distance in meters.
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


def process_strava_query(classify_agent, sql_agent, response_agent, user_query):
    console = Console()

    # Step 1: Classify the query
    console.print("[bold blue]Step 1: Classifying query...[/bold blue]")
    classification = classify_query(classify_agent, user_query)
    console.print(f"[bold]Classification:[/bold] {classification.classification}")
    console.print(f"[bold]Confidence:[/bold] {classification.confidence:.2f}")

    if classification.classification != "sql_appropriate":
        console.print(
            "[bold yellow]Query not appropriate for SQL processing[/bold yellow]"
        )
        sql_result = SQLQueryResult(
            query=user_query,
            sql_query="",
            success=False,
            error_message=f"Query classified as {classification.classification}",
            rows=None,
            column_names=None,
            row_count=0,
        )
        response_input = ResponseAgentInput(
            original_query=user_query, sql_result=sql_result
        )
        response = response_agent.run(response_input)
        return response.markdown_output, sql_result

    # Step 2: Convert to SQL with conversation context
    console.print("[bold blue]Step 2: Converting to SQL...[/bold blue]")
    sql_query = convert_to_sql(sql_agent, user_query)
    if sql_query is None:
        console.print("[bold red]No tables found in the database[/bold red]")
        return None, None
    console.print(Panel(sql_query, title="Generated SQL"))

    # Step 3: Execute SQL
    console.print("[bold blue]Step 3: Executing SQL query...[/bold blue]")
    execution_result = run_query(sql_query)

    # Step 4: Generate response
    console.print("[bold blue]Step 4: Generating response...[/bold blue]")
    response, execution_result = generate_response(
        response_agent, user_query, execution_result
    )

    if not execution_result["success"]:
        console.print(
            f"[bold red]SQL execution error:[/bold red] {execution_result['error_message']}"
        )
    else:
        console.print(
            f"[bold green]Query returned {execution_result['row_count']} rows[/bold green]"
        )

    return response


def main():
    """Run an interactive query session with shared memory."""
    load_dotenv()

    shared_memory = AgentMemory()

    initial_message = "Welcome to the Strava Data Assistant! I can help you analyze your Strava activities. How can I assist you today?"
    shared_memory.add_message(
        role="assistant", content=BaseAgentOutputSchema(chat_message=initial_message)
    )

    classify_agent, sql_agent, response_agent = initialize_agents(shared_memory)

    console = Console()
    console.print(
        Panel(
            initial_message,
            title="Strava Query Pipeline",
            subtitle="Type /exit to quit",
            width=console.width,
            style="bold cyan",
        )
    )

    while True:
        user_query = console.input("\n[bold blue]You:[/bold blue] ")

        # Check for exit command
        if user_query.lower() in ["/exit", "/quit", "exit", "quit"]:
            console.print("Exiting...", style="bold red")
            break

        try:
            shared_memory.add_message(
                role="user", content=BaseAgentInputSchema(chat_message=user_query)
            )
            shared_memory.initialize_turn()

            response = process_strava_query(
                classify_agent, sql_agent, response_agent, user_query
            )

            shared_memory.add_message(
                role="assistant", content=BaseAgentOutputSchema(chat_message=response)
            )

            console.print("\n[bold green]Response:[/bold green]")
            markdown_response = Markdown(response)
            console.print(Panel(markdown_response, width=console.width))

        except Exception as e:
            console.print(f"\n[bold red]Error:[/bold red] {str(e)}")
            import traceback

            console.print(traceback.format_exc())


if __name__ == "__main__":
    main()
