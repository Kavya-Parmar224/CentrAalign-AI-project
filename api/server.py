import os, asyncio, logging, uuid
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from openai import AsyncOpenAI
from dotenv import load_dotenv
load_dotenv()

from agent.core import AutonomousAgent
from agent.memory import MemoryManager
from agent.tools.registry import ToolRegistry, Tool
from agent.tools.browser_tool import BrowserTool, create_browser_tool
from agent.tools import file_tool, http_tool
from agent.tools.ask_human_tool import submit_answer
from agent.schemas import AgentState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title='Autonomous AI Task Worker', version='1.0.0')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

# Global state
client = AsyncOpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.environ.get("GEMINI_API_KEY", "")
)
running_agents: dict[str, AgentState] = {}
active_agent_tasks: dict[str, asyncio.Task] = {}
ws_connections: dict[str, list[WebSocket]] = {}
browsers: dict[str, BrowserTool] = {}

class TaskRequest(BaseModel):
    task: str

class AnswerRequest(BaseModel):
    answer: str

@app.post('/api/task')
async def start_task(req: TaskRequest):
    task_id = str(uuid.uuid4())[:8]
    
    # Create browser and tools
    browser = BrowserTool()
    browsers[task_id] = browser
    bt_kwargs = create_browser_tool(browser)
    
    registry = ToolRegistry()
    registry.register(Tool(**bt_kwargs))
    registry.register(Tool(
        name='read_file',
        description='Read a local file. Supports text, CSV, JSON.',
        input_schema=file_tool.READ_SCHEMA,
        fn=file_tool.read_file
    ))
    registry.register(Tool(
        name='write_file',
        description='Write content to a local file.',
        input_schema=file_tool.WRITE_SCHEMA,
        fn=file_tool.write_file
    ))
    registry.register(Tool(
        name='http_request',
        description='Make HTTP requests to APIs or web services.',
        input_schema=http_tool.HTTP_SCHEMA,
        fn=http_tool.http_request
    ))
    from agent.tools.ask_human_tool import ASK_HUMAN_SCHEMA
    registry.register(Tool(
        name='ask_human',
        description='Ask the human user a question or request approval. Use when uncertain or before destructive actions.',
        input_schema=ASK_HUMAN_SCHEMA,
        fn=lambda **kw: asyncio.sleep(0)
    ))
    
    memory = MemoryManager(task_id=task_id, client=client)
    ws_connections[task_id] = []
    
    async def emit(event_type: str, data: dict):
        msg = {'type': event_type, 'data': data}
        dead = []
        for ws in ws_connections.get(task_id, []):
            try:
                await ws.send_json(msg)
            except:
                dead.append(ws)
        for ws in dead:
            try:
                ws_connections[task_id].remove(ws)
            except ValueError:
                pass
    
    agent = AutonomousAgent(
        client=client,
        tool_registry=registry,
        memory=memory,
        event_emitter=emit,
        task_id=task_id
    )
    
    state = AgentState(task_id=task_id, task=req.task)
    running_agents[task_id] = state
    
    async def run_agent():
        try:
            result = await agent.run(req.task)
            running_agents[task_id] = result
        except asyncio.CancelledError:
            logger.info(f"Task {task_id} was cancelled by user.")
            state = running_agents.get(task_id)
            if state:
                state.status = 'failed'
                state.final_summary = "Task was manually stopped by the user."
            await emit('error', {'error': 'Task was manually stopped by the user.'})
            await emit('task_complete', {'summary': 'Task was manually stopped by the user.', 'verification': None, 'screenshots': []})
        finally:
            try:
                await browser.close()
            except:
                pass
            active_agent_tasks.pop(task_id, None)
    
    t = asyncio.create_task(run_agent())
    active_agent_tasks[task_id] = t
    return {'task_id': task_id, 'status': 'started'}

@app.post('/api/task/{task_id}/stop')
async def stop_task(task_id: str):
    task = active_agent_tasks.get(task_id)
    if task and not task.done():
        task.cancel()
        return {'status': 'stopped'}
    raise HTTPException(404, 'Task not found or already finished')

@app.get('/api/task/{task_id}')
async def get_task(task_id: str):
    state = running_agents.get(task_id)
    if not state:
        raise HTTPException(404, 'Task not found')
    return state.model_dump()

@app.post('/api/task/{task_id}/answer')
async def submit_human_answer(task_id: str, req: AnswerRequest):
    ok = submit_answer(task_id, req.answer)
    if not ok:
        raise HTTPException(400, 'No pending question for this task')
    return {'status': 'answered'}

@app.websocket('/ws/{task_id}')
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    await websocket.accept()
    if task_id not in ws_connections:
        ws_connections[task_id] = []
    ws_connections[task_id].append(websocket)
    logger.info(f'WS connected for task {task_id}')
    try:
        state = running_agents.get(task_id)
        if state:
            await websocket.send_json({'type': 'state', 'data': state.model_dump()})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        try:
            ws_connections[task_id].remove(websocket)
        except ValueError:
            pass
        logger.info(f'WS disconnected for task {task_id}')

@app.get('/api/screenshot/{task_id}/{filename}')
async def get_screenshot(task_id: str, filename: str):
    screenshot_dir = os.environ.get('SCREENSHOT_DIR', './screenshots')
    path = os.path.join(screenshot_dir, filename)
    if not os.path.exists(path):
        raise HTTPException(404, 'Screenshot not found')
    return FileResponse(path)

@app.get('/health')
async def health():
    return {'status': 'ok'}
