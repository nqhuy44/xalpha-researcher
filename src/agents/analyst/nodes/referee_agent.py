import logging
from typing import Any, Dict

from src.agents.analyst.state import AnalystState, RefereeDecision
from src.agents.analyst.utils.debate_formatting import format_debate_transcript
from src.services.llm import LLMService

logger = logging.getLogger(__name__)

async def referee_agent_node(state: AnalystState) -> Dict[str, Any]:
    """
    The Referee Agent:
    Validates the Judge's Verdict against the Debate Transcript and Context to catch
    hallucinations, logical errors, or extreme bias.
    """
    logger.info(f"Referee Agent invoked to verify the Judge's verdict for {state.ticker}...")

    llm = LLMService()

    # Same transcript shape the Judge saw — single source of truth in debate_formatting.
    transcript_str = format_debate_transcript(state.rounds)
    
    # 2. Format the verdict to review
    verdict_str = state.verdict.model_dump_json(indent=2) if state.verdict else "ERROR: No verdict provided."
    
    # 3. Construct Prompts
    system_prompt = llm.load_prompt("referee_system.txt")
    user_prompt = (
        f"TICKER: {state.ticker}\n\n"
        f"--- RAW CONTEXT DATA ---\n{state.context}\n\n"
        f"--- DEBATE TRANSCRIPT ---\n{transcript_str}\n\n"
        f"--- JUDGE VERDICT TO REVIEW ---\n{verdict_str}\n\n"
        f"Execute your verification process and output your RefereeDecision JSON."
    )
    
    try:
        # Note: we use "judge" role here for high-quality deep reasoning, 
        # but allow agent overrides explicitly named "referee" if configured.
        decision = await llm.generate_structured(
            system_prompt, 
            user_prompt, 
            RefereeDecision, 
            role="judge", 
            agent_name="referee"
        )
        logger.info(f"Referee action: {decision.action} | Valid: {decision.is_valid}")
        return {"referee_decision": decision, "referee_history": [decision]}
    except Exception as e:
        logger.error(f"Referee Agent failed validation query: {e}")
        # In case of failure, we return inconclusive to not crash the engine, but flag the issue
        emergency_decision = RefereeDecision(
            is_valid=False,
            hallucinations_detected=[],
            logic_flaws=[f"System error during referee check: {str(e)}"],
            bias_assessment="Unknown due to error",
            action="INCONCLUSIVE",
            referee_synthesis="Referee service failed. Manual review recommended."
        )
        return {"referee_decision": emergency_decision, "referee_history": [emergency_decision]}
