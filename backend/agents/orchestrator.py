"""Fetch.ai Orchestrator uAgent (SC-FETCH-01).

This agent receives an IntakeResult, stores it in memory, retrieves relevant
context, generates scores using the deterministic scorers, and synthesizes a
final directive.
"""

import os
import time

from uagents import Agent, Context, Model
from uagents_core.utils.registration import (
    RegistrationRequestCredentials,
    register_chat_agent,
)

from backend.intake.schema import IntakeResult
from backend.memory.store import search_similar, store_log
from backend.scorers import score_all


class ProcessIntake(Model):
    intake_dict: dict


class AgentDirective(Model):
    directive: str


orchestrator = Agent(
    name="orchestrator",
    seed="aegis-orchestrator-seed-v1",
    port=8000,
    endpoint=[os.getenv("AGENT_ENDPOINT", "http://127.0.0.1:8000/submit")],
    network="testnet",
)


@orchestrator.on_event("startup")
async def startup(ctx: Context):
    ctx.logger.info("Orchestrator Agent started.")
    ctx.logger.info(f"Agent Address (ASI:One): {orchestrator.address}")

    # Register on Agentverse/ASI:One if credentials are provided
    agentverse_key = os.getenv("AGENTVERSE_KEY")
    agent_seed = os.getenv("AGENT_SEED_PHRASE")
    endpoint = os.getenv("AGENT_ENDPOINT")
    
    if agentverse_key and agent_seed and endpoint:
        base_url = endpoint.replace("/submit", "")
        try:
            register_chat_agent(
                "aegis-backend",
                base_url,
                active=True,
                credentials=RegistrationRequestCredentials(
                    agentverse_api_key=agentverse_key,
                    agent_seed_phrase=agent_seed,
                ),
            )
            ctx.logger.info("Successfully registered with Agentverse/ASI:One.")
        except Exception as e:
            ctx.logger.error(f"Failed to register with Agentverse: {e}")


@orchestrator.on_message(model=ProcessIntake, replies=AgentDirective)
async def handle_intake(ctx: Context, sender: str, msg: ProcessIntake):
    ctx.logger.info(f"Received ProcessIntake from {sender}")
    intake = IntakeResult.model_validate(msg.intake_dict)

    # 1. Store the log in memory
    ts = time.time()
    log_id = store_log(intake, ts)
    ctx.logger.info(f"Stored log with ID: {log_id}")

    # 2. Retrieve relevant context
    query_text = f"Readiness: {intake.subjective_readiness}"
    if intake.soreness:
        query_text += f", Soreness: {intake.soreness[0].body_part}"

    context = search_similar(query_text, k=3)
    ctx.logger.info(f"Retrieved {len(context)} similar logs.")

    # 3. Score the intake
    scores = score_all(intake)
    ctx.logger.info(f"Scores calculated: {scores}")

    # 4. Synthesize directive string
    readiness_score = scores.get("readiness", {}).get("score", 50)
    
    lines = [f"Based on your intake, your readiness score is {readiness_score}/100."]
    if readiness_score < 50:
        lines.append("Recommendation: Take a rest day or focus on light recovery.")
    else:
        lines.append("Recommendation: You are ready for a full training session.")

    if context:
        lines.append(f"Context: Found {len(context)} similar past logs.")

    directive_str = " ".join(lines)

    await ctx.send(sender, AgentDirective(directive=directive_str))


if __name__ == "__main__":
    orchestrator.run()
