"""
Parse API - Web API interface for code parsing and analysis.

This module provides REST API endpoints for code analysis.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import json
import logging

# For FastAPI integration (optional)
try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    
# Import from new structure
from ..api.analysis_api import AnalysisAPI
from ..api.training_api import TrainingAPI
from ..api.knowledge_api import KnowledgeAPI

logger = logging.getLogger(__name__)


# Request/Response models
class AnalysisRequest:
    """Request for code analysis."""
    def __init__(self, code: str, analyses: Optional[List[str]] = None,
                 options: Optional[Dict[str, Any]] = None):
        self.code = code
        self.analyses = analyses or ["cfg", "fixpoint"]
        self.options = options or {}


class TrainingRequest:
    """Request for training."""
    def __init__(self, concept: str, examples: List[Dict[str, Any]],
                 validation: Optional[List[Dict[str, Any]]] = None):
        self.concept = concept
        self.examples = examples
        self.validation = validation


class KnowledgeRequest:
    """Request for knowledge operations."""
    def __init__(self, operation: str, **kwargs):
        self.operation = operation
        self.params = kwargs


class ParseAPI:
    """
    Web API for RegionAI parsing and analysis.
    
    This class can be used standalone or integrated with web frameworks.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.analysis_api = AnalysisAPI(config)
        self.training_api = TrainingAPI(config)
        self.knowledge_api = KnowledgeAPI(config)
        
    def analyze(self, request: AnalysisRequest) -> Dict[str, Any]:
        """
        Analyze code.
        
        Args:
            request: Analysis request
            
        Returns:
            Analysis results
        """
        try:
            result = self.analysis_api.analyze_code(
                request.code,
                analyses=request.analyses,
                options=request.options
            )
            
            return {
                "success": result.success,
                "results": result.to_dict(),
                "errors": result.errors or []
            }
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def train(self, request: TrainingRequest) -> Dict[str, Any]:
        """
        Train a concept.
        
        Args:
            request: Training request
            
        Returns:
            Training results
        """
        try:
            result = self.training_api.train_concept(
                request.concept,
                request.examples,
                validation_set=request.validation
            )
            
            return {
                "success": result.success,
                "session_id": result.session_id,
                "mastery": result.mastery_levels,
                "recommendations": result.recommendations
            }
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def knowledge(self, request: KnowledgeRequest) -> Dict[str, Any]:
        """
        Perform knowledge operations.
        
        Args:
            request: Knowledge request
            
        Returns:
            Operation results
        """
        try:
            if request.operation == "add_fact":
                success = self.knowledge_api.add_fact(**request.params)
                return {"success": success}
                
            elif request.operation == "query":
                result = self.knowledge_api.query(**request.params)
                return {
                    "success": result.success,
                    "results": result.results,
                    "confidence": result.confidence
                }
                
            elif request.operation == "reason":
                result = self.knowledge_api.reason(**request.params)
                return result
                
            elif request.operation == "explain":
                result = self.knowledge_api.explain(**request.params)
                return result
                
            else:
                return {
                    "success": False,
                    "error": f"Unknown operation: {request.operation}"
                }
                
        except Exception as e:
            logger.error(f"Knowledge operation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def health(self) -> Dict[str, Any]:
        """Get API health status."""
        return {
            "status": "healthy",
            "version": "1.0.0",
            "apis": {
                "analysis": "available",
                "training": "available",
                "knowledge": "available"
            }
        }


# FastAPI integration (optional)
if FASTAPI_AVAILABLE:
    
    class AnalysisRequestModel(BaseModel):
        code: str
        analyses: Optional[List[str]] = None
        options: Optional[Dict[str, Any]] = None
        
    class TrainingRequestModel(BaseModel):
        concept: str
        examples: List[Dict[str, Any]]
        validation: Optional[List[Dict[str, Any]]] = None
        
    class KnowledgeRequestModel(BaseModel):
        operation: str
        params: Dict[str, Any]
        
        
    def create_fastapi_app(config: Optional[Dict[str, Any]] = None) -> FastAPI:
        """Create FastAPI application."""
        app = FastAPI(
            title="RegionAI Parse API",
            description="API for code analysis and AI training",
            version="1.0.0"
        )
        
        api = ParseAPI(config)
        
        @app.get("/health")
        async def health():
            return api.health()
            
        @app.post("/analyze")
        async def analyze(request: AnalysisRequestModel):
            req = AnalysisRequest(
                code=request.code,
                analyses=request.analyses,
                options=request.options
            )
            return api.analyze(req)
            
        @app.post("/train")
        async def train(request: TrainingRequestModel):
            req = TrainingRequest(
                concept=request.concept,
                examples=request.examples,
                validation=request.validation
            )
            return api.train(req)
            
        @app.post("/knowledge")
        async def knowledge(request: KnowledgeRequestModel):
            req = KnowledgeRequest(
                operation=request.operation,
                **request.params
            )
            return api.knowledge(req)
            
        return app


# Flask integration (optional)
try:
    from flask import Flask, request, jsonify
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    
    
if FLASK_AVAILABLE:
    
    def create_flask_app(config: Optional[Dict[str, Any]] = None) -> Flask:
        """Create Flask application."""
        app = Flask(__name__)
        api = ParseAPI(config)
        
        @app.route("/health", methods=["GET"])
        def health():
            return jsonify(api.health())
            
        @app.route("/analyze", methods=["POST"])
        def analyze():
            data = request.get_json()
            req = AnalysisRequest(
                code=data["code"],
                analyses=data.get("analyses"),
                options=data.get("options")
            )
            return jsonify(api.analyze(req))
            
        @app.route("/train", methods=["POST"])
        def train():
            data = request.get_json()
            req = TrainingRequest(
                concept=data["concept"],
                examples=data["examples"],
                validation=data.get("validation")
            )
            return jsonify(api.train(req))
            
        @app.route("/knowledge", methods=["POST"])
        def knowledge():
            data = request.get_json()
            req = KnowledgeRequest(
                operation=data["operation"],
                **data.get("params", {})
            )
            return jsonify(api.knowledge(req))
            
        return app


# Simple HTTP server (no dependencies)
def create_simple_server(host: str = "localhost", port: int = 8000,
                        config: Optional[Dict[str, Any]] = None):
    """Create simple HTTP server without external dependencies."""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import urllib.parse
    
    api = ParseAPI(config)
    
    class RequestHandler(BaseHTTPRequestHandler):
        
        def do_GET(self):
            if self.path == "/health":
                self.send_json_response(api.health())
            else:
                self.send_error(404)
                
        def do_POST(self):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            
            try:
                data = json.loads(body)
                
                if self.path == "/analyze":
                    req = AnalysisRequest(
                        code=data["code"],
                        analyses=data.get("analyses"),
                        options=data.get("options")
                    )
                    self.send_json_response(api.analyze(req))
                    
                elif self.path == "/train":
                    req = TrainingRequest(
                        concept=data["concept"],
                        examples=data["examples"],
                        validation=data.get("validation")
                    )
                    self.send_json_response(api.train(req))
                    
                elif self.path == "/knowledge":
                    req = KnowledgeRequest(
                        operation=data["operation"],
                        **data.get("params", {})
                    )
                    self.send_json_response(api.knowledge(req))
                    
                else:
                    self.send_error(404)
                    
            except Exception as e:
                self.send_json_response({"error": str(e)}, status=400)
                
        def send_json_response(self, data: dict, status: int = 200):
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
            
        def log_message(self, format, *args):
            # Suppress default logging
            pass
            
    server = HTTPServer((host, port), RequestHandler)
    print(f"Server running at http://{host}:{port}")
    return server


# Example usage
def example_usage():
    """Example of using the API directly."""
    api = ParseAPI()
    
    # Analysis example
    code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""
    
    analysis_req = AnalysisRequest(code, analyses=["cfg", "metrics"])
    result = api.analyze(analysis_req)
    print("Analysis result:", result)
    
    # Training example
    training_req = TrainingRequest(
        concept="recursion",
        examples=[
            {"input": "factorial", "output": "recursive function"},
            {"input": "fibonacci", "output": "recursive function"}
        ]
    )
    result = api.train(training_req)
    print("Training result:", result)
    
    # Knowledge example
    knowledge_req = KnowledgeRequest(
        operation="add_fact",
        subject="factorial",
        predicate="is",
        object="recursive"
    )
    result = api.knowledge(knowledge_req)
    print("Knowledge result:", result)


if __name__ == "__main__":
    # Run simple server by default
    server = create_simple_server()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()