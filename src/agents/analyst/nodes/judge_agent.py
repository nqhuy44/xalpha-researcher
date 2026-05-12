import logging
from typing import Any, Dict

from src.agents.analyst.state import AnalystState, Verdict
from src.agents.analyst.utils.debate_formatting import format_debate_transcript
from src.services.llm import LLMService

logger = logging.getLogger(__name__)

async def judge_agent_node(state: AnalystState) -> Dict[str, Any]:
    """The Judge Agent: Evaluates the debate and produces the final Verdict."""
    logger.info(f"Judge Agent scoring the debate for {state.ticker}...")

    llm = LLMService()
    transcript_str = format_debate_transcript(state.rounds)
    
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
        verdict = await llm.generate_structured(
            system_prompt, user_prompt, Verdict, role="judge", agent_name="judge",
            ticker=state.ticker, node="judge", debate_run_id=state.debate_run_id,
        )
        logger.info(f"Judge rendered verdict with confidence {verdict.confidence_score}%")
        # Increment attempt counter
        return {"verdict": verdict, "judge_attempts": state.judge_attempts + 1}
    except Exception as e:
        logger.error(f"Judge Agent failed to produce structured JSON: {e}")
        raise
