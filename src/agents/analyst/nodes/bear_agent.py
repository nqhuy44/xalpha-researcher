import logging
from typing import Any, Dict

from pydantic import BaseModel, Field

from src.agents.analyst.state import AnalystState, Argument, DebateRound, Rebuttal
from src.agents.analyst.utils.debate_formatting import format_opponent_attacks
from src.services.llm import LLMService

logger = logging.getLogger(__name__)


class BearOpeningOutput(BaseModel):
    arguments: list[Argument] = Field(description="Exactly 5 critical reasons to SELL the stock.")


class BearRebuttalOutput(BaseModel):
    rebuttals: list[Rebuttal] = Field(description="Rebuttals attacking the Bull's previous claims.")


async def bear_agent_node(state: AnalystState) -> Dict[str, Any]:
    """Bear persona: round 1 opens, later rounds rebut Bull's prior output."""
    logger.info(f"Bear Agent running for {state.ticker} (Round {state.current_round})")
    llm = LLMService()

    if state.current_round == 1:
        system_prompt = llm.load_prompt("bear_system.txt")
        user_prompt = (
            f"Analyze the following context for {state.ticker} and provide "
            f"5 critical risks/reasons to SELL:\n\n{state.context}"
        )
        response = await llm.generate_structured(
            system_prompt, user_prompt, BearOpeningOutput, role="deep", agent_name="bear",
        )
        return {"rounds": [DebateRound(round_number=1, bear_arguments=response.arguments)]}

    # Rebuttal round — pull Bull's output from the previous round.
    prev_round = next(
        (r for r in state.rounds if r.round_number == state.current_round - 1), None,
    )
    bull_args = prev_round.bull_arguments if prev_round else []
    bull_rebs = prev_round.bull_rebuttals if prev_round else []
    if not bull_args and not bull_rebs:
        logger.warning(
            f"Bear found no Bull output in round {state.current_round - 1} to rebut",
        )

    opponent_text = format_opponent_attacks(bull_args, bull_rebs)
    system_prompt = llm.load_prompt("bear_rebuttal.txt")
    user_prompt = (
        f"CONTEXT:\n{state.context}\n\n"
        f"BULL'S ARGUMENTS FROM PREVIOUS ROUND:\n{opponent_text}\n\n"
        f"Address each argument above using context data."
    )
    response = await llm.generate_structured(
        system_prompt, user_prompt, BearRebuttalOutput, role="deep", agent_name="bear",
    )
    return {
        "rounds": [
            DebateRound(round_number=state.current_round, bear_rebuttals=response.rebuttals),
        ],
    }
