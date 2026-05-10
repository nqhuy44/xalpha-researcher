import logging
from typing import Any, Dict

from pydantic import BaseModel, Field

from src.agents.analyst.state import AnalystState, Argument, DebateRound, Rebuttal
from src.agents.analyst.utils.debate_formatting import format_opponent_attacks
from src.services.llm import LLMService

logger = logging.getLogger(__name__)


class BullOpeningOutput(BaseModel):
    arguments: list[Argument] = Field(description="Exactly 5 compelling reasons to BUY the stock.")


class BullRebuttalOutput(BaseModel):
    rebuttals: list[Rebuttal] = Field(description="Rebuttals attacking the Bear's previous claims.")


async def bull_agent_node(state: AnalystState) -> Dict[str, Any]:
    """Bull persona: round 1 opens, later rounds rebut Bear's prior output."""
    logger.info(f"Bull Agent running for {state.ticker} (Round {state.current_round})")
    llm = LLMService()

    if state.current_round == 1:
        system_prompt = llm.load_prompt("bull_system.txt")
        user_prompt = (
            f"Analyze the following context for {state.ticker} and provide 5 reasons to BUY:\n\n"
            f"{state.context}"
        )
        response = await llm.generate_structured(
            system_prompt, user_prompt, BullOpeningOutput, role="deep", agent_name="bull",
        )
        return {"rounds": [DebateRound(round_number=1, bull_arguments=response.arguments)]}

    # Rebuttal round — pull Bear's output from the previous round.
    prev_round = next(
        (r for r in state.rounds if r.round_number == state.current_round - 1), None,
    )
    bear_args = prev_round.bear_arguments if prev_round else []
    bear_rebs = prev_round.bear_rebuttals if prev_round else []
    if not bear_args and not bear_rebs:
        logger.warning(
            f"Bull found no Bear output in round {state.current_round - 1} to rebut",
        )

    opponent_text = format_opponent_attacks(bear_args, bear_rebs)
    system_prompt = llm.load_prompt("bull_rebuttal.txt")
    user_prompt = (
        f"CONTEXT:\n{state.context}\n\n"
        f"BEAR'S ARGUMENTS FROM PREVIOUS ROUND:\n{opponent_text}\n\n"
        f"Address each argument above using context data."
    )
    response = await llm.generate_structured(
        system_prompt, user_prompt, BullRebuttalOutput, role="deep", agent_name="bull",
    )
    return {
        "rounds": [
            DebateRound(round_number=state.current_round, bull_rebuttals=response.rebuttals),
        ],
    }
