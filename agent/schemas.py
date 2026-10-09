from pydantic import BaseModel, Field
from typing import Optional, Any
from enum import Enum
from datetime import datetime

class StepStatus(str, Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    SKIPPED = 'skipped'

class AgentStatus(str, Enum):
    PLANNING = 'planning'
    RUNNING = 'running'
    WAITING_HUMAN = 'waiting_human'
    VERIFYING = 'verifying'
    DONE = 'done'
    FAILED = 'failed'

class VerificationStatus(str, Enum):
    VERIFIED = 'verified'
    PARTIAL = 'partial'
    FAILED = 'failed'

class TraceEntry(BaseModel):
    step_index: int
    reasoning: str
    tool_name: Optional[str] = None
    tool_args: Optional[dict] = None
    result_summary: Optional[str] = None
    success: bool = True
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class Step(BaseModel):
    id: int
    description: str
    suggested_tool: Optional[str] = None
    expected_outcome: str
    status: StepStatus = StepStatus.PENDING
    result: Optional[str] = None
    retries: int = 0

class TaskPlan(BaseModel):
    task_description: str
    steps: list[Step]
    verification_criteria: list[str]

class ToolResult(BaseModel):
    success: bool
    output: Any = None
    error: Optional[str] = None
    screenshot_path: Optional[str] = None

class Memory(BaseModel):
    facts: list[str] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
    working: dict[str, Any] = Field(default_factory=dict)

class VerificationResult(BaseModel):
    status: VerificationStatus
    explanation: str
    evidence: list[str] = Field(default_factory=list)

class AgentState(BaseModel):
    task_id: str
    task: str
    plan: Optional[TaskPlan] = None
    memory: Memory = Field(default_factory=Memory)
    trace: list[TraceEntry] = Field(default_factory=list)
    status: AgentStatus = AgentStatus.PLANNING
    verification: Optional[VerificationResult] = None
    final_summary: Optional[str] = None
    screenshots: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
