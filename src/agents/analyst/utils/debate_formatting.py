"""Shared formatting helpers for the debate.

Single source of truth for how arguments and rebuttals are stringified into
LLM prompts (Bull/Bear rebuttal context) and into the transcript shown to
Judge and Referee.
"""

from typing import List

from src.agents.analyst.state import Argument, DebateRound, Rebuttal


def format_argument(arg: Argument) -> str:
    """Single Argument → multi-line string for transcripts and rebuttal prompts."""
    return (
        f"- [{arg.type} | Strength {arg.strength}/10] {arg.claim}\n"
        f"  Evidence: {arg.evidence}\n"
        f"  Acknowledged counter: {arg.acknowledged_counter}"
    )


def format_rebuttal(reb: Rebuttal) -> str:
    """Single Rebuttal → multi-line string for transcripts and rebuttal prompts."""
    return (
        f"- [Flaw: {reb.flaw_type} | Strength {reb.rebuttal_strength}/10] target: {reb.target_claim}\n"
        f"  Counter: {reb.counter_evidence}"
    )


def format_opponent_attacks(arguments: List[Argument], rebuttals: List[Rebuttal]) -> str:
    """Format the opponent's prior-round output as the user-prompt input for a rebuttal node.

    Empty inputs return a sentinel so the LLM doesn't silently rebut nothing.
    """
    parts: List[str] = []
    for a in arguments:
        parts.append(format_argument(a))
    for r in rebuttals:
        parts.append(format_rebuttal(r))
    return "\n\n".join(parts) if parts else "No prior arguments to address."


def format_debate_transcript(rounds: List[DebateRound]) -> str:
    """Format the full debate history for Judge and Referee prompts.

    Rounds are sorted by `round_number`. Round 1 shows openings; later rounds
    show rebuttals only.
    """
    lines: List[str] = []
    for r in sorted(rounds, key=lambda x: x.round_number):
        lines.append(f"\n--- ROUND {r.round_number} ---")
        if r.round_number == 1:
            lines.append("BULL OPENING ARGUMENTS:")
            lines.extend(format_argument(a) for a in r.bull_arguments)
            lines.append("\nBEAR OPENING ARGUMENTS:")
            lines.extend(format_argument(a) for a in r.bear_arguments)
        else:
            lines.append("BULL REBUTTALS:")
            lines.extend(format_rebuttal(rb) for rb in r.bull_rebuttals)
            lines.append("\nBEAR REBUTTALS:")
            lines.extend(format_rebuttal(rb) for rb in r.bear_rebuttals)
    return "\n".join(lines)
