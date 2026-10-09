import sqlite3, json, logging, os
from datetime import datetime
from agent.schemas import Memory, TraceEntry
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)
DB_PATH = os.environ.get('MEMORY_DB', './memory.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS episodes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id TEXT,
        step_index INTEGER,
        data TEXT,
        created_at TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

class MemoryManager:
    def __init__(self, task_id: str, client: AsyncOpenAI = None):
        self.task_id = task_id
        self.client = client
        self.memory = Memory()
    
    def add_observation(self, obs: str):
        self.memory.observations.append(obs)
    
    def add_fact(self, fact: str):
        if fact not in self.memory.facts:
            self.memory.facts.append(fact)
    
    def set_working(self, key: str, value):
        self.memory.working[key] = value
    
    def get_context(self, max_chars: int = 4000) -> str:
        parts = []
        if self.memory.facts:
            parts.append('=== KEY FACTS DISCOVERED ===')
            parts.extend(f'- {f}' for f in self.memory.facts)
        if self.memory.working:
            parts.append('=== WORKING MEMORY ===')
            for k, v in self.memory.working.items():
                parts.append(f'{k}: {v}')
        if self.memory.observations:
            parts.append('=== RECENT OBSERVATIONS ===')
            # Include last N observations that fit
            recent = self.memory.observations[-10:]
            parts.extend(f'[{i+1}] {o}' for i, o in enumerate(recent))
        context = '\n'.join(parts)
        if len(context) > max_chars:
            context = context[-max_chars:]
        return context
    
    def save_trace_entry(self, entry: TraceEntry):
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            'INSERT INTO episodes (task_id, step_index, data, created_at) VALUES (?, ?, ?, ?)',
            (self.task_id, entry.step_index, entry.model_dump_json(), datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()
