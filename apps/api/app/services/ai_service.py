"""
AI service for portfolio website using local LLM (Ollama).

This service provides:
- Resume Q&A using local language models
- ML predictions and visualizations
- Free, self-hosted AI capabilities
"""

import asyncio
import json
import logging
import aiohttp
from typing import List, Optional, Dict, Any
from app.models.ai import ChatMessage, ChatResponse, PredictionResponse, VisualizationResponse
from app.core.config import settings

logger = logging.getLogger(__name__)

class LocalAIService:
    """Service for local AI capabilities using Ollama."""
    
    def __init__(self):
        """Initialize the local AI service."""
        self.ollama_base_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
        self.default_model = getattr(settings, 'OLLAMA_DEFAULT_MODEL', 'llama2:7b')
        self.cv_context = self._load_cv_context()
        
    def _load_cv_context(self) -> str:
        """Load CV context for AI responses."""
        return """
        Cristobal Cortinez Duhalde is a Data Scientist and ML Engineer with expertise in:
        
        EDUCATION:
        - MSc in Applied Mathematics from Universidad de Chile (2019-2021)
        - BSc in Mathematics from Universidad de Chile (2015-2019)
        
        EXPERIENCE:
        - Senior Data Scientist at Quantitative Finance Solutions (2023-present)
        - ML Engineer at Machine Learning Consulting (2022-2022)
        - Quantitative Developer at Financial Technology Startup (2021-2022)
        
        SKILLS:
        - Programming: Python (expert), C++ (advanced), JavaScript/TypeScript (intermediate)
        - ML/AI: TensorFlow, PyTorch, Scikit-learn, MLflow (expert to advanced)
        - Mathematical: PDE methods, finite difference/element methods, optimization (expert)
        - Tools: Docker, AWS, PostgreSQL, Redis, Git (advanced to intermediate)
        
        PROJECTS:
        - Finite difference option pricing library with PDE methods
        - Django optimization app for linear programming
        - ML pipelines for financial risk assessment
        - Real-time risk calculation engines
        
        SPECIALIZATIONS:
        - Quantitative finance and derivatives pricing
        - Machine learning and MLOps
        - Numerical methods and mathematical modeling
        - Financial risk management
        """
    
    async def _call_ollama(self, prompt: str, model: str = None) -> str:
        """Call Ollama API for text generation."""
        if model is None:
            model = self.default_model
            
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "max_tokens": 500
                    }
                }
                
                async with session.post(
                    f"{self.ollama_base_url}/api/generate",
                    json=payload,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get('response', 'I apologize, but I could not generate a response.')
                    else:
                        logger.error(f"Ollama API error: {response.status}")
                        return self._fallback_response(prompt)
                        
        except asyncio.TimeoutError:
            logger.warning("Ollama API timeout, using fallback")
            return self._fallback_response(prompt)
        except Exception as e:
            logger.error(f"Error calling Ollama: {str(e)}")
            return self._fallback_response(prompt)
    
    def _fallback_response(self, prompt: str) -> str:
        """Fallback response when Ollama is not available."""
        prompt_lower = prompt.lower()
        
        if any(word in prompt_lower for word in ["experience", "work", "job"]):
            return "I have extensive experience in Data Science and Quantitative Finance, including roles at Quantitative Finance Solutions, Machine Learning Consulting, and Financial Technology Startup. I specialize in ML, financial modeling, and PDE methods."
        elif any(word in prompt_lower for word in ["education", "degree", "university"]):
            return "I hold an MSc in Applied Mathematics from Universidad de Chile (2019-2021) and a BSc in Mathematics from the same institution (2015-2019). My focus was on financial mathematics and numerical methods."
        elif any(word in prompt_lower for word in ["skills", "technologies", "programming"]):
            return "My technical skills include Python (expert), C++ (advanced), TensorFlow, PyTorch, Scikit-learn, MLflow, Docker, AWS, PostgreSQL, and expertise in machine learning, statistical modeling, and numerical methods."
        elif any(word in prompt_lower for word in ["projects", "work", "portfolio"]):
            return "I've worked on several key projects including finite difference options pricing library, Django optimization app, ML pipelines for financial risk assessment, and real-time risk calculation engines. Check out my GitHub for more details!"
        elif any(word in prompt_lower for word in ["finance", "quantitative", "pricing"]):
            return "I specialize in quantitative finance, particularly derivatives pricing using PDE methods, finite difference schemes, and Monte Carlo simulations. I've implemented these methods in production systems for financial risk management."
        elif any(word in prompt_lower for word in ["ml", "machine learning", "ai"]):
            return "I have extensive experience in machine learning and MLOps, including building automated ML pipelines, implementing MLflow for experiment tracking, and deploying models in production environments."
        else:
            return "I'm Cristobal Cortinez Duhalde, a Data Scientist and ML Engineer with expertise in quantitative finance and applied mathematics. I specialize in finite difference methods, optimization algorithms, and MLOps pipelines. How can I help you learn more about my background?"
    
    async def chat_with_resume(self, message: str, conversation_history: Optional[List[ChatMessage]] = None) -> ChatResponse:
        """Chat with AI about resume and experience using local LLM."""
        try:
            # Build context from conversation history
            context = self.cv_context
            if conversation_history:
                recent_context = "\n".join([f"User: {msg.message}\nAssistant: {msg.response}" for msg in conversation_history[-3:]])
                context += f"\n\nRecent conversation:\n{recent_context}"
            
            # Create prompt for the LLM
            prompt = f"""You are an AI assistant helping people learn about Cristobal Cortinez Duhalde's background and experience. 

Context about Cristobal:
{context}

User question: {message}

Please provide a helpful, accurate response based on Cristobal's background. Be conversational but professional. If asked about something not in the context, politely say you don't have that information.

Response:"""
            
            # Get response from Ollama
            response = await self._call_ollama(prompt)
            
            return ChatResponse(
                message=response.strip(),
                confidence=0.85,
                sources=["resume", "experience", "projects", "local_llm"]
            )
            
        except Exception as e:
            logger.error(f"Error in chat_with_resume: {str(e)}")
            return ChatResponse(
                message=self._fallback_response(message),
                confidence=0.7,
                sources=["resume", "fallback"]
            )
    
    async def make_prediction(self, input_data: dict, model_type: str) -> PredictionResponse:
        """Make ML predictions using local models or simulations."""
        try:
            if model_type == "linear_regression":
                # Simple linear regression simulation
                x = input_data.get("x", 0)
                prediction = 2 * x + 1  # y = 2x + 1
                confidence = 0.85
                explanation = "Linear regression model: y = 2x + 1"
                
            elif model_type == "classification":
                # Simple classification simulation
                features = input_data.get("features", [0, 0])
                prediction = "class_a" if sum(features) > 0 else "class_b"
                confidence = 0.78
                explanation = "Binary classification based on feature sum"
                
            elif model_type == "financial_option":
                # Simple option pricing simulation
                spot_price = input_data.get("spot_price", 100)
                strike_price = input_data.get("strike_price", 100)
                volatility = input_data.get("volatility", 0.2)
                time_to_expiry = input_data.get("time_to_expiry", 1.0)
                
                # Simplified Black-Scholes approximation
                if spot_price > strike_price:
                    prediction = max(spot_price - strike_price, 0) * (1 + volatility * time_to_expiry)
                else:
                    prediction = max(strike_price - spot_price, 0) * (1 + volatility * time_to_expiry)
                
                confidence = 0.82
                explanation = "Simplified option pricing model based on Black-Scholes approximation"
                
            else:
                prediction = "unknown"
                confidence = 0.5
                explanation = f"Unknown model type: {model_type}"
            
            return PredictionResponse(
                prediction=prediction,
                confidence=confidence,
                model_info={
                    "type": model_type, 
                    "version": "1.0",
                    "explanation": explanation,
                    "local_model": True
                }
            )
            
        except Exception as e:
            logger.error(f"Error in make_prediction: {str(e)}")
            return PredictionResponse(
                prediction="error",
                confidence=0.0,
                model_info={"type": model_type, "version": "1.0", "error": str(e)}
            )
    
    async def create_visualization(self, data: dict, chart_type: str, options: dict = {}) -> VisualizationResponse:
        """Create data visualizations with sample data or real data processing."""
        try:
            if chart_type == "line_chart" and "data" in data:
                # Process real data for line chart
                chart_data = {
                    "labels": [str(i) for i in range(len(data["data"]))],
                    "datasets": [{
                        "label": data.get("label", "Data"),
                        "data": data["data"],
                        "borderColor": "#3B82F6",
                        "backgroundColor": "rgba(59, 130, 246, 0.1)"
                    }]
                }
                
            elif chart_type == "bar_chart" and "data" in data:
                # Process real data for bar chart
                chart_data = {
                    "labels": [str(i) for i in range(len(data["data"]))],
                    "datasets": [{
                        "label": data.get("label", "Data"),
                        "data": data["data"],
                        "backgroundColor": ["#3B82F6", "#8B5CF6", "#06B6D4", "#10B981", "#F59E0B"]
                    }]
                }
                
            elif chart_type == "scatter_plot" and "x" in data and "y" in data:
                # Process real data for scatter plot
                chart_data = {
                    "datasets": [{
                        "label": data.get("label", "Data Points"),
                        "data": [{"x": x, "y": y} for x, y in zip(data["x"], data["y"])],
                        "backgroundColor": "#3B82F6",
                        "pointRadius": 6
                    }]
                }
                
            else:
                # Fallback to sample data
                chart_data = {
                    "labels": ["A", "B", "C", "D", "E"],
                    "datasets": [{
                        "label": "Sample Data",
                        "data": [10, 20, 15, 25, 18],
                        "backgroundColor": ["#3B82F6", "#8B5CF6", "#06B6D4", "#10B981", "#F59E0B"]
                    }]
                }
            
            return VisualizationResponse(
                chart_data=chart_data,
                chart_type=chart_type,
                options=options or {"responsive": True, "maintainAspectRatio": False}
            )
            
        except Exception as e:
            logger.error(f"Error in create_visualization: {str(e)}")
            # Return fallback visualization
            return VisualizationResponse(
                chart_data={
                    "labels": ["Error"],
                    "datasets": [{"label": "Error", "data": [0], "backgroundColor": ["#EF4444"]}]
                },
                chart_type=chart_type,
                options={"responsive": True, "maintainAspectRatio": False}
            )
    
    async def check_ollama_status(self) -> Dict[str, Any]:
        """Check if Ollama is running and available."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.ollama_base_url}/api/tags", timeout=5) as response:
                    if response.status == 200:
                        models = await response.json()
                        return {
                            "status": "running",
                            "models": [model["name"] for model in models.get("models", [])],
                            "default_model": self.default_model,
                            "base_url": self.ollama_base_url
                        }
                    else:
                        return {"status": "error", "message": f"HTTP {response.status}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

# Global instance
ai_service = LocalAIService()

# Backward compatibility functions
async def chat_with_resume(message: str, conversation_history: Optional[List[ChatMessage]] = None) -> ChatResponse:
    """Chat with AI about resume and experience."""
    return await ai_service.chat_with_resume(message, conversation_history)

async def make_prediction(input_data: dict, model_type: str) -> PredictionResponse:
    """Make ML predictions."""
    return await ai_service.make_prediction(input_data, model_type)

async def create_visualization(data: dict, chart_type: str, options: dict = {}) -> VisualizationResponse:
    """Create data visualizations."""
    return await ai_service.create_visualization(data, chart_type, options)
