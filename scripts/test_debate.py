import asyncio
import structlog
import sys
from src.agents.analyst.engine import DebateEngine
from src.db.session import async_session_factory
from src.agents.analyst.report_generator import generate_html_report, save_report

logger = structlog.get_logger(__name__)

async def test_debate():
    ticker = sys.argv[1].upper() if len(sys.argv) > 1 else "FPT"
    rounds = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 1
    
    print(f"--- Starting Debate Test for {ticker} with {rounds} rebuttals ---")
    async def print_msg(msg: str):
        print(msg)
        
    engine = DebateEngine(max_rebuttals=rounds)
    result = await engine.analyze(ticker, on_message=print_msg)
    
    if result:
        verdict, referee_history, transcript, rounds_list = result
        
        print("\n=== FINAL VERDICT ===")
        print(f"Decision: {verdict.decision} (Confidence: {verdict.confidence_score}%)")
        print(f"Scores -> Bull: {verdict.bull_score} | Bear: {verdict.bear_score}")
        print(f"Synthesis: {verdict.judge_synthesis}")
        
        if referee_history:
            for i, referee in enumerate(referee_history):
                print(f"\n=== REFEREE VERIFICATION (ROUND {i+1}) ===")
                print(f"Action: {referee.action} (Valid: {referee.is_valid})")
                if referee.hallucinations_detected:
                    print(f"Hallucinations: {referee.hallucinations_detected}")
                if referee.logic_flaws:
                    print(f"Logic Flaws: {referee.logic_flaws}")
                print(f"Bias: {referee.bias_assessment}")
                print(f"Reasoning: {referee.referee_synthesis}")
        
        print("\n--- SHORT TERM ---")
        print(f"Outlook: {verdict.short_term.outlook}")
        print(f"Entry: {verdict.short_term.entry_price} | Target: {verdict.short_term.target_price} | Stop: {verdict.short_term.stop_loss}")
        print(f"Rationale: {verdict.short_term.rationale}")
        
        # Save HTML
        html_content = generate_html_report(ticker, verdict, rounds_list, referee_history)
        report_path = save_report(ticker, html_content)
        print(f"\n✅ HTML Report saved successfully to: {report_path}")
        
    else:
        print("Failed to get a verdict.")

if __name__ == "__main__":
    asyncio.run(test_debate())
