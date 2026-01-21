"""
MCP Server with SSE protocol for columnist agent V2.
"""

from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import json
import time
import threading
from typing import Dict, Any, List
import queue
import uuid
from datetime import datetime

from .web_search import WebSearchTool
from .fact_check import FactCheckTool


class MCPServer:
    """MCP Server with Server-Sent Events support."""
    
    def __init__(self, host="localhost", port=5000):
        self.app = Flask(__name__)
        CORS(self.app)
        
        self.host = host
        self.port = port
        
        # Initialize tools
        self.tools = {
            "web_search": WebSearchTool(),
            "fact_check": FactCheckTool()
        }
        
        # Event management
        self.event_queue = queue.Queue()
        self.clients = {}
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask routes."""
        
        @self.app.route('/', methods=['GET'])
        def index():
            return jsonify({
                "name": "Columnist Agent MCP Server",
                "version": "2.0.0",
                "tools": list(self.tools.keys()),
                "status": "running"
            })
        
        @self.app.route('/tools', methods=['GET'])
        def list_tools():
            """List available tools."""
            tool_list = []
            for name, tool in self.tools.items():
                tool_info = {
                    "name": name,
                    "description": tool.description
                }
                tool_list.append(tool_info)
            
            return jsonify({"tools": tool_list})
        
        @self.app.route('/tools/call', methods=['POST'])
        def call_tool():
            """Call a specific tool."""
            try:
                data = request.json
                tool_name = data.get('name')
                arguments = data.get('arguments', {})
                request_id = data.get('id', str(uuid.uuid4()))
                
                if tool_name not in self.tools:
                    return jsonify({
                        "error": f"Tool '{tool_name}' not found",
                        "available_tools": list(self.tools.keys())
                    }), 404
                
                # Send start event
                self._emit_event({
                    "type": "tool_call_start",
                    "tool_name": tool_name,
                    "request_id": request_id,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Execute tool
                tool = self.tools[tool_name]
                result = tool.execute(arguments)
                
                # Send completion event
                self._emit_event({
                    "type": "tool_call_complete",
                    "tool_name": tool_name,
                    "request_id": request_id,
                    "timestamp": datetime.now().isoformat(),
                    "success": "error" not in result
                })
                
                return jsonify({
                    "request_id": request_id,
                    "tool_name": tool_name,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                error_id = str(uuid.uuid4())
                self._emit_event({
                    "type": "error",
                    "error_id": error_id,
                    "message": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                
                return jsonify({
                    "error": str(e),
                    "error_id": error_id
                }), 500
        
        @self.app.route('/events')
        def events():
            """Server-Sent Events endpoint."""
            client_id = str(uuid.uuid4())
            self.clients[client_id] = True
            
            def event_stream():
                try:
                    # Send initial connection event
                    yield f"data: {json.dumps({'type': 'connected', 'client_id': client_id})}\n\n"
                    
                    # Keep connection alive and send events
                    while self.clients.get(client_id, False):
                        try:
                            # Try to get event with timeout
                            event = self.event_queue.get(timeout=1)
                            yield f"data: {json.dumps(event)}\n\n"
                        except queue.Empty:
                            # Send heartbeat
                            yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.now().isoformat()})}\n\n"
                        except Exception as e:
                            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                            break
                            
                except GeneratorExit:
                    pass
                finally:
                    # Cleanup client
                    if client_id in self.clients:
                        del self.clients[client_id]
            
            return Response(
                stream_with_context(event_stream()),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Cache-Control'
                }
            )
        
        @self.app.route('/health', methods=['GET'])
        def health():
            """Health check endpoint."""
            return jsonify({
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "active_clients": len(self.clients),
                "available_tools": len(self.tools)
            })
    
    def _emit_event(self, event: Dict[str, Any]):
        """Emit event to all connected clients."""
        try:
            self.event_queue.put(event, timeout=1)
        except queue.Full:
            # If queue is full, we drop the event to prevent blocking
            pass
    
    def run(self, debug=False):
        """Run the MCP server."""
        print(f"Starting MCP Server on http://{self.host}:{self.port}")
        print(f"Available tools: {list(self.tools.keys())}")
        print(f"Events endpoint: http://{self.host}:{self.port}/events")
        
        self.app.run(
            host=self.host,
            port=self.port,
            debug=debug,
            threaded=True
        )


if __name__ == "__main__":
    server = MCPServer()
    server.run(debug=True)