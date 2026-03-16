import logging
from langgraph.graph import StateGraph, START, END

from src.agents.portfolio.state import PortfolioState
from src.agents.portfolio.nodes.portfolio_manager import portfolio_manager_node
from src.agents.portfolio.nodes.risk_manager import risk_manager_node

logger = logging.getLogger(__name__)

# 1. Initialize Graph
workflow = StateGraph(PortfolioState)

# 2. Add Nodes
workflow.add_node("portfolio_manager", portfolio_manager_node)
workflow.add_node("risk_manager", risk_manager_node)

# 3. Define Edges (Sequential Logic)
workflow.add_edge(START, "portfolio_manager")
workflow.add_edge("portfolio_manager", "risk_manager")
workflow.add_edge("risk_manager", END)

# 4. Compile the graph
portfolio_graph = workflow.compile()
