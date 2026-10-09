import asyncio
import httpx
import json

tasks = [
    "Find the open high-priority ticket, look up the user's manager via the API, and write a summary file.",
    "Check the onboarding ticket, navigate to the provisioning page, grant them GitHub access, and mark the ticket as resolved.",
    "Get all open tickets via the API and summarize the current workload."
]

async def run_task(task_text):
    print(f"\n{'='*50}\nStarting Task: {task_text}\n{'='*50}", flush=True)
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            res = await client.post('http://localhost:8000/api/task', json={'task': task_text})
            if res.status_code != 200:
                print("Failed to start:", res.text, flush=True)
                return
                
            task_id = res.json()['task_id']
            print(f"Task started: {task_id}", flush=True)
            
            while True:
                await asyncio.sleep(2)
                state = await client.get(f'http://localhost:8000/api/task/{task_id}')
                data = state.json()
                status = data['status']
                
                print(f"Status: {status}")
                
                if status in ['done', 'failed', 'cancelled', 'waiting_human']:
                    print(f"Task finished with status: {status}")
                    print("\nTrace summary:")
                    for entry in data.get('trace', []):
                        success = "OK" if entry.get('success') else "FAIL"
                        print(f" - [{entry['step_index']}] [{entry['tool_name']}] ({success}) {str(entry.get('result_summary'))[:200]}")
                    print(f"\nFinal Summary: {data.get('final_summary')}")
                    
                    if data.get('verification'):
                        print(f"Verification: {data['verification']['status']} - {data['verification']['explanation']}")
                    
                    if status == 'waiting_human':
                        print("Agent is asking for human input. Aborting test.")
                        await client.post(f'http://localhost:8000/api/task/{task_id}/stop')
                    return data
        except Exception as e:
            print(f"Test error: {e}")

async def main():
    for task in tasks:
        await run_task(task)

if __name__ == '__main__':
    asyncio.run(main())
