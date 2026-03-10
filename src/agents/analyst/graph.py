import logging
from langgraph.graph import StateGraph, START, END

from src.agents.analyst.state import AnalystState
from src.agents.analyst.nodes.data_aggregator import aggregate_data_node
from src.agents.analyst.nodes.bull_agent import bull_agent_node
from src.agents.analyst.nodes.bear_agent import bear_agent_node
from src.agents.analyst.nodes.judge_agent import judge_agent_node
from src.agents.analyst.nodes.referee_agent import referee_agent_node

logger = logging.getLogger(__name__)

def join_node(state: AnalystState) -> dict:
    """Dummy node to join the parallel edges and increment round."""
    # Since both bull and bear ran, we finished a round.
    # We increment here so it only happens once per round!
    return {"current_round": state.current_round + 1}

def router(state: AnalystState):
    """
    Decides where to go after both Bull and Bear have spoken.
    Implements max_rounds check and early stopping placeholder.
    """
    if state.current_round >= state.max_rounds:
        return "judge"
    
    # Early stopping logic: if they agree on major points (future implementation)
    # For now, just follow max_rounds
    return ["bull", "bear"]

def referee_router(state: AnalystState):
    """
    Decides if the Referee verification layer should run based on the Judge's Verdict.
    """
    if not state.verdict:
        return END
        
    # Always run referee if this is a retried verdict!
    if getattr(state, "judge_attempts", 1) > 1:
        logger.info(f"Triggering Referee check for retried verdict (Attempt {state.judge_attempts}).")
        return "referee"
        
    confidence = state.verdict.confidence_score
    
    # Run referee if confidence is low.
    if confidence < 75:
        logger.info(f"Triggering Referee check. Confidence: {confidence}")
        return "referee"
    
    logger.info(f"Skipping Referee check. Confidence: {confidence}")
    return END

def post_referee_router(state: AnalystState):
    """
    Decides whether to loop back to the Judge if the Referee invalidated the verdict, 
    up to max_judge_attempts.
    """
    if not state.referee_decision or state.referee_decision.is_valid:
        return END
        
    if state.judge_attempts <= state.max_judge_attempts:
        logger.warning(f"Referee invalidated verdict. Looping back to Judge. Attempt {state.judge_attempts}/{state.max_judge_attempts}")
        return "judge"
        
    logger.error("Max Judge attempts reached after Referee invalidations. Ending graph.")
    return END

# 1. Initialize Graph
workflow = StateGraph(AnalystState)

# 2. Add Nodes
workflow.add_node("data_aggregator", aggregate_data_node)
workflow.add_node("bull", bull_agent_node)
workflow.add_node("bear", bear_agent_node)
workflow.add_node("join", join_node)
workflow.add_node("judge", judge_agent_node)
workflow.add_node("referee", referee_agent_node)

# 3. Define Edges (Flow)
workflow.add_edge(START, "data_aggregator")

# Fan-out to both agents
workflow.add_edge("data_aggregator", "bull")
workflow.add_edge("data_aggregator", "bear")

# Fan-in to the join node
workflow.add_edge("bull", "join")
workflow.add_edge("bear", "join")

# Conditionally route from join
workflow.add_conditional_edges("join", router)

# After Judge, conditionally run referee
workflow.add_conditional_edges("judge", referee_router)

# After Referee, decide if we loop back or end.
workflow.add_conditional_edges("referee", post_referee_router)

# 4. Compile
debate_graph = workflow.compile()
