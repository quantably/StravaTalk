-- Migration: Add conversation history persistence table
-- This stores chat history and memory for users across sessions

CREATE TABLE IF NOT EXISTS conversation_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    session_id VARCHAR(255), -- Optional session grouping
    message_index INTEGER NOT NULL, -- Order within conversation
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    sql_query TEXT, -- For assistant messages that used SQL
    data_summary TEXT, -- Brief description of results for memory
    result_count INTEGER DEFAULT 0,
    query_type VARCHAR(50),
    show_table BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_conversation_history_user_id ON conversation_history(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_history_session ON conversation_history(user_id, session_id);
CREATE INDEX IF NOT EXISTS idx_conversation_history_order ON conversation_history(user_id, session_id, message_index);

-- Table for persisting memory state
CREATE TABLE IF NOT EXISTS conversation_memory (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    session_id VARCHAR(255),
    memory_data JSONB, -- Serialized ConversationMemory state
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create index for memory lookups
CREATE INDEX IF NOT EXISTS idx_conversation_memory_user_session ON conversation_memory(user_id, session_id);