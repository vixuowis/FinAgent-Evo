from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class SkillCategory(str, Enum):
    DATA = "DATA"
    ANALYSIS = "ANALYSIS"
    DECISION = "DECISION"
    EXECUTION = "EXECUTION"

class ModelTier(str, Enum):
    LIGHT = "LIGHT"
    STANDARD = "STANDARD"
    HEAVY = "HEAVY"

class LLMConfig(BaseModel):
    model_tier: ModelTier
    temperature: float
    max_tokens: int

class ExecutionLog(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    input: Any
    output: Any
    success: bool
    performance_metrics: Optional[Dict[str, float]] = None

class SkillGenotype(BaseModel):
    skill_id: str
    category: SkillCategory
    llm_config: LLMConfig
    prompt_chromosome: str
    tool_deps: List[str]
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    fitness_score: float = 0.5
    execution_history: List[ExecutionLog] = []

class MemoryEntry(BaseModel):
    id: str
    content: str
    importance: float
    tags: List[str]
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class Experience(BaseModel):
    id: str
    task: str
    context: Dict[str, Any]
    outcome: Any
    lessons: List[str]
    importance: float
