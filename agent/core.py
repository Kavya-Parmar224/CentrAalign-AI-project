import asyncio
import logging
import uuid
import re
import json
from typing import Callable, Optional

from openai import AsyncOpenAI

from agent.schemas import AgentState, AgentStatus, TraceEntry
from agent.tools.registry import ToolRegistry, Tool
from agent.memory import MemoryManager
from agent import planner, verifier

logger = logging.getLogger(__name__)

AGENT_SYSTEM = """\
You are an autonomous AI task worker. You complete tasks by reasoning and using tools.

The Acme Corp Internal Helpdesk portal is located at: http://localhost:5001
Internal APIs available:
- GET http://localhost:5001/api/employees/<email> (Returns employee details)
- GET http://localhost:5001/api/tickets (Returns all tickets)

You follow the ReAct pattern:
1. REASON: Think about what to do next given the task, plan, and current state
2. ACT: Choose and call a tool to take action
3. OBSERVE: The tool result updates your context
4. Repeat until the task is complete

Guidelines:
- Be methodical and precise with tool arguments
- When using the browser, prefer CSS selectors — IDs are most reliable: #element-id
- For dropdown menus (<select>), you MUST use the `select` action (not `click` or `fill`)
- Extract and remember important information (amounts, dates, IDs, URLs) in your reasoning
- If an action fails, try a different approach; do not give up after one failure
- After performing a state-changing action (like granting access or resolving a ticket), ALWAYS verify it was successful by inspecting the screen or API before moving on.
- When the task is fully complete, say TASK_COMPLETE followed by a brief summary
- Use ask_human before any destructive or irreversible action you are uncertain about
- Keep reasoning concise but execution thorough
"""

class AutonomousAgent:
    MAX_ITERATIONS = 25
    MAX_RETRIES = 3

    def __init__(
        self,
        client: AsyncOpenAI,
        tool_registry: ToolRegistry,
        memory: MemoryManager,
        event_emitter: Optional[Callable] = None,
        task_id: str = None,
    ):
        self.client = client
        self.tools = tool_registry
        self.memory = memory
        self.emit = event_emitter or (lambda *a, **kw: asyncio.sleep(0))
        self.task_id = task_id or str(uuid.uuid4())
        self._conversation: list[dict] = []

    async def run(self, task: str) -> AgentState:
        state = AgentState(task_id=self.task_id, task=task, status=AgentStatus.PLANNING)
        await self.emit("status", {"status": "planning", "task": task})

        try:
            state.plan = await planner.create_plan(task, self.client)
            await self.emit("plan_created", {"plan": state.plan.model_dump()})
            logger.info("Plan created with %d steps", len(state.plan.steps))
        except Exception as exc:
            logger.error("Planning failed: %s", exc)
            state.status = AgentStatus.FAILED
            state.final_summary = f"Failed to create plan: {exc}"
            await self.emit("error", {"error": str(exc)})
            await self.emit("task_complete", {
                "summary": state.final_summary,
                "verification": None,
                "screenshots": []
            })
            return state

        state.status = AgentStatus.RUNNING
        state = await self._execute_loop(state)

        state.status = AgentStatus.VERIFYING
        await self.emit("status", {"status": "verifying"})
        try:
            state.verification = await verifier.verify_task(state, self.client)
            await self.emit("verification_done", {"verification": state.verification.model_dump()})
        except Exception as exc:
            logger.error("Verification failed: %s", exc)

        state.final_summary = await self._summarize(state)
        state.status = AgentStatus.DONE
        await self.emit("task_complete", {
            "summary": state.final_summary,
            "verification": state.verification.model_dump() if state.verification else None,
            "screenshots": state.screenshots,
        })
        return state

    async def _execute_loop(self, state: AgentState) -> AgentState:
        iteration = 0
        consecutive_failures = 0

        plan_str = ""
        if state.plan:
            plan_str = "PLAN:\n" + "\n".join(
                f"{s.id}. {s.description} (expected: {s.expected_outcome})"
                for s in state.plan.steps
            )
        self._conversation = [
            {"role": "system", "content": AGENT_SYSTEM},
            {"role": "user", "content": (
                f"TASK: {state.task}\n\n{plan_str}\n\n"
                "Begin executing. Use tools to take real actions. "
                "When the task is fully complete, say TASK_COMPLETE followed by a summary."
            )}
        ]

        while iteration < self.MAX_ITERATIONS:
            iteration += 1
            logger.info("Iteration %d", iteration)

            if iteration > 1 and iteration % 5 == 1:
                mem_ctx = self.memory.get_context(max_chars=1500)
                if mem_ctx:
                    self._conversation.append({
                        "role": "user",
                        "content": f"[Context refresh — key facts so far]\n{mem_ctx}\n\nContinue.",
                    })

            try:
                response = await self.client.chat.completions.create(
                    model="gemini-3.1-flash-lite",
                    temperature=0.1,
                    max_tokens=2000,
                    tools=self.tools.get_all_schemas(),
                    messages=self._conversation,
                )
            except Exception as exc:
                logger.error("LLM call failed: %s", exc)
                if '429' in str(exc) or 'RESOURCE_EXHAUSTED' in str(exc):
                    await self.emit('status', {'status': 'Rate limit hit, waiting 30s...'})
                    await asyncio.sleep(30)
                else:
                    await asyncio.sleep(2)
                continue

            message = response.choices[0].message
            reasoning = message.content or ""

            if getattr(message, "tool_calls", None) is None or not message.tool_calls:
                if "TASK_COMPLETE" in reasoning:
                    logger.info("Agent signaled TASK_COMPLETE")
                    self.memory.add_observation(f"Task complete signal: {reasoning[:400]}")
                    self._conversation.append({"role": "assistant", "content": reasoning})
                    break
                self.memory.add_observation(f"Reasoning (no action): {reasoning[:200]}")
                self._conversation.append({"role": "assistant", "content": reasoning or "Thinking…"})
                self._conversation.append({"role": "user", "content": "Continue — what is your next action?"})
                consecutive_failures += 1
                if consecutive_failures >= 4:
                    logger.warning("Agent stuck — stopping loop")
                    break
                continue

            tool_call = message.tool_calls[0]
            tool_name = tool_call.function.name
            try:
                tool_args = json.loads(tool_call.function.arguments)
            except:
                tool_args = {}
            tool_use_id = tool_call.id

            await self.emit("step_started", {
                "iteration": iteration,
                "tool": tool_name,
                "args": tool_args,
                "reasoning": reasoning,
            })

            result = None
            retries = 0
            while retries <= self.MAX_RETRIES:
                if retries > 0:
                    wait = min(2 ** retries, 16)
                    logger.info("Retry %d for %s (wait %ds)", retries, tool_name, wait)
                    await asyncio.sleep(wait)

                if tool_name == "ask_human":
                    from agent.tools.ask_human_tool import ask_human
                    state.status = AgentStatus.WAITING_HUMAN
                    await self.emit("status", {"status": "waiting_human"})
                    result = await ask_human(
                        question=tool_args.get("question", ""),
                        context=tool_args.get("context", ""),
                        task_id=self.task_id,
                        event_emitter=self.emit,
                    )
                    state.status = AgentStatus.RUNNING
                else:
                    result = await self.tools.dispatch(tool_name, tool_args)

                if result.success:
                    consecutive_failures = 0
                    break
                retries += 1
                logger.warning("Tool %s failed (attempt %d): %s", tool_name, retries, result.error)

            if result.success:
                result_str = str(result.output)[:3000] if result.output is not None else "OK"
            else:
                result_str = f"ERROR: {result.error}"

            if result.screenshot_path:
                state.screenshots.append(result.screenshot_path)
                result_str += f"\n[Screenshot saved: {result.screenshot_path}]"

            obs = f"{tool_name}({_short_args(tool_args)}): {result_str[:1500]}"
            self.memory.add_observation(obs)
            if not result.success:
                consecutive_failures += 1

            await self._extract_facts(tool_name, tool_args, result)

            self._conversation.append(message.model_dump(exclude_unset=True))
            self._conversation.append({
                "role": "tool",
                "tool_call_id": tool_use_id,
                "name": tool_name,
                "content": result_str,
            })

            entry = TraceEntry(
                step_index=iteration,
                reasoning=reasoning or f"Calling {tool_name}",
                tool_name=tool_name,
                tool_args=tool_args,
                result_summary=obs[:1500],
                success=result.success,
            )
            state.trace.append(entry)
            self.memory.save_trace_entry(entry)

            await self.emit("step_completed", {
                "iteration": iteration,
                "tool": tool_name,
                "success": result.success,
                "result": obs[:500],
                "screenshot": result.screenshot_path,
            })

        return state

    async def _extract_facts(self, tool_name: str, args: dict, result) -> None:
        if not result.output:
            return
        output_str = str(result.output)
        ticket_ids = re.findall(r"\bT-\d{3,4}\b", output_str)
        emails = re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", output_str)
        for t in ticket_ids[:3]:
            self.memory.add_fact(f"Ticket ID found: {t}")
        for e in emails[:3]:
            self.memory.add_fact(f"Email found: {e}")
        if tool_name == "browser" and args.get("action") == "navigate":
            self.memory.add_fact(f"Navigated to: {args.get('url', '?')}")

    async def _summarize(self, state: AgentState) -> str:
        facts = "\n".join(f"- {f}" for f in state.memory.facts)
        ver = state.verification
        ver_str = f"{ver.status.value}: {ver.explanation}" if ver else "Not verified"
        prompt = (
            f"Task: {state.task}\n\n"
            f"Key facts: {facts or 'none'}\n\n"
            f"Verification: {ver_str}\n\n"
            "Write a concise 2-3 sentence summary of what was accomplished."
        )
        import asyncio
        for attempt in range(3):
            try:
                r = await self.client.chat.completions.create(
                    model="gemini-3.1-flash-lite",
                    temperature=0.2,
                    max_tokens=400,
                    messages=[
                        {"role": "system", "content": "You are a summarizing agent."},
                        {"role": "user", "content": prompt}
                    ],
                )
                return r.choices[0].message.content
            except Exception as e:
                if '429' in str(e) and attempt < 2:
                    logger.warning(f"Rate limit hit during summarize, waiting 30s... ({e})")
                    await asyncio.sleep(30)
                elif attempt == 2:
                    return f"Task execution complete. Verification: {ver_str}"
            return f"Task execution complete. Verification: {ver_str}"

def _short_args(args: dict) -> str:
    s = str(args)
    return s[:80] + "…" if len(s) > 80 else s
