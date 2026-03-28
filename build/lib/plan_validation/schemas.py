"""Validation schemas and registry contract models."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from context_action_plan.enums import ActionName, ResultKind
from context_action_plan.schemas import ParsedOutput

from .enums import IssueSeverity, ToolCategory, ValidationCode, ValueKind


class ValidationIssue(BaseModel):
    """Structured validation issue."""

    code: ValidationCode
    severity: IssueSeverity
    message: str
    field: Optional[str] = None
    step_id: Optional[str] = None


class ValidationResult(BaseModel):
    """Final validation status for parsed output."""

    is_valid: bool
    is_executable: bool
    normalized_kind: Optional[ResultKind] = None
    errors: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)
    normalized: Optional[dict] = None


class ArgSpec(BaseModel):
    """Argument contract definition for a tool."""

    name: str
    kind: ValueKind
    description: str = ""


class ToolSpec(BaseModel):
    """Tool/action execution contract."""

    name: ActionName
    description: str
    category: ToolCategory
    required_args: list[ArgSpec] = Field(default_factory=list)
    optional_args: list[ArgSpec] = Field(default_factory=list)
    one_of: list[list[str]] = Field(default_factory=list)
    allow_step_references: bool = True

    def arg_spec_map(self) -> dict[str, ArgSpec]:
        """Return all args (required+optional) as a name->spec map."""
        return {spec.name: spec for spec in [*self.required_args, *self.optional_args]}


class ToolRegistry(BaseModel):
    """Registry of approved executable tools."""

    tools: dict[ActionName, ToolSpec]
    known_unimplemented_capabilities: list[str] = Field(default_factory=list)

    def get(self, action: ActionName) -> Optional[ToolSpec]:
        """Return tool spec by action name."""
        return self.tools.get(action)

    def has(self, action: ActionName) -> bool:
        """Whether a tool action is registered."""
        return action in self.tools

    def actions(self) -> list[ActionName]:
        """List all registered action names."""
        return list(self.tools.keys())


__all__ = [
    "ArgSpec",
    "ParsedOutput",
    "ToolRegistry",
    "ToolSpec",
    "ValidationIssue",
    "ValidationResult",
]
