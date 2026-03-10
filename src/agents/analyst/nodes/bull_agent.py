import logging
from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field

from src.agents.analyst.state import AnalystState, DebateRound, Argument, Rebuttal
from src.services.llm import LLMService

logger = logging.getLogger(__name__)

class BullOpeningOutput(BaseModel):
    arguments: list[Argument] = Field(description="Exactly 5 compelling reasons to BUY the stock.")

class BullRebuttalOutput(BaseModel):
    rebuttals: list[Rebuttal] = Field(description="Rebuttals attacking the opponent's previous claims.")

async def bull_agent_node(state: AnalystState) -> Dict[str, Any]:
    """The Bull Agent: Generates opening arguments or rebuttals."""
    logger.info(f"Bull Agent running for {state.ticker} (Round {state.current_round})")
    
    llm = LLMService()
    
    if state.current_round == 1:
        # OPENING ROUND
        system_prompt = llm.load_prompt("bull_system.txt")
        user_prompt = f"Analyze the following context for {state.ticker} and provide 5 reasons to BUY:\n\n{state.context}"
        response = await llm.generate_structured(system_prompt, user_prompt, BullOpeningOutput, role="deep", agent_name="bull")
        
        return {"rounds": [DebateRound(round_number=1, bull_arguments=response.arguments)]}
        
    else:
        # REBUTTAL ROUND
        # Find what the Bear said in the previous round
        bear_attacks = []
        for r in state.rounds:
            if r.round_number == state.current_round - 1:
                bear_attacks.extend(r.bear_arguments)
                bear_attacks.extend(r.bear_rebuttals)
            
        bear_text_parts = []
        for a in bear_attacks:
            if hasattr(a, 'claim') and a.claim:
                bear_text_parts.append(f"CLAIM: {a.claim}\nEVIDENCE: {a.evidence}")
            elif hasattr(a, 'target_claim') and a.target_claim:
                bear_text_parts.append(f"ATTACK: {a.target_claim}\nCOUNTER: {a.counter_evidence}")
        
        bear_text = "\n\n".join(bear_text_parts) if bear_text_parts else "No specific arguments found to rebut."
            
        system_prompt = llm.load_prompt("bull_rebuttal.txt")
        user_prompt = f"CONTEXT:\n{state.context}\n\nBEAR'S ARGUMENTS FROM PREVIOUS ROUND:\n{bear_text}\n\nDestroy these arguments using context data."
        response = await llm.generate_structured(system_prompt, user_prompt, BullRebuttalOutput, role="deep", agent_name="bull")
        
        return {"rounds": [DebateRound(round_number=state.current_round, bull_rebuttals=response.rebuttals)]}
