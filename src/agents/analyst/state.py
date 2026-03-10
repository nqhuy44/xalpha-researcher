from datetime import datetime
from typing import Annotated, Dict, Any, List, Optional
from pydantic import BaseModel, Field
import operator

class Argument(BaseModel):
    """A single argument made by an agent in the debate."""
    claim: str = Field(description="A concise summary of the point being made.")
    evidence: str = Field(description="Specific data points or facts backing the claim.")
    strength: int = Field(description="Self-assessed strength of this argument from 1-10.")

class Rebuttal(BaseModel):
    """A rebuttal to a specific opponent's claim."""
    target_claim: str = Field(description="The opponent's original claim being attacked.")
    counter_evidence: str = Field(description="Data and logic used to destroy the opponent's claim.")

class DebateRound(BaseModel):
    """A single round of debate."""
    round_number: int
    bull_arguments: List[Argument] = []
    bear_arguments: List[Argument] = []
    bull_rebuttals: List[Rebuttal] = []
    bear_rebuttals: List[Rebuttal] = []

class HorizonPrediction(BaseModel):
    """Prediction for a specific time horizon."""
    horizon: str = Field(description="Timeframe: 1 month, 6 months, or 1 year.")
    action: str = Field(description="Suggested action: Mua, Bán, Giữ, Theo dõi sát, Bỏ qua, etc.")
    outlook: str = Field(description="Bullish, Bearish, or Neutral.")
    horizon_confidence: int = Field(description="0 to 100 percentage expressing confidence in this specific timeframe.")
    entry_price: float = Field(description="Suggested entry level based on technicals.")
    target_price: float = Field(description="Expected price target.")
    stop_loss: float = Field(description="Strict invalidation level to cut losses.")
    rationale: str = Field(description="Why this specific target and stop loss make sense.")
    risk_reward_ratio: float

class Verdict(BaseModel):
    """The final structured output from the Judge Agent."""
    decision: str = Field(description="MUST BE exactly one of: 'Tiềm năng', 'Rủi ro', or 'An toàn'.")
    confidence_score: int = Field(description="0 to 100 percentage of overall certainty.")
    bull_score: int = Field(description="Total points awarded to the Bull")
    bear_score: int = Field(description="Total points awarded to the Bear")
    
    bull_surviving_points: List[str]
    bear_surviving_points: List[str]
    destroyed_arguments: List[str] = Field(description="Key claims that were successfully ripped apart in rebuttals.")
    
    judge_synthesis: str = Field(description="A 2-3 sentence overarching conclusion.")
    
    short_term: HorizonPrediction
    medium_term: HorizonPrediction
    long_term: HorizonPrediction

class RefereeDecision(BaseModel):
    """The safety verification layer output after Judge's verdict."""
    is_valid: bool = Field(description="False if severe reasoning errors, hallucinations, or heavy bias are found in the Judge's verdict")
    hallucinations_detected: List[str] = Field(description="Specific facts the judge used that do not exist in the provided evidence context or debate round arguments")
    logic_flaws: List[str] = Field(description="Specific logical inconsistencies in the judge's reasoning")
    bias_assessment: str = Field(description="Assessment of whether the judge favored one side unfairly despite equal evidence")
    action: str = Field(description="Must be exactly one of: 'CONFIRM', 'OVERRIDE', or 'INCONCLUSIVE'")
    referee_synthesis: str = Field(description="Brief explanation of why the referee decided to confirm, override, or label it inconclusive")

class AnalystState(BaseModel):
    """
    The main LangGraph State object holding the entire context.
    'rounds' uses operator.add so we can append new rounds without overwriting.
    """
    ticker: str
    company_name: str
    context: str = Field(default="", description="The extremely detailed text block containing EOD, financials, and news.")
    
    # State accumulated across nodes
    rounds: Annotated[List[DebateRound], operator.add] = Field(default_factory=list)
    current_round: int = 1
    max_rounds: int = 3
    confidence_threshold: float = 0.75
    judge_attempts: int = 1
    max_judge_attempts: int = 2
    
    verdict: Optional[Verdict] = None
    referee_decision: Optional[RefereeDecision] = None
    referee_history: Annotated[List[RefereeDecision], operator.add] = Field(default_factory=list)
