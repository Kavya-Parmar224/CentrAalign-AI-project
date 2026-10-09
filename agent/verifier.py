import re
import json
import logging

from openai import AsyncOpenAI

from agent.schemas import AgentState, VerificationResult, VerificationStatus

logger = logging.getLogger(__name__)

VERIFIER_SYSTEM = """\
You are a verification agent. Your job is to honestly assess whether an autonomous AI worker
successfully completed a user's task.

You will receive:
1. The original task
2. The verification criteria established at planning time
3. A condensed execution trace (what the agent did and observed)
4. Key facts discovered during execution

Respond ONLY with a JSON object — no prose, no markdown:
{
  "status": "verified" | "partial" | "failed",
  "explanation": "<detailed explanation of what was and wasn't achieved>",
  "evidence": ["<specific piece of evidence 1>", "<specific piece of evidence 2>"]
}

Rules:
- Only mark "verified" if there is clear, specific evidence the goal was achieved
- "partial" means some but not all criteria were met
- "failed" means the task was not meaningfully accomplished
- Be honest — do not give the benefit of the doubt without evidence
"""

async def verify_task(state: AgentState, client: AsyncOpenAI) -> VerificationResult:
    logger.info("Running verification for task %s", state.task_id)

    criteria_str = "\n".join(
        f"- {c}" for c in (state.plan.verification_criteria if state.plan else [])
    )

    trace_str = "\n".join(
        f"Step {e.step_index}: [{e.tool_name or 'reasoning'}] "
        f"{e.reasoning[:300]} -> {(e.result_summary or '')[:800]}"
        for e in state.trace[-20:]
    )

    facts_str = "\n".join(f"- {f}" for f in state.memory.facts) or "(no key facts extracted)"

    prompt = (
        f"Original task: {state.task}\n\n"
        f"Verification criteria:\n{criteria_str or '(none specified)'}\n\n"
        f"Execution trace (last 20 steps):\n{trace_str or '(empty)'}\n\n"
        f"Key facts discovered:\n{facts_str}\n\n"
        "Was the task successfully completed?"
    )

    import asyncio
    for attempt in range(3):
        try:
            response = await client.chat.completions.create(
                model="gemini-3.1-flash-lite",
                temperature=0.2,
                max_tokens=1000,
                messages=[
                    {"role": "system", "content": VERIFIER_SYSTEM},
                    {"role": "user", "content": prompt}
                ],
            )
            break
        except Exception as e:
            if '429' in str(e) and attempt < 2:
                logger.warning(f"Rate limit hit during verification, waiting 30s... ({e})")
                await asyncio.sleep(30)
            else:
                raise e
    raw = response.choices[0].message.content.strip()

    m = re.search(r"\{.*\}", raw, re.DOTALL)
    data = json.loads(m.group() if m else raw)

    return VerificationResult(
        status=VerificationStatus(data["status"]),
        explanation=data["explanation"],
        evidence=data.get("evidence", []),
    )
