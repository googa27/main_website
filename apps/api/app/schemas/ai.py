from typing import Any

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    message: str = Field(..., description="User message")
    response: str = Field(..., description="Assistant response")


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    conversation_history: list[ChatMessage] | None = Field(
        default_factory=list, description="Previous conversation"
    )


class ChatResponse(BaseModel):
    message: str = Field(..., description="AI response message")
    confidence: float = Field(..., description="Confidence score (0.0 to 1.0)")
    sources: list[str] | None = Field(
        default_factory=list, description="Information sources"
    )


class PredictionRequest(BaseModel):
    input_data: dict[str, Any] = Field(..., description="Input data for prediction")
    model_type: str = Field(..., description="Type of model to use")


class PredictionResponse(BaseModel):
    prediction: str | float | int = Field(..., description="Prediction result")
    confidence: float = Field(..., description="Confidence score (0.0 to 1.0)")
    model_info: dict[str, Any] = Field(
        ..., description="Model information and metadata"
    )


class VisualizationRequest(BaseModel):
    data: dict[str, Any] = Field(..., description="Data to visualize")
    chart_type: str = Field(..., description="Type of chart to create")
    options: dict[str, Any] | None = Field(
        default_factory=dict, description="Chart options"
    )


class VisualizationResponse(BaseModel):
    chart_data: dict[str, Any] = Field(..., description="Chart data in Chart.js format")
    chart_type: str = Field(..., description="Type of chart created")
    options: dict[str, Any] = Field(..., description="Chart options and configuration")
