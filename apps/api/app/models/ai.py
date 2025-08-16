from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict, Any

class ChatMessage(BaseModel):
    message: str = Field(..., description="User message")
    response: str = Field(..., description="Assistant response")

class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    conversation_history: Optional[List[ChatMessage]] = Field(default_factory=list, description="Previous conversation")

class ChatResponse(BaseModel):
    message: str = Field(..., description="AI response message")
    confidence: float = Field(..., description="Confidence score (0.0 to 1.0)")
    sources: Optional[List[str]] = Field(default_factory=list, description="Information sources")

class PredictionRequest(BaseModel):
    input_data: Dict[str, Any] = Field(..., description="Input data for prediction")
    model_type: str = Field(..., description="Type of model to use")

class PredictionResponse(BaseModel):
    prediction: Union[str, float, int] = Field(..., description="Prediction result")
    confidence: float = Field(..., description="Confidence score (0.0 to 1.0)")
    model_info: Dict[str, Any] = Field(..., description="Model information and metadata")

class VisualizationRequest(BaseModel):
    data: Dict[str, Any] = Field(..., description="Data to visualize")
    chart_type: str = Field(..., description="Type of chart to create")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Chart options")

class VisualizationResponse(BaseModel):
    chart_data: Dict[str, Any] = Field(..., description="Chart data in Chart.js format")
    chart_type: str = Field(..., description="Type of chart created")
    options: Dict[str, Any] = Field(..., description="Chart options and configuration")
