"""Pydantic request/response schemas for Kintsugi API."""
from __future__ import annotations
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class AnswerStatus(str, Enum):
    answered = "answered"
    refused = "refused"


class ReasonCode(str, Enum):
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    NO_MODEL_EVIDENCE = "NO_MODEL_EVIDENCE"
    LOW_RELEVANCE = "LOW_RELEVANCE"
    HAZARD_REFERRAL = "HAZARD_REFERRAL"
    ANSWERED = "ANSWERED"


class CitationOut(BaseModel):
    claim: str
    page: int
    excerpt: str = ""


class AnswerRequest(BaseModel):
    model_number: str = Field(default="", max_length=64, description="Appliance model number")
    model: str = Field(default="", max_length=64, description="Alias for model_number")
    symptom: str = Field(..., min_length=1, max_length=500, description="Symptom or question")
    brand: str = Field(default="", max_length=64, description="Optional brand hint")

    model_config = {"str_strip_whitespace": True}


class AnswerResponse(BaseModel):
    status: AnswerStatus
    answer: str
    citations: list[CitationOut] = []
    reason_code: ReasonCode
    warnings: list[str] = []
    matched_model: str = ""
    demo_mode: bool = True


class FixOutcomeRequest(BaseModel):
    model: str = Field(..., min_length=1, max_length=64)
    symptom_category: str = Field(..., description="enum: electrical|mechanical|software|other")
    outcome: str = Field(..., description="enum: fixed|partially|not_fixed|unsafe_referred")


class FixOutcomeResponse(BaseModel):
    recorded: bool
    id: str = ""


class HealthResponse(BaseModel):
    status: str
    atlas_ok: bool
    version: str
    demo_mode: bool
    llm_model: str
    embedding_model: str
