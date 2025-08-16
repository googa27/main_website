from fastapi import APIRouter, HTTPException
from app.models.ai import (
    ChatRequest, ChatResponse, 
    PredictionRequest, PredictionResponse,
    VisualizationRequest, VisualizationResponse
)
from app.services.ai_service import (
    chat_with_resume, 
    make_prediction, 
    create_visualization,
    ai_service
)

router = APIRouter()

@router.get("/ai/status")
async def get_ai_status():
    """Get AI service status and available models."""
    try:
        status = await ai_service.check_ollama_status()
        return status
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get AI status: {str(e)}"
        )

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Chat with AI about resume and experience"""
    try:
        response = await chat_with_resume(request.message, request.conversation_history)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"AI chat error: {str(e)}"
        )

@router.post("/predict", response_model=PredictionResponse)
async def prediction_endpoint(request: PredictionRequest):
    """Make ML predictions"""
    try:
        response = await make_prediction(request.input_data, request.model_type)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Prediction error: {str(e)}"
        )

@router.post("/visualize", response_model=VisualizationResponse)
async def visualization_endpoint(request: VisualizationRequest):
    """Create data visualizations"""
    try:
        response = await create_visualization(request.data, request.chart_type, request.options)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Visualization error: {str(e)}"
        )
