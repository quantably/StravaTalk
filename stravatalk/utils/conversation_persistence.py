"""
Conversation history persistence utilities.
Handles saving and loading chat history and memory across sessions.
"""

import json
import uuid
from typing import List, Dict, Any, Optional
from .db_utils import get_db_connection
from .memory import ConversationMemory
import psycopg2.extras

def generate_session_id() -> str:
    """Generate a unique session ID."""
    return str(uuid.uuid4())

def save_conversation_history(user_id: int, chat_history: List[Dict], session_id: Optional[str] = None):
    """Save conversation history to database."""
    if not session_id:
        session_id = generate_session_id()
    
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to database for saving conversation")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Clear existing history for this session
        cursor.execute(
            "DELETE FROM conversation_history WHERE user_id = %s AND session_id = %s",
            (user_id, session_id)
        )
        
        # Insert all messages
        for i, message in enumerate(chat_history):
            cursor.execute("""
                INSERT INTO conversation_history (
                    user_id, session_id, message_index, role, content, 
                    sql_query, data_summary, result_count, query_type, show_table
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                session_id,
                i,
                message["role"],
                message["text"],
                message.get("sql_query"),
                message.get("data_summary"),
                message.get("result_count", 0),
                message.get("query_type"),
                message.get("show_table", False)
            ))
        
        conn.commit()
        return session_id
        
    except Exception as e:
        print(f"Error saving conversation history: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def load_conversation_history(user_id: int, session_id: Optional[str] = None) -> tuple[List[Dict], Optional[str]]:
    """Load conversation history from database."""
    conn = get_db_connection()
    if not conn:
        return [], None
    
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        if session_id:
            # Load specific session
            cursor.execute("""
                SELECT * FROM conversation_history 
                WHERE user_id = %s AND session_id = %s 
                ORDER BY message_index
            """, (user_id, session_id))
        else:
            # Load most recent session
            cursor.execute("""
                SELECT * FROM conversation_history 
                WHERE user_id = %s AND session_id = (
                    SELECT session_id FROM conversation_history 
                    WHERE user_id = %s 
                    ORDER BY created_at DESC 
                    LIMIT 1
                )
                ORDER BY message_index
            """, (user_id, user_id))
        
        rows = cursor.fetchall()
        
        if not rows:
            return [], None
        
        # Convert to chat history format
        chat_history = []
        session_id = rows[0]["session_id"]
        
        for row in rows:
            message = {
                "role": row["role"],
                "text": row["content"],
            }
            
            # Add additional fields for assistant messages
            if row["role"] == "assistant":
                if row["sql_query"]:
                    message["sql_query"] = row["sql_query"]
                if row["data_summary"]:
                    message["data_summary"] = row["data_summary"]
                if row["result_count"]:
                    message["result_count"] = row["result_count"]
                if row["query_type"]:
                    message["query_type"] = row["query_type"]
                if row["show_table"]:
                    message["show_table"] = row["show_table"]
            
            chat_history.append(message)
        
        return chat_history, session_id
        
    except Exception as e:
        print(f"Error loading conversation history: {e}")
        return [], None
    finally:
        cursor.close()
        conn.close()

def save_conversation_memory(user_id: int, memory: ConversationMemory, session_id: str):
    """Save conversation memory state to database."""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Serialize memory to JSON
        memory_data = memory.to_dict()
        
        cursor.execute("""
            INSERT INTO conversation_memory (user_id, session_id, memory_data)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id) 
            DO UPDATE SET 
                session_id = EXCLUDED.session_id,
                memory_data = EXCLUDED.memory_data,
                updated_at = NOW()
        """, (user_id, session_id, json.dumps(memory_data)))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"Error saving conversation memory: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def load_conversation_memory(user_id: int, session_id: Optional[str] = None) -> Optional[ConversationMemory]:
    """Load conversation memory state from database."""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        if session_id:
            cursor.execute(
                "SELECT memory_data FROM conversation_memory WHERE user_id = %s AND session_id = %s",
                (user_id, session_id)
            )
        else:
            cursor.execute(
                "SELECT memory_data FROM conversation_memory WHERE user_id = %s ORDER BY updated_at DESC LIMIT 1",
                (user_id,)
            )
        
        row = cursor.fetchone()
        
        if row and row["memory_data"]:
            memory_data = row["memory_data"]
            if isinstance(memory_data, str):
                memory_data = json.loads(memory_data)
            
            return ConversationMemory.from_dict(memory_data)
        
        return None
        
    except Exception as e:
        print(f"Error loading conversation memory: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def clear_conversation_history(user_id: int, session_id: Optional[str] = None):
    """Clear conversation history for user."""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        if session_id:
            cursor.execute(
                "DELETE FROM conversation_history WHERE user_id = %s AND session_id = %s",
                (user_id, session_id)
            )
            cursor.execute(
                "DELETE FROM conversation_memory WHERE user_id = %s AND session_id = %s",
                (user_id, session_id)
            )
        else:
            cursor.execute("DELETE FROM conversation_history WHERE user_id = %s", (user_id,))
            cursor.execute("DELETE FROM conversation_memory WHERE user_id = %s", (user_id,))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"Error clearing conversation history: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()