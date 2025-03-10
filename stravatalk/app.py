import streamlit as st
from dotenv import load_dotenv

from atomic_agents.lib.components.agent_memory import AgentMemory
from atomic_agents.agents.base_agent import BaseAgentInputSchema, BaseAgentOutputSchema
from orchestrator import (
    initialize_agents,
    classify_query,
    convert_to_sql,
    run_query,
    generate_response,
)

import pandas as pd

from agents.response_agent import (
    ResponseAgentInput,
    SQLQueryResult,
)


def create_interface():
    st.set_page_config(page_title="StravaTalk", page_icon="🏃‍♂️", layout="centered")

    st.title("StravaTalk 🏃‍♂️")

    load_dotenv()

    # Initialize session state for shared memory
    if "shared_memory" not in st.session_state:
        st.session_state.shared_memory = AgentMemory()
        initial_message = "Welcome to the Strava Data Assistant! I can help you analyze your Strava activities. How can I assist you today?"
        st.session_state.shared_memory.add_message(
            role="assistant",
            content=BaseAgentOutputSchema(chat_message=initial_message),
        )

    # Initialize agents if not already in session state
    if "agents" not in st.session_state:
        st.session_state.agents = initialize_agents(st.session_state.shared_memory)

    # Display chat messages from history on app rerun
    for message in st.session_state.shared_memory.history:
        if hasattr(message.content, "chat_message"):
            with st.chat_message(message.role):
                st.markdown(message.content.chat_message)
    # Query input
    if prompt := st.chat_input("Ask about your Strava activities..."):
        handle_query(prompt)


def process_strava_query(classify_agent, sql_agent, response_agent, user_query):
    with st.status("Processing your query...", expanded=True) as status:
        # Step 1: Classify the query
        status.write("Classifying query...")
        classification = classify_query(classify_agent, user_query)
        status.write(
            f"✓ Classification: {classification.classification} (Confidence: {classification.confidence:.2f})"
        )

        if classification.classification != "sql_appropriate":
            status.update(
                label="Query not appropriate for SQL processing", state="error"
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

        # Step 2: Convert to SQL
        status.write("Converting to SQL...")
        sql_query = convert_to_sql(sql_agent, user_query)
        if sql_query is None:
            status.update(label="No tables found in the database", state="error")
            return None, None
        status.write("✓ SQL Query generated:")
        status.code(sql_query, language="sql")

        # Step 3: Execute SQL
        status.write("Executing SQL query...")
        execution_result = run_query(sql_query)

        # Step 4: Generate response
        status.write("Generating response...")
        response, execution_result = generate_response(
            response_agent, user_query, execution_result
        )

        if not execution_result["success"]:
            status.update(
                label=f"Error: {execution_result['error_message']}", state="error"
            )
        else:
            status.write(f"✓ Query returned {execution_result['row_count']} rows")
            if execution_result["rows"] and execution_result["column_names"]:
                df = pd.DataFrame(
                    data=execution_result["rows"],
                    columns=execution_result["column_names"],
                )
                status.dataframe(df)

            status.update(label="Query processed successfully!", state="complete")

    return response


def handle_query(user_query):
    if user_query:
        try:
            # Display user message immediately
            with st.chat_message("user"):
                st.markdown(user_query)

            st.session_state.shared_memory.add_message(
                role="user", content=BaseAgentInputSchema(chat_message=user_query)
            )
            st.session_state.shared_memory.initialize_turn()

            classify_agent, sql_agent, response_agent = st.session_state.agents
            response = process_strava_query(
                classify_agent, sql_agent, response_agent, user_query
            )

            # Display assistant response immediately
            with st.chat_message("assistant"):
                st.markdown(response)

            st.session_state.shared_memory.add_message(
                role="assistant", content=BaseAgentOutputSchema(chat_message=response)
            )

        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.exception(e)


def main():
    create_interface()


if __name__ == "__main__":
    main()
