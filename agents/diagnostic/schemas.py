from pydantic import BaseModel, Field


from pydantic import BaseModel, Field


class DiagnosticOutput(BaseModel):

    symptom: str

    assemblies_to_check: list[str] = Field(
        default_factory=list
    )