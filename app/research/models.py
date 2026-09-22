from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl, model_validator


class ResearchCitation(BaseModel):
    title: str
    url: HttpUrl


class ResearchFinding(BaseModel):
    statement: str
    citations: list[ResearchCitation] = Field(default_factory=list)


class ResearchAnswer(BaseModel):
    answer: str
    findings: list[ResearchFinding] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    citations: list[ResearchCitation] = Field(default_factory=list)
    query_scope: str

    @model_validator(mode="after")
    def findings_must_be_cited(self) -> "ResearchAnswer":
        missing = [finding.statement for finding in self.findings if not finding.citations]
        if missing:
            raise ValueError("Every factual finding must include at least one citation")
        return self
