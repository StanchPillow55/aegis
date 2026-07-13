import time
import logging

from backend.intake.schema import IntakeResult
from backend.providers.memory import search_similar, store_log
from backend.scorers import score_all
from backend.providers.llm import generate_directive
from backend.providers.tracing import traced_span

logger = logging.getLogger(__name__)


class Orchestrator:
    """Local typed orchestrator replacing Fetch.ai uAgents."""

    @traced_span("orchestrator.process_intake", operation="process")
    def process_intake(self, intake: IntakeResult) -> str:
        logger.info("Processing intake")

        # 1. Store the log in memory
        ts = time.time()
        log_id = store_log(intake, ts)
        logger.info(f"Stored log with ID: {log_id}")

        # 2. Retrieve relevant context
        query_text = f"Readiness: {intake.subjective_readiness}"
        if intake.soreness:
            query_text += f", Soreness: {intake.soreness[0].body_part}"

        context_logs = search_similar(query_text, k=3)
        logger.info(f"Retrieved {len(context_logs)} similar logs.")

        # 3. Score the intake
        scores = score_all(intake)
        logger.info(f"Scores calculated: {scores}")

        # 4. Synthesize directive string
        directive_str = generate_directive(intake, context_logs, scores)
        logger.info(f"Generated directive: {directive_str}")

        return directive_str


orchestrator = Orchestrator()
