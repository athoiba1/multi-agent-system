from typing import Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ResultStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class StepResult(BaseModel):
    step_id: str
    step_name: str
    status: ResultStatus
    output_data: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: float = 0
    timestamp: datetime = Field(default_factory=datetime.now)


class PipelineResult(BaseModel):
    task_id: str
    status: ResultStatus
    steps_results: list[StepResult] = Field(default_factory=list)
    final_output: dict[str, Any] = Field(default_factory=dict)
    total_duration_ms: float = 0
    timestamp: datetime = Field(default_factory=datetime.now)
    error: Optional[str] = None
