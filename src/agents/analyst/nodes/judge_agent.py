import logging
import json
from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage

from src.agents.analyst.state import AnalystState, Verdict
from src.services.llm import LLMService

logger = logging.getLogger(__name__)

async def judge_agent_node(state: AnalystState) -> Dict[str, Any]:
    """The Judge Agent: Evaluates the debate and produces the final Verdict."""
    logger.info(f"Judge Agent scoring the debate for {state.ticker}...")
    
    llm = LLMService()
    
    # Format the entire debate history for the Judge
    debate_transcript = []
    
    # Sort rounds just in case
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
    
    system_prompt = llm.load_prompt("judge_system.txt")
    user_prompt = f"TICKER: {state.ticker}\n\nRAW CONTEXT DATA:\n{state.context}\n\nDEBATE TRANSCRIPT:\n{transcript_str}\n\n"
    
    # Inject Referee Feedback on Retries
    if getattr(state, "referee_history", None) and len(state.referee_history) > 0:
        last_ref_decision = state.referee_history[-1]
        user_prompt += "🚨 MẶT LỆNH QUAN TRỌNG TỪ REFEREE (LẦN TRƯỚC BẠN ĐÃ BỊ TỪ CHỐI!):\n"
        user_prompt += f"- Action: {last_ref_decision.action}\n"
        user_prompt += f"- Nhận xét (Synthesis): {last_ref_decision.referee_synthesis}\n"
        if last_ref_decision.hallucinations_detected:
            user_prompt += f"- Lỗi Hallucination phát hiện: {', '.join(last_ref_decision.hallucinations_detected)}\n"
        if last_ref_decision.logic_flaws:
            user_prompt += f"- Lỗi suy luận/Logic: {', '.join(last_ref_decision.logic_flaws)}\n"
        if last_ref_decision.bias_assessment:
            user_prompt += f"- Đánh giá thiên vị: {last_ref_decision.bias_assessment}\n"
        user_prompt += "\n👉 YÊU CẦU: Dựa vào các phân tích bên trên, bạn hãy sửa lại lỗi logic của mình và ĐƯA RA MỘT VERDICT MỚI HỢP LÝ HƠN. KHÔNG được lặp lại các lỗi trên.\n\n"
    
    user_prompt += "Render your final Verdict."
    
    try:
        verdict = await llm.generate_structured(system_prompt, user_prompt, Verdict, role="judge", agent_name="judge")
        logger.info(f"Judge rendered verdict with confidence {verdict.confidence_score}%")
        # Increment attempt counter
        return {"verdict": verdict, "judge_attempts": state.judge_attempts + 1}
    except Exception as e:
        logger.error(f"Judge Agent failed to produce structured JSON: {e}")
        raise
