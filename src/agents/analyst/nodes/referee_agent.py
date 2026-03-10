import logging
from typing import Dict, Any

from src.agents.analyst.state import AnalystState, RefereeDecision
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
    
    # 1. Format the transcript (same as the judge saw)
    debate_transcript = []
    sorted_rounds = sorted(state.rounds, key=lambda x: x.round_number)
    
    for r in sorted_rounds:
        debate_transcript.append(f"\n--- ROUND {r.round_number} ---")
        if r.round_number == 1:
            debate_transcript.append("BULL OPENING ARGUMENTS:")
            for a in r.bull_arguments:
                debate_transcript.append(f"- [Strength {a.strength}/10] {a.claim}\n  Evidence: {a.evidence}")
            debate_transcript.append("\nBEAR OPENING ARGUMENTS:")
            for a in r.bear_arguments:
                debate_transcript.append(f"- [Strength {a.strength}/10] {a.claim}\n  Evidence: {a.evidence}")
        else:
            debate_transcript.append("BULL REBUTTALS:")
            for rb in r.bull_rebuttals:
                debate_transcript.append(f"- Target: {rb.target_claim}\n  Counter: {rb.counter_evidence}")
            debate_transcript.append("\nBEAR REBUTTALS:")
            for rb in r.bear_rebuttals:
                debate_transcript.append(f"- Target: {rb.target_claim}\n  Counter: {rb.counter_evidence}")
                
    transcript_str = "\n".join(debate_transcript)
    
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
