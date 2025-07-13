"""
Simple conversation memory for Strava data queries.
Tracks recent queries, results, and context for clarifications.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import json

@dataclass
class MemoryEntry:
    """Single conversation memory entry."""
    timestamp: str
    user_query: str
    sql_query: Optional[str]
    data_summary: str  # Brief description of the results
    result_count: int
    query_type: str
    
class ConversationMemory:
    """Simple memory manager for conversation context."""
    
    def __init__(self, max_entries: int = 5):
        self.max_entries = max_entries
        self.entries: List[MemoryEntry] = []
        self.context_summary = ""
    
    def add_entry(self, user_query: str, sql_query: Optional[str], 
                 data_summary: str, result_count: int, query_type: str):
        """Add a new memory entry."""
        entry = MemoryEntry(
            timestamp=datetime.now().isoformat(),
            user_query=user_query,
            sql_query=sql_query,
            data_summary=data_summary,
            result_count=result_count,
            query_type=query_type
        )
        
        self.entries.append(entry)
        
        # Keep only the most recent entries
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]
        
        # Update context summary
        self._update_context_summary()
    
    def get_context_for_query(self, current_query: str) -> str:
        """Get relevant context for the current query."""
        if not self.entries:
            return ""
        
        # Always provide context from recent entries (simple approach)
        # With only 3-5 entries max, the overhead is minimal
        recent_context = []
        for entry in self.entries[-3:]:  # Last 3 entries
            context_line = f"Previous query: '{entry.user_query}'"
            if entry.sql_query:
                context_line += f" (SQL: {entry.sql_query[:100]}...)"
            context_line += f" → {entry.data_summary}"
            recent_context.append(context_line)
        
        return "Recent conversation context:\n" + "\n".join(recent_context)
    
    def get_last_sql_query(self) -> Optional[str]:
        """Get the most recent SQL query."""
        for entry in reversed(self.entries):
            if entry.sql_query:
                return entry.sql_query
        return None
    
    def get_last_result_summary(self) -> Optional[str]:
        """Get the most recent result summary."""
        if self.entries:
            return self.entries[-1].data_summary
        return None
    
    def _update_context_summary(self):
        """Update the overall context summary."""
        if not self.entries:
            self.context_summary = ""
            return
        
        # Create a brief summary of recent activity
        recent_topics = []
        for entry in self.entries[-3:]:
            if "activities" in entry.data_summary.lower():
                recent_topics.append("activity data")
            elif "distance" in entry.data_summary.lower():
                recent_topics.append("distance metrics")
            elif "time" in entry.data_summary.lower():
                recent_topics.append("time analysis")
            elif "elevation" in entry.data_summary.lower():
                recent_topics.append("elevation data")
        
        if recent_topics:
            unique_topics = list(set(recent_topics))
            self.context_summary = f"Recent discussion about: {', '.join(unique_topics)}"
        else:
            self.context_summary = "General Strava data discussion"
    
    def clear(self):
        """Clear all memory."""
        self.entries = []
        self.context_summary = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for session state storage."""
        return {
            "entries": [asdict(entry) for entry in self.entries],
            "context_summary": self.context_summary,
            "max_entries": self.max_entries
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMemory':
        """Create from dictionary (session state restoration)."""
        memory = cls(max_entries=data.get("max_entries", 5))
        memory.context_summary = data.get("context_summary", "")
        
        for entry_dict in data.get("entries", []):
            entry = MemoryEntry(**entry_dict)
            memory.entries.append(entry)
        
        return memory

def create_data_summary(data: Any, query_type: str, result_count: int) -> str:
    """Create a brief summary of query results for memory."""
    if data is None or result_count == 0:
        return "No results found"
    
    # Handle pandas DataFrame check properly
    if hasattr(data, 'empty') and data.empty:
        return "No results found"
    
    if query_type.upper() == "TEXT":
        return f"Generated text response"
    elif query_type.upper() in ["TABLE", "TEXT_AND_TABLE"]:
        # Try to infer what kind of data this is
        if hasattr(data, 'columns'):
            columns = list(data.columns)
            if 'distance' in columns:
                return f"Distance data for {result_count} activities"
            elif 'moving_time' in columns:
                return f"Time analysis for {result_count} activities"
            elif 'elevation_gain' in columns:
                return f"Elevation data for {result_count} activities"
            elif 'type' in columns:
                return f"Activity breakdown for {result_count} activities"
            else:
                return f"Data table with {result_count} rows and {len(columns)} columns"
        else:
            return f"Query results with {result_count} items"
    
    return f"Results ({result_count} items)"