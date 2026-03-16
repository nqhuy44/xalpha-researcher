import logging
from typing import Dict, Any, Optional, Tuple, Callable, Awaitable, List
from src.agents.analyst.state import AnalystState, Verdict, DebateRound, RefereeDecision
from src.agents.analyst.graph import debate_graph
from src.agents.portfolio.engine import PortfolioEngine

logger = logging.getLogger(__name__)

class DebateEngine:
    """Facade for executing the Bull vs Bear debate graph."""
    
    def __init__(self, max_rebuttals: int = 1):
        self.max_rebuttals = max_rebuttals
        
    async def analyze(self, ticker: str, on_message: Optional[Callable[[str], Awaitable[None]]] = None) -> Optional[Tuple[Verdict, List[RefereeDecision], str, List[DebateRound]]]:
        """
        Runs the full LangGraph debate pipeline for a given ticker.
        Returns the final structured Judge Verdict, a list of Referee Decisions (history), the debate transcript, and structured rounds.
        If on_message callback is provided, strings of debate rounds are streamed to it.
        """
        logger.info(f"Starting Debate Engine for {ticker} (Max Rebuttals: {self.max_rebuttals})")
        
        # Initialize state
        initial_state = AnalystState(
            ticker=ticker,
            company_name=ticker, # Can be enhanced to fetch real name if needed outside graph
            current_round=1,
            max_rounds=self.max_rebuttals + 1 # +1 because opening is round 1, rebuttals start from round 2
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
                    
                # ALWAYS TRIGGER PORTFOLIO AGENT so the UI gets a PortfolioSuggestion record
                logger.info("Triggering Portfolio workflow for PortfolioSuggestion tracking")
                try:
                    port_engine = PortfolioEngine()
                    port_state = await port_engine.process_signal(ticker, verdict_obj, verdict_id=db_verdict.id if db_verdict else None)
                    logger.info(f"Portfolio execution status: {port_state.execution_status if port_state else 'None'}")
                except Exception as e:
                    logger.error(f"Portfolio workflow failed to trigger: {e}")
                
                return verdict_obj, referee_history, transcript_str, final_rounds_list
                
            logger.error("Graph finished but no Verdict was produced.")
            return None
            
        except Exception as e:
            logger.error(f"Debate Engine failed for {ticker}: {e}", exc_info=True)
            return None
