"""council.py — headless multi-model deliberation (Karpathy llm-council pattern).
3 stages: (1) first opinions, (2) anonymized cross-review/rank, (3) Chairman synthesis.
Calls providers DIRECTLY (Anthropic + Gemini) — no OpenRouter needed.
Used by the Planner and QA/Validation nodes of the agentic dev loop.

Env: ANTHROPIC_API_KEY, GEMINI_API_KEY, CHAIRMAN_MODEL, COUNCIL_MODELS (comma-sep)
"""
import os, asyncio, json

CHAIRMAN = os.getenv("CHAIRMAN_MODEL", "claude-sonnet-4-5")
MEMBERS  = [m.strip() for m in os.getenv(
    "COUNCIL_MODELS", "gemini-2.5-flash,claude-haiku-4-5,gemini-2.5-pro").split(",") if m.strip()]

async def _call(model: str, prompt: str) -> str:
    """Route a model id to the right provider SDK."""
    if model.startswith("gemini"):
        from google import genai
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        r = await asyncio.to_thread(client.models.generate_content, model=model, contents=prompt)
        return r.text
    else:  # claude-*
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        r = await asyncio.to_thread(
            client.messages.create, model=model, max_tokens=2000,
            messages=[{"role": "user", "content": prompt}])
        return r.content[0].text

async def council(question: str, criteria: str = "") -> dict:
    ctx = f"QUESTION:\n{question}\n\nSUCCESS CRITERIA:\n{criteria}\n" if criteria else question
    # Stage 1: first opinions (parallel)
    s1 = await asyncio.gather(*[_call(m, ctx) for m in MEMBERS])
    opinions = {f"Response {chr(65+i)}": s1[i] for i in range(len(s1))}
    # Stage 2: anonymized cross-review + ranking
    blob = "\n\n".join(f"{k}:\n{v}" for k, v in opinions.items())
    rev_prompt = (f"{ctx}\n\nAnonymous responses:\n{blob}\n\n"
                  "Critique each for correctness vs the criteria, then rank best->worst with reasons.")
    s2 = await asyncio.gather(*[_call(m, rev_prompt) for m in MEMBERS])
    # Stage 3: Chairman synthesis
    chair_prompt = (f"{ctx}\n\nCouncil responses:\n{blob}\n\nCouncil reviews:\n"
                    + "\n\n".join(s2) +
                    "\n\nSynthesize ONE final answer. Return JSON: "
                    '{"decision": "...", "dissents": ["..."], "confidence": 0.0}')
    final = await _call(CHAIRMAN, chair_prompt)
    try:
        start = final.index("{"); parsed = json.loads(final[start:final.rindex("}")+1])
    except Exception:
        parsed = {"decision": final, "dissents": [], "confidence": None}
    return {"opinions": opinions, "reviews": s2, **parsed}

if __name__ == "__main__":
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "Sanity check: reply with a one-line plan."
    print(json.dumps(asyncio.run(council(q)), indent=2))
