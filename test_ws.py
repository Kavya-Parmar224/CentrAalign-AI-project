import asyncio
import httpx
import websockets
import json

tasks = [
    "Find the open high-priority ticket, look up the user's manager via the API, and write a summary file.",
    "Check the onboarding ticket, navigate to the provisioning page, grant them GitHub access, and mark the ticket as resolved.",
    "Get all open tickets via the API and summarize the current workload."
]

async def run_task(task_text):
    print(f"\n{'='*50}\nStarting Task: {task_text}\n{'='*50}", flush=True)
    async with httpx.AsyncClient() as client:
        res = await client.post('http://localhost:8000/api/task', json={'task': task_text})
        task_id = res.json()['task_id']
        print(f"Task started: {task_id}", flush=True)
        
        uri = f"ws://localhost:8000/ws/{task_id}"
        async with websockets.connect(uri) as ws:
            while True:
                msg = await ws.recv()
                data = json.loads(msg)
                type_ = data.get('type')
                payload = data.get('data', {})
                
                if type_ == 'status':
                    print(f"Status: {payload.get('status')}", flush=True)
                elif type_ == 'step_started':
                    print(f" -> Reason: {payload.get('reasoning')}", flush=True)
                    print(f" -> Calling: {payload.get('tool')}({payload.get('args')})", flush=True)
                elif type_ == 'step_completed':
                    print(f" <- Result: {payload.get('result')}", flush=True)
                elif type_ == 'task_complete':
                    print(f"DONE! Summary: {payload.get('summary')}", flush=True)
                    break
                elif type_ == 'error':
                    print(f"ERROR: {payload}", flush=True)
                    break
                elif type_ == 'human_request':
                    print(f"WAITING ON HUMAN: {payload}", flush=True)
                    # answer it automatically
                    await client.post(f'http://localhost:8000/api/task/{task_id}/answer', json={'answer': 'Yes, proceed.'})

async def main():
    for t in tasks:
        await run_task(t)

if __name__ == '__main__':
    asyncio.run(main())
