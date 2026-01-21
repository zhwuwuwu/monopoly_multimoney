"""
Simple MCP server example for testing the columnist agent.
This server provides mock tools for web search, fact checking, and news retrieval.
"""

import asyncio
import json
import websockets
from typing import Dict, Any, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockMCPServer:
    """Mock MCP server for testing purposes."""
    
    def __init__(self):
        self.tools = [
            {
                "name": "web_search",
                "description": "Search the web for information",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "fact_check",
                "description": "Check the factual accuracy of a claim",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "claim": {"type": "string", "description": "Claim to verify"}
                    },
                    "required": ["claim"]
                }
            },
            {
                "name": "news_search",
                "description": "Search for latest news on a topic",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "description": "News topic"},
                        "limit": {"type": "integer", "description": "Number of results", "default": 5}
                    },
                    "required": ["topic"]
                }
            }
        ]
    
    def mock_web_search(self, query: str) -> List[Dict[str, Any]]:
        """Mock web search results."""
        return [
            {
                "title": f"关于{query}的最新研究",
                "content": f"最新研究表明，{query}领域出现了重要进展。专家认为这将对未来发展产生深远影响。",
                "source": "学术期刊网",
                "url": "https://example.com/research1"
            },
            {
                "title": f"{query}的发展趋势分析",
                "content": f"分析显示，{query}正在经历快速发展期，预计未来三年将有显著突破。",
                "source": "行业报告",
                "url": "https://example.com/trend1"
            }
        ]
    
    def mock_fact_check(self, claim: str) -> Dict[str, Any]:
        """Mock fact checking result."""
        return {
            "claim": claim,
            "verification_status": "verified",
            "confidence": 0.85,
            "sources": ["权威机构A", "学术研究B"],
            "explanation": f"经过多方验证，该说法基本属实。相关数据来源可靠。"
        }
    
    def mock_news_search(self, topic: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Mock news search results."""
        news_items = [
            {
                "title": f"{topic}领域迎来新突破",
                "content": f"据最新报道，{topic}领域出现重要进展，引起业界广泛关注。",
                "source": "科技日报",
                "published_date": "2024-01-15",
                "url": "https://example.com/news1"
            },
            {
                "title": f"专家解读{topic}发展现状",
                "content": f"权威专家对{topic}的发展现状进行了深入分析，指出了机遇与挑战并存。",
                "source": "人民网",
                "published_date": "2024-01-14",
                "url": "https://example.com/news2"
            }
        ]
        return news_items[:limit]
    
    async def handle_message(self, websocket, message: str) -> None:
        """Handle incoming MCP messages."""
        try:
            data = json.loads(message)
            method = data.get("method")
            params = data.get("params", {})
            request_id = data.get("id")
            
            if method == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "mock-mcp-server",
                            "version": "1.0.0"
                        }
                    }
                }
            
            elif method == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "tools": self.tools
                    }
                }
            
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if tool_name == "web_search":
                    result = self.mock_web_search(arguments.get("query", ""))
                elif tool_name == "fact_check":
                    result = self.mock_fact_check(arguments.get("claim", ""))
                elif tool_name == "news_search":
                    result = self.mock_news_search(
                        arguments.get("topic", ""),
                        arguments.get("limit", 5)
                    )
                else:
                    result = {"error": f"Unknown tool: {tool_name}"}
                
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": result
                    }
                }
            
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
            
            await websocket.send(json.dumps(response))
            
        except json.JSONDecodeError:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": "Parse error"
                }
            }
            await websocket.send(json.dumps(error_response))
        
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "id": data.get("id") if 'data' in locals() else None,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
            await websocket.send(json.dumps(error_response))
    
    async def serve(self, host: str = "localhost", port: int = 8000):
        """Start the MCP server."""
        async def handle_client(websocket, path):
            logger.info(f"Client connected: {websocket.remote_address}")
            try:
                async for message in websocket:
                    await self.handle_message(websocket, message)
            except websockets.exceptions.ConnectionClosed:
                logger.info(f"Client disconnected: {websocket.remote_address}")
            except Exception as e:
                logger.error(f"Error handling client: {e}")
        
        logger.info(f"Starting MCP server on ws://{host}:{port}")
        await websockets.serve(handle_client, host, port)


if __name__ == "__main__":
    server = MockMCPServer()
    asyncio.run(server.serve())