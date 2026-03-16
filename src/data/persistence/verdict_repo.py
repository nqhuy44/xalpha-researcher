import structlog
from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from src.db.models.analyst import DebateVerdict
from src.agents.analyst.state import Verdict, RefereeDecision, DebateRound

logger = structlog.get_logger(__name__)

class VerdictRepository:
    """Repository for managing DebateVerdict persistence."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        
    async def save_verdict(self, ticker: str, verdict: Verdict, referee: Optional[RefereeDecision] = None, rounds: Optional[List[DebateRound]] = None, referee_history: Optional[List[RefereeDecision]] = None) -> DebateVerdict:
        """
        Saves a new verdict, soft-expiring all previous active verdicts for this ticker.
        """
        # 1. Soft-delete old active verdicts
        try:
            stmt = update(DebateVerdict).where(
                DebateVerdict.ticker == ticker,
                DebateVerdict.is_active == True
            ).values(is_active=False)
            
            await self.session.execute(stmt)
            
            # 2. Insert new verdict
            db_verdict = DebateVerdict(
                ticker=ticker,
                decision=verdict.decision,
                confidence_score=verdict.confidence_score,
                bull_score=verdict.bull_score,
                bear_score=verdict.bear_score,
                short_term=verdict.short_term.model_dump(),
                medium_term=verdict.medium_term.model_dump(),
                long_term=verdict.long_term.model_dump(),
                context_layer_assessment=verdict.context_layer_assessment.model_dump() if verdict.context_layer_assessment else None,
                judge_synthesis=verdict.judge_synthesis,
                referee_action=referee.action if referee else None,
                is_referee_valid=referee.is_valid if referee else None,
                referee_synthesis=referee.referee_synthesis if referee else None,
                debate_rounds=[r.model_dump() for r in rounds] if rounds else None,
                referee_history=[rh.model_dump() for rh in referee_history] if referee_history else None,
                is_active=True
            )
            
            self.session.add(db_verdict)
            await self.session.commit()
            
            logger.info("verdict_saved_to_db", ticker=ticker)
            return db_verdict
            
        except Exception as e:
            await self.session.rollback()
            logger.error("verdict_save_failed", error=str(e), ticker=ticker)
            raise
