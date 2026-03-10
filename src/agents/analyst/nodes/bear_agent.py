import logging
from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field

from src.agents.analyst.state import AnalystState, DebateRound, Argument, Rebuttal
from src.services.llm import LLMService

logger = logging.getLogger(__name__)

class BearOpeningOutput(BaseModel):
    arguments: list[Argument] = Field(description="Exactly 5 critical reasons to SELL the stock.")

class BearRebuttalOutput(BaseModel):
    rebuttals: list[Rebuttal] = Field(description="Rebuttals attacking the Bull's previous claims.")

async def bear_agent_node(state: AnalystState) -> Dict[str, Any]:
    """The Bear Agent: Generates opening risks or rebuttals."""
    logger.info(f"Bear Agent running for {state.ticker} (Round {state.current_round})")
    
    llm = LLMService()
    
    if state.current_round == 1:
        # OPENING ROUND
        system_prompt = llm.load_prompt("bear_system.txt")
        user_prompt = f"Analyze the following context for {state.ticker} and provide 5 critical risks/reasons to SELL:\n\n{state.context}"
        response = await llm.generate_structured(system_prompt, user_prompt, BearOpeningOutput, role="deep", agent_name="bear")
        return {"rounds": [DebateRound(round_number=1, bear_arguments=response.arguments)]}
        
    else:
        # REBUTTAL ROUND
        bull_claims = []
        for r in state.rounds:
            if r.round_number == state.current_round - 1:
                bull_claims.extend(r.bull_arguments)
                bull_claims.extend(r.bull_rebuttals)
            
        if not bull_claims:
            logger.warning("Bear couldn't find Bull's arguments to rebut!")
            bull_text = "No prior arguments found."
        bull_text_parts = []
        for a in bull_claims:
            if hasattr(a, 'claim') and a.claim:
                bull_text_parts.append(f"CLAIM: {a.claim}\nEVIDENCE: {a.evidence}")
            elif hasattr(a, 'target_claim') and a.target_claim:
                bull_text_parts.append(f"ATTACK: {a.target_claim}\nCOUNTER: {a.counter_evidence}")
        
        bull_text = "\n\n".join(bull_text_parts) if bull_text_parts else "No specific arguments found to rebut."
            
        system_prompt = llm.load_prompt("bear_rebuttal.txt")
        user_prompt = f"CONTEXT:\n{state.context}\n\nBULL'S ARGUMENTS FROM PREVIOUS ROUND:\n{bull_text}\n\nDestroy these arguments using context data."
        response = await llm.generate_structured(system_prompt, user_prompt, BearRebuttalOutput, role="deep", agent_name="bear")
        return {"rounds": [DebateRound(round_number=state.current_round, bear_rebuttals=response.rebuttals)]}
