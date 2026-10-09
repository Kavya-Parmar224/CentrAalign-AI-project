from typing import Callable, Any
from agent.schemas import ToolResult
import logging

logger = logging.getLogger(__name__)

class Tool:
    def __init__(self, name: str, description: str, input_schema: dict, fn: Callable):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.fn = fn
    
    def to_openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema
            }
        }

class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}
    
    def register(self, tool: Tool):
        self._tools[tool.name] = tool
        logger.info(f'Registered tool: {tool.name}')
    
    def get_tool(self, name: str) -> Tool:
        return self._tools.get(name)
    
    def get_all_schemas(self) -> list[dict]:
        return [t.to_openai_schema() for t in self._tools.values()]
    
    async def dispatch(self, tool_name: str, args: dict, state=None) -> ToolResult:
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolResult(success=False, error=f'Unknown tool: {tool_name}')
        try:
            result = await tool.fn(**args)
            if isinstance(result, ToolResult):
                return result
            return ToolResult(success=True, output=result)
        except Exception as e:
            logger.exception(f'Tool {tool_name} raised exception')
            return ToolResult(success=False, error=str(e))
