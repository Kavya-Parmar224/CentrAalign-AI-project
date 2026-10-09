import json, logging
from openai import AsyncOpenAI
from agent.schemas import TaskPlan, Step

logger = logging.getLogger(__name__)

PLANNER_SYSTEM = '''
You are a task planning agent for an autonomous AI worker system.
Your job is to decompose a user's natural language task into a clear, ordered execution plan.

The AI worker has these tools:
- browser: Navigate websites, click elements, fill forms, extract text, take screenshots
- read_file: Read local files (text, CSV, JSON)
- write_file: Write content to files
- http_request: Make HTTP API calls (GET, POST, PUT, DELETE)
- ask_human: Ask the human for clarification or approval when uncertain

The Acme Corp Internal Helpdesk portal is located at: http://localhost:5001
Internal APIs available:
- GET http://localhost:5001/api/employees/<email>
- GET http://localhost:5001/api/tickets

Return a JSON object with this exact structure:
{
  "task_description": "<concise restatement of what needs to be done>",
  "steps": [
    {
      "id": 1,
      "description": "<what to do in this step>",
      "suggested_tool": "<tool name or null>",
      "expected_outcome": "<what success looks like for this step>"
    }
  ],
  "verification_criteria": [
    "<specific, checkable criterion for overall task success>"
  ]
}

Be practical and specific. Each step should be a single, concrete action.
Include a verification step at the end to confirm the task was completed.
'''

async def create_plan(task: str, client: AsyncOpenAI) -> TaskPlan:
    logger.info(f'Planning task: {task[:100]}')
    
    for attempt in range(3):
        try:
            response = await client.chat.completions.create(
                model='gemini-3.1-flash-lite',
                temperature=0.2,
                max_tokens=2000,
                messages=[
                    {'role': 'system', 'content': PLANNER_SYSTEM},
                    {'role': 'user', 'content': f'Plan this task: {task}'}
                ]
            )
            break
        except Exception as e:
            if '429' in str(e) and attempt < 2:
                import asyncio
                logger.warning(f"Rate limit hit during planning, waiting 30s... ({e})")
                await asyncio.sleep(30)
            else:
                raise e
                
    raw = response.choices[0].message.content
    import re
    m = re.search(r'\{.*\}', raw, re.DOTALL)
    if m:
        data = json.loads(m.group())
    else:
        data = json.loads(raw)
    
    steps = [Step(**s) for s in data['steps']]
    return TaskPlan(
        task_description=data['task_description'],
        steps=steps,
        verification_criteria=data['verification_criteria']
    )
