import os, csv, json, logging
from agent.schemas import ToolResult
logger = logging.getLogger(__name__)

async def read_file(path: str, encoding: str = 'utf-8') -> ToolResult:
    try:
        if not os.path.exists(path):
            return ToolResult(success=False, error=f'File not found: {path}')
        ext = os.path.splitext(path)[1].lower()
        with open(path, 'r', encoding=encoding, errors='replace') as f:
            content = f.read()
        if ext == '.json':
            try:
                return ToolResult(success=True, output=json.loads(content))
            except:
                pass
        elif ext == '.csv':
            reader = csv.DictReader(content.splitlines())
            return ToolResult(success=True, output=list(reader))
        return ToolResult(success=True, output=content[:10000])
    except Exception as e:
        return ToolResult(success=False, error=str(e))

async def write_file(path: str, content: str, encoding: str = 'utf-8') -> ToolResult:
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, 'w', encoding=encoding) as f:
            f.write(content)
        return ToolResult(success=True, output=f'Written {len(content)} chars to {path}')
    except Exception as e:
        return ToolResult(success=False, error=str(e))

READ_SCHEMA = {
    'type': 'object',
    'properties': {
        'path': {'type': 'string', 'description': 'File path to read'},
        'encoding': {'type': 'string', 'default': 'utf-8'}
    },
    'required': ['path']
}

WRITE_SCHEMA = {
    'type': 'object',
    'properties': {
        'path': {'type': 'string', 'description': 'File path to write'},
        'content': {'type': 'string', 'description': 'Content to write'},
    },
    'required': ['path', 'content']
}
