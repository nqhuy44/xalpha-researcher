import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, Callable, Awaitable, List

from src.agents.analyst.state import AnalystState, Verdict, DebateRound, RefereeDecision
from src.agents.analyst.graph import debate_graph
from src.agents.portfolio.engine import PortfolioEngine

logger = logging.getLogger(__name__)

# O3: warn when a single debate exceeds this input-token budget.
DEBATE_INPUT_TOKEN_BUDGET = 200_000

# Rough per-model pricing (USD per 1M tokens) for cost estimation in DebateTrace.
# Update when Gemini pricing changes; zero means "unknown".
_MODEL_PRICE_PER_M: Dict[str, Tuple[float, float]] = {
    # model substring -> (input_usd_per_M, output_usd_per_M)
    "gemini-2.5-pro": (1.25, 10.00),
    "gemini-2.5-flash": (0.15, 0.60),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-1.5-pro": (1.25, 5.00),
    "gemini-1.5-flash": (0.075, 0.30),
}

_SKIP_MESSAGES = {
    "WARN_LIST":        "⛔ {ticker} nằm trong danh sách cảnh báo và không thể phân tích.",
    "LOW_MARKET_CAP":   "⚠️ {ticker} có vốn hóa quá thấp (dưới 100 tỷ VND). Bỏ qua.",
    "LOW_VOLUME":       "⚠️ {ticker} có khối lượng giao dịch bình quân 30 ngày quá thấp (dưới 100k cổ phiếu/ngày). Bỏ qua.",
    "CACHE_HIT":        "✅ {ticker} đã có phán quyết độ tin cậy cao trong phiên hôm nay. Không cần phân tích lại.",
    "NO_COMPANY_DATA":  "❓ {ticker} chưa có dữ liệu công ty trong hệ thống. Vui lòng đồng bộ dữ liệu trước.",
}

def _skip_message(ticker: str, skip_reason: str) -> str:
    template = _SKIP_MESSAGES.get(skip_reason, "⚠️ {ticker} bị bỏ qua bởi Gatekeeper ({reason}).")
    return template.format(ticker=ticker, reason=skip_reason)


def _estimate_cost(model: str, input_tok: int, output_tok: int) -> Optional[float]:
    model_lower = model.lower()
    for key, (in_price, out_price) in _MODEL_PRICE_PER_M.items():
        if key in model_lower:
            return (input_tok * in_price + output_tok * out_price) / 1_000_000
    return None

class DebateEngine:
    """Facade for executing the Bull vs Bear debate graph."""

    def __init__(self, max_rebuttals: int = 1):
        self.max_rebuttals = max_rebuttals

    @staticmethod
    async def _create_debate_trace(ticker: str, debate_run_id: str) -> Optional[str]:
        """Insert a running DebateTrace row at debate start. Returns its id string."""
        try:
            from src.db.session import async_session_factory
            from src.db.models.observability import DebateTrace
            trace = DebateTrace(id=uuid.UUID(debate_run_id), ticker=ticker, status="running")
            async with async_session_factory() as session:
                session.add(trace)
                await session.commit()
            return debate_run_id
        except Exception as exc:
            logger.warning(f"debate_trace_create_failed: {exc}")
            return None

    @staticmethod
    async def _finalize_debate_trace(
        debate_run_id: str,
        status: str = "completed",
        verdict_id: Optional[str] = None,
    ) -> None:
        """Aggregate llm_usage rows for this run into DebateTrace and apply O3 alert."""
        try:
            from sqlalchemy import select, func as sqlfunc
            from src.db.session import async_session_factory
            from src.db.models.observability import DebateTrace, LLMUsage

            run_uuid = uuid.UUID(debate_run_id)

            async with async_session_factory() as session:
                rows = (await session.execute(
                    select(LLMUsage).where(LLMUsage.debate_run_id == run_uuid)
                )).scalars().all()

                total_input = sum(r.input_tokens for r in rows)
                total_output = sum(r.output_tokens for r in rows)
                total_cached = sum(r.cached_tokens for r in rows)
                total_latency = sum(r.latency_ms for r in rows)

                # Per-node breakdown for the dashboard tile
                breakdown: Dict[str, Any] = {}
                for r in rows:
                    key = r.node or "unknown"
                    entry = breakdown.setdefault(key, {"input_tokens": 0, "output_tokens": 0, "calls": 0, "latency_ms": 0, "model": r.model})
                    entry["input_tokens"] += r.input_tokens
                    entry["output_tokens"] += r.output_tokens
                    entry["calls"] += 1
                    entry["latency_ms"] += r.latency_ms

                # Cost estimate from the model used by the first non-zero row
                models_used = [r.model for r in rows if r.model]
                cost = _estimate_cost(models_used[0], total_input, total_output) if models_used else None

                trace = await session.get(DebateTrace, run_uuid)
                if trace:
                    trace.finished_at = datetime.now(timezone.utc)
                    trace.status = status
                    trace.total_input_tokens = total_input
                    trace.total_output_tokens = total_output
                    trace.total_cached_tokens = total_cached
                    trace.total_latency_ms = total_latency
                    trace.total_llm_calls = len(rows)
                    trace.node_breakdown = breakdown
                    trace.total_cost_usd = cost
                    if verdict_id:
                        trace.verdict_id = uuid.UUID(verdict_id)
                    await session.commit()

            # O3: alert if input tokens exceeded budget
            if total_input > DEBATE_INPUT_TOKEN_BUDGET:
                logger.warning(
                    "debate_token_budget_exceeded",
                    debate_run_id=debate_run_id,
                    total_input_tokens=total_input,
                    budget=DEBATE_INPUT_TOKEN_BUDGET,
                    overage=total_input - DEBATE_INPUT_TOKEN_BUDGET,
                )

            logger.info(
                "debate_trace_finalized",
                debate_run_id=debate_run_id,
                status=status,
                total_input_tokens=total_input,
                total_output_tokens=total_output,
                total_llm_calls=len(rows),
                estimated_cost_usd=cost,
            )

        except Exception as exc:
            logger.warning(f"debate_trace_finalize_failed: {exc}")
        
    async def analyze(self, ticker: str, on_message: Optional[Callable[[str], Awaitable[None]]] = None) -> Optional[Tuple[Verdict, List[RefereeDecision], str, List[DebateRound]]]:
        """
        Runs the full LangGraph debate pipeline for a given ticker.
        Returns the final structured Judge Verdict, a list of Referee Decisions (history), the debate transcript, and structured rounds.
        If on_message callback is provided, strings of debate rounds are streamed to it.
        """
        logger.info(f"Starting Debate Engine for {ticker} (Max Rebuttals: {self.max_rebuttals})")

        debate_run_id = str(uuid.uuid4())
        debate_trace_id = await self._create_debate_trace(ticker, debate_run_id)

        # Initialize state
        initial_state = AnalystState(
            ticker=ticker,
            company_name=ticker,  # Can be enhanced to fetch real name if needed outside graph
            current_round=1,
            max_rounds=self.max_rebuttals + 1,  # +1 because opening is round 1, rebuttals start from round 2
            debate_run_id=debate_run_id,
        )
        
        try:
            current_state = initial_state.model_dump()
            logger.info("Executing LangGraph Debate Workflow via stream...")
            
            final_state_raw = current_state.copy()
            transcript_parts = [f"⚖️ **BIÊN BẢN TRANH BIỆN: {ticker}**"]
            all_rounds = []
            if on_message:
                await on_message(transcript_parts[0])
            
            async for step in debate_graph.astream(current_state, stream_mode="updates"):
                for node_name, node_state in step.items():
                    # We manually merge the verdict for the final return
                    if "verdict" in node_state and node_state["verdict"]:
                        final_state_raw["verdict"] = node_state["verdict"]
                        
                    if "referee_decision" in node_state and node_state["referee_decision"]:
                        final_state_raw["referee_decision"] = node_state["referee_decision"]
                        
                        if "referee_history" in node_state and node_state["referee_history"]:
                            if "referee_history" not in final_state_raw:
                                final_state_raw["referee_history"] = []
                            final_state_raw["referee_history"].extend(node_state["referee_history"])
                            
                        rd = node_state["referee_decision"]
                        msg = f"\n👮 **REFEREE DECISION: {rd.action}** 👮\n_Hợp lệ:_ {rd.is_valid}\n_Kết luận:_ {rd.referee_synthesis}"
                        transcript_parts.append(msg)
                        if on_message:
                            await on_message(msg)
                        
                    if "rounds" in node_state:
                         r = node_state["rounds"][-1]
                         all_rounds.append(r)
                         
                         msg = ""
                         if node_name == "bull":
                             if getattr(r, "bull_arguments", None):
                                 msg_lines = [f"\n--- **VÒNG {r.round_number}** ---\n🐂 **BULL (Mở Đầu):**"]
                                 for a in r.bull_arguments:
                                     msg_lines.append(f"  • {a.claim}\n    _Bằng chứng:_ {a.evidence}")
                                 msg = "\n".join(msg_lines)
                             elif getattr(r, "bull_rebuttals", None):
                                 msg_lines = ["\n🐂 **BULL (Phản Biện):**"]
                                 for a in r.bull_rebuttals:
                                     msg_lines.append(f"  • _Chống lại:_ {a.target_claim}\n    _Phản biện:_ {a.counter_evidence}")
                                 msg = "\n".join(msg_lines)
                         elif node_name == "bear":
                             if getattr(r, "bear_arguments", None):
                                 msg_lines = ["\n🐻 **BEAR (Mở Đầu):**"]
                                 for a in r.bear_arguments:
                                     msg_lines.append(f"  • {a.claim}\n    _Bằng chứng:_ {a.evidence}")
                                 msg = "\n".join(msg_lines)
                             elif getattr(r, "bear_rebuttals", None):
                                 msg_lines = ["\n🐻 **BEAR (Phản Biện):**"]
                                 for a in r.bear_rebuttals:
                                     msg_lines.append(f"  • _Chống lại:_ {a.target_claim}\n    _Phản biện:_ {a.counter_evidence}")
                                 msg = "\n".join(msg_lines)
                                 
                         if msg:
                             transcript_parts.append(msg)
                             if on_message:
                                 await on_message(msg)

            # Gatekeeper short-circuit: graph exited without entering the debate.
            if not final_state_raw.get("gatekeeper_passed", True):
                skip_reason = final_state_raw.get("skip_reason", "unknown")
                logger.info(f"debate_skipped ticker={ticker} reason={skip_reason}")
                if on_message:
                    await on_message(_skip_message(ticker, skip_reason))
                await self._finalize_debate_trace(debate_run_id=debate_run_id, status="skipped")
                return None

            # The final state is a dict representing the AnalystState
            if 'verdict' in final_state_raw and final_state_raw['verdict']:
                # Langchain structured output might return a dict or the Pydantic object
                verdict_data = final_state_raw['verdict']
                if isinstance(verdict_data, Verdict):
                    verdict_obj = verdict_data
                else:
                    verdict_obj = Verdict(**verdict_data)
                
                transcript_str = "\n".join(transcript_parts)
                # Group all_rounds by round_number into merged DebateRound objects since Bull and Bear yield partial rounds
                
                merged_rounds = {}
                for r in all_rounds:
                    if r.round_number not in merged_rounds:
                        merged_rounds[r.round_number] = r
                    else:
                        target = merged_rounds[r.round_number]
                        if r.bull_arguments: target.bull_arguments = r.bull_arguments
                        if r.bear_arguments: target.bear_arguments = r.bear_arguments
                        if r.bull_rebuttals: target.bull_rebuttals = r.bull_rebuttals
                        if r.bear_rebuttals: target.bear_rebuttals = r.bear_rebuttals
                
                final_rounds_list = sorted(merged_rounds.values(), key=lambda x: x.round_number)
                
                # --- Persistence ---
                from src.db.session import async_session_factory
                from src.data.persistence.verdict_repo import VerdictRepository
                
                referee_history = []
                if 'referee_history' in final_state_raw and final_state_raw['referee_history']:
                    for rd_data in final_state_raw['referee_history']:
                        rd_obj = rd_data if isinstance(rd_data, RefereeDecision) else RefereeDecision(**rd_data)
                        referee_history.append(rd_obj)
                elif 'referee_decision' in final_state_raw and final_state_raw['referee_decision']:
                    # Fallback if only single decision is present
                    rd_data = final_state_raw['referee_decision']
                    rd_obj = rd_data if isinstance(rd_data, RefereeDecision) else RefereeDecision(**rd_data)
                    referee_history.append(rd_obj)

                # For repo saving, we can just save the latest referee decision (or adapt DB later)
                # Currently saving the last one is fine for the single-relation table
                latest_referee = referee_history[-1] if referee_history else None

                try:
                    async with async_session_factory() as session:
                        repo = VerdictRepository(session)
                        db_verdict = await repo.save_verdict(ticker, verdict_obj, latest_referee, final_rounds_list, referee_history)
                except Exception as e:
                    logger.error(f"failed_to_persist_verdict for {ticker}: {e}")
                    db_verdict = None

                # Finalize DebateTrace (O2) and O3 token budget alert.
                await self._finalize_debate_trace(
                    debate_run_id=debate_run_id,
                    verdict_id=str(db_verdict.id) if db_verdict else None,
                    status="completed",
                )

                # Trigger Portfolio agent. The engine itself short-circuits when the verdict
                # isn't actionable for this user (not held + non-bullish or low-confidence) —
                # see ACTIONABLE_DECISIONS / PORTFOLIO_TRIGGER_CONFIDENCE in PortfolioEngine.
                # In that case `port_state` is None and no PortfolioSuggestion row is created,
                # which is the correct UI signal (no action recommended).
                logger.info("Triggering Portfolio workflow")
                try:
                    port_engine = PortfolioEngine()
                    port_state = await port_engine.process_signal(ticker, verdict_obj, verdict_id=db_verdict.id if db_verdict else None)
                    logger.info(f"Portfolio execution status: {port_state.execution_status if port_state else 'skipped'}")
                except Exception as e:
                    logger.error(f"Portfolio workflow failed to trigger: {e}")

                return verdict_obj, referee_history, transcript_str, final_rounds_list

            logger.error("Graph finished but no Verdict was produced.")
            await self._finalize_debate_trace(debate_run_id=debate_run_id, status="failed")
            return None

        except Exception as e:
            logger.error(f"Debate Engine failed for {ticker}: {e}", exc_info=True)
            await self._finalize_debate_trace(debate_run_id=debate_run_id, status="failed")
            return None
