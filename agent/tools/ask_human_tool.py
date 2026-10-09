import asyncio, logging
from agent.schemas import ToolResult
logger = logging.getLogger(__name__)

# Global store for pending questions per task
_pending: dict[str, asyncio.Future] = {}

async def ask_human(question: str, context: str = '', task_id: str = '',
                     event_emitter=None, timeout: int = 120) -> ToolResult:
    """Pauses agent and asks human a question. Requires event_emitter."""
    if event_emitter:
        await event_emitter('human_request', {
            'question': question,
            'context': context,
            'task_id': task_id
        })
    loop = asyncio.get_event_loop()
    fut = loop.create_future()
    _pending[task_id] = fut
    try:
        answer = await asyncio.wait_for(fut, timeout=timeout)
        return ToolResult(success=True, output={'answer': answer})
    except asyncio.TimeoutError:
        _pending.pop(task_id, None)
        return ToolResult(success=False, error='Human did not respond within timeout')

def submit_answer(task_id: str, answer: str):
    """Called by the API when the human submits their answer."""
    fut = _pending.pop(task_id, None)
    if fut and not fut.done():
        fut.set_result(answer)
        return True
    return False

ASK_HUMAN_SCHEMA = {
    'type': 'object',
    'properties': {
        'question': {'type': 'string', 'description': 'The question to ask the human'},
        'context': {'type': 'string', 'description': 'Additional context to help the human answer'}
    },
    'required': ['question']
}
