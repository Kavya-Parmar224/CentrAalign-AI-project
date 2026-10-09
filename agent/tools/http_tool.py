import httpx, logging
from agent.schemas import ToolResult
logger = logging.getLogger(__name__)

async def http_request(url: str, method: str = 'GET', headers: dict = None,
                        body: dict = None, timeout: int = 30) -> ToolResult:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method=method.upper(),
                url=url,
                headers=headers or {},
                json=body
            )
        try:
            output = response.json()
        except:
            output = response.text[:5000]
        
        # We return success=True even for 4xx/5xx so the LLM can read the status code and body
        return ToolResult(
            success=True,
            output={'status': response.status_code, 'body': output}
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))

HTTP_SCHEMA = {
    'type': 'object',
    'properties': {
        'url': {'type': 'string'},
        'method': {'type': 'string', 'enum': ['GET','POST','PUT','DELETE','PATCH'], 'default': 'GET'},
        'headers': {'type': 'object'},
        'body': {'type': 'object', 'description': 'JSON request body'},
        'timeout': {'type': 'integer', 'default': 30}
    },
    'required': ['url']
}
