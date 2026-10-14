"""Declared, package-relative materials; saving them is not a reproduction certification."""

from pydantic import BaseModel, ConfigDict, Field


class ExecutionMaterials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entrypoint: str = Field(description="Research script path relative to the saved package")
    parameters: list[str] = Field(description="Parameter file paths relative to the package")
    environment: list[str] = Field(
        min_length=1, description="Lock and environment file paths relative to the package"
    )
    data: list[str] = Field(
        description="Frozen input or exact authorized data selection identity file paths"
    )
    evidence: list[str] = Field(description="Existing execution and verification record file paths")
    instructions: str = Field(
        min_length=1,
        max_length=8000,
        description="How to prepare and run with these paths; state missing prerequisites honestly",
    )

    def validate_files(self, files: list[str]) -> None:
        paths = [self.entrypoint, *self.parameters, *self.environment, *self.data, *self.evidence]
        if len({path.casefold() for path in paths}) != len(paths) or not set(paths) <= set(files):
            raise ValueError("Execution paths must be unique and included in study files")
