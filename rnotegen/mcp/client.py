"""
MCP (Model Context Protocol) client implementation.
"""

import asyncio
import websockets
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MCPTool:
    """Represents an MCP tool."""
    name: str
    description: str
    parameters: Dict[str, Any]


class MCPClient:
    """MCP protocol client for external tool integration."""
    
    def __init__(self, server_url: str = "ws://localhost:8000"):
        self.server_url = server_url
        self.websocket = None
        self.tools: List[MCPTool] = []
        self.request_id = 0
    
    async def connect(self) -> None:
        """Connect to MCP server."""
        try:
            self.websocket = await websockets.connect(self.server_url)
            await self._initialize_session()
            logger.info(f"Connected to MCP server: {self.server_url}")
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            raise
    
    async def _initialize_session(self) -> None:
        """Initialize MCP session and get available tools."""
        # Send initialization request
        init_request = {
            "jsonrpc": "2.0",
            "id": self._get_request_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "columnist-agent",
                    "version": "1.0.0"
                }
            }
        }
        
        await self._send_request(init_request)
        response = await self._receive_response()
        
        if response.get("error"):
            raise Exception(f"MCP initialization failed: {response['error']}")
        
        # Get available tools
        await self._list_tools()
    
    async def _list_tools(self) -> None:
        """List available tools from MCP server."""
        list_request = {
            "jsonrpc": "2.0",
            "id": self._get_request_id(),
            "method": "tools/list"
        }
        
        await self._send_request(list_request)
        response = await self._receive_response()
        
        if response.get("result", {}).get("tools"):
            self.tools = [
                MCPTool(
                    name=tool["name"],
                    description=tool["description"],
                    parameters=tool.get("inputSchema", {})
                )
                for tool in response["result"]["tools"]
            ]
            logger.info(f"Loaded {len(self.tools)} MCP tools")
        else:
            logger.warning("No MCP tools available")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool."""
        if not self.websocket:
            await self.connect()
        
        call_request = {
            "jsonrpc": "2.0",
            "id": self._get_request_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        try:
            await self._send_request(call_request)
            response = await self._receive_response()
            
            if response.get("error"):
                logger.error(f"Tool call failed: {response['error']}")
                return {"error": response["error"]}
            
            return response.get("result", {})
            
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return {"error": str(e)}
    
    async def search_internet(self, query: str) -> List[Dict[str, Any]]:
        """Search internet using MCP tools."""
        # Try to find a web search tool
        search_tools = [tool for tool in self.tools if "search" in tool.name.lower()]
        
        if not search_tools:
            logger.warning("No search tools available")
            return []
        
        search_tool = search_tools[0]
        result = await self.call_tool(search_tool.name, {"query": query})
        
        if result.get("error"):
            return []
        
        # Parse search results (format may vary by tool)
        results = result.get("content", [])
        if isinstance(results, str):
            try:
                results = json.loads(results)
            except json.JSONDecodeError:
                results = [{"content": results, "source": "search"}]
        
        return results[:5]  # Limit results
    
    async def fact_check(self, claims: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fact-check claims using MCP tools."""
        # Try to find a fact-checking tool
        fact_check_tools = [tool for tool in self.tools if "fact" in tool.name.lower() or "verify" in tool.name.lower()]
        
        if not fact_check_tools:
            logger.info("No fact-checking tools available, skipping fact-check")
            return claims
        
        fact_check_tool = fact_check_tools[0]
        fact_checked_results = []
        
        for claim in claims[:3]:  # Limit to avoid too many requests
            result = await self.call_tool(fact_check_tool.name, {"claim": claim.get("content", "")})
            
            if not result.get("error"):
                fact_checked_results.append({
                    **claim,
                    "fact_checked": True,
                    "verification_result": result
                })
            else:
                fact_checked_results.append({
                    **claim,
                    "fact_checked": False
                })
        
        return fact_checked_results
    
    async def get_news(self, topic: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get latest news about a topic."""
        news_tools = [tool for tool in self.tools if "news" in tool.name.lower()]
        
        if not news_tools:
            logger.warning("No news tools available")
            return []
        
        news_tool = news_tools[0]
        result = await self.call_tool(news_tool.name, {"topic": topic, "limit": limit})
        
        if result.get("error"):
            return []
        
        return result.get("content", [])
    
    def _get_request_id(self) -> int:
        """Get next request ID."""
        self.request_id += 1
        return self.request_id
    
    async def _send_request(self, request: Dict[str, Any]) -> None:
        """Send request to MCP server."""
        if not self.websocket:
            raise Exception("Not connected to MCP server")
        
        await self.websocket.send(json.dumps(request))
    
    async def _receive_response(self) -> Dict[str, Any]:
        """Receive response from MCP server."""
        if not self.websocket:
            raise Exception("Not connected to MCP server")
        
        response_text = await self.websocket.recv()
        return json.loads(response_text)
    
    async def close(self) -> None:
        """Close MCP connection."""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            logger.info("MCP connection closed")
    
    def __del__(self):
        """Cleanup on deletion."""
        if self.websocket:
            asyncio.create_task(self.close())