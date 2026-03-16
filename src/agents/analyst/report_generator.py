import os
import difflib
from datetime import datetime
from typing import List, Optional
from src.agents.analyst.state import Verdict, DebateRound, RefereeDecision
from src.config.settings import settings

def generate_html_report(ticker: str, verdict: Verdict, rounds: List[DebateRound], referee_history: List[RefereeDecision] = None) -> str:
    """
    Generates a modern, responsive HTML report for the debate.
    """
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # CSS Styles for modern, beautiful layout
    styles = """
    :root {
        --bg-color: #0f172a;
        --card-bg: #1e293b;
        --text-main: #f8fafc;
        --text-muted: #94a3b8;
        --bull-color: #10b981;
        --bear-color: #ef4444;
        --accent-color: #3b82f6;
    }
    body {
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
        background-color: var(--bg-color);
        color: var(--text-main);
        margin: 0;
        padding: 2rem;
        line-height: 1.6;
    }
    .container {
        max-width: 1200px;
        margin: 0 auto;
    }
    .header {
        text-align: center;
        margin-bottom: 3rem;
        padding-bottom: 2rem;
        border-bottom: 1px solid #334155;
    }
    .header h1 {
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
        letter-spacing: -0.025em;
    }
    .header p {
        color: var(--text-muted);
        font-size: 1.1rem;
    }
    .verdict-banner {
        background: linear-gradient(135deg, rgba(30,41,59,1) 0%, rgba(15,23,42,1) 100%);
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 2rem;
        margin-bottom: 3rem;
        text-align: center;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    .decision {
        font-size: 3rem;
        font-weight: 800;
        margin: 1rem 0;
        color: var(--text-main);
    }
    
    .score-board {
        display: flex;
        justify-content: center;
        gap: 3rem;
        margin-top: 1.5rem;
        font-size: 1.5rem;
        font-weight: 600;
    }
    .score-board .bull { color: var(--bull-color); }
    .score-board .bear { color: var(--bear-color); }
    
    .synthesis {
        font-size: 1.1rem;
        color: #cbd5e1;
        max-width: 800px;
        margin: 1.5rem auto 0;
        font-style: italic;
    }
    
    .debate-section {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 2rem;
        margin-bottom: 3rem;
    }
    @media (max-width: 768px) {
        .debate-section { grid-template-columns: 1fr; }
    }
    .column {
        background-color: var(--card-bg);
        border-radius: 12px;
        padding: 1.5rem;
        border-top: 4px solid;
    }
    .column.bull { border-color: var(--bull-color); }
    .column.bear { border-color: var(--bear-color); }
    
    .column h2 {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-top: 0;
        font-size: 1.5rem;
        border-bottom: 1px solid #334155;
        padding-bottom: 1rem;
    }
    .column.bull h2 { color: var(--bull-color); }
    .column.bear h2 { color: var(--bear-color); }
    
    .argument-group {
        margin-bottom: 2.5rem;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }
    .argument {
        padding: 1.25rem;
        background-color: rgba(0,0,0,0.3);
        border-radius: 12px;
        position: relative;
        border: 1px solid rgba(255,255,255,0.05);
    }
    .arg-header {
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 0.75rem;
    }
    .strength {
        font-size: 0.75rem;
        padding: 2px 8px;
        border-radius: 4px;
        background: #334155;
        color: #94a3b8;
    }
    .argument h3 {
        margin: 0;
        font-size: 1.15rem;
        color: #f8fafc;
        flex: 1;
        padding-right: 1rem;
    }
    .argument p {
        margin: 0;
        color: #cbd5e1;
        font-size: 0.95rem;
    }
    .rebuttal-reply {
        margin-left: 2rem;
        padding: 1rem;
        background-color: rgba(59, 130, 246, 0.1);
        border-left: 3px solid var(--accent-color);
        border-radius: 0 8px 8px 0;
        position: relative;
    }
    .rebuttal-reply::before {
        content: "";
        position: absolute;
        left: -1rem;
        top: 0;
        bottom: 50%;
        width: 1rem;
        border-left: 2px solid #334155;
        border-bottom: 2px solid #334155;
        border-radius: 0 0 0 8px;
    }
    .reply-header {
        font-size: 0.8rem;
        font-weight: 700;
        color: var(--accent-color);
        text-transform: uppercase;
        margin-bottom: 0.25rem;
    }
    .rebuttal-reply p {
        margin: 0;
        font-size: 0.9rem;
        color: #94a3b8;
    }
    
    .horizons {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 1.5rem;
    }
    .horizon-card {
        background-color: var(--card-bg);
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #334155;
    }
    .horizon-card h3 {
        margin-top: 0;
        color: var(--accent-color);
        border-bottom: 1px solid #334155;
        padding-bottom: 0.5rem;
    }
    .horizon-data {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.5rem;
        margin-bottom: 1rem;
    }
    .horizon-data div {
        background: rgba(0,0,0,0.2);
        padding: 0.5rem;
        border-radius: 6px;
        text-align: center;
    }
    .horizon-data span {
        display: block;
        font-size: 0.8rem;
        color: var(--text-muted);
    }
    .horizon-data strong {
        font-size: 1.1rem;
    }
    .horizon-confidence {
        text-align: center;
        font-size: 0.9rem;
        color: #cbd5e1;
        margin-bottom: 1rem;
        font-weight: 600;
        background: rgba(59, 130, 246, 0.1);
        padding: 0.25rem;
        border-radius: 6px;
    }
    """

    def get_color_for_text(text: str) -> str:
        t = text.lower()
        if "tiềm năng" in t:
            return "var(--bull-color)"
        elif "khả quan" in t:
            return "#a3e635" # Lime green
        elif "trung lập" in t:
            return "#94a3b8" # Slate
        elif "rủi ro" in t:
            return "var(--bear-color)"
        elif "an toàn" in t:
            return "#38bdf8" # Sky blue
        
        # Fallbacks for actions
        if "mua" in t: return "var(--bull-color)"
        if "bán" in t: return "var(--bear-color)"
        if "giữ" in t or "theo dõi" in t: return "#f59e0b"
        
        return "var(--text-main)"

    def clean_text(text: str) -> str:
        if not text: return ""
        # The LLM sometimes includes evidence or newlines in the target_claim field
        cleaned = text.strip().split('\n')[0].strip()
        
        # Strip common prefixes used in prompts
        prefixes = ["CLAIM:", "ATTACK:", "EVIDENCE:", "COUNTER:", "- Claim:", "- Attack on Bull:", "- Attack on Bear:"]
        for p in prefixes:
            if cleaned.upper().startswith(p.upper()):
                cleaned = cleaned[len(p):].strip()
        return cleaned

    def find_best_thread(text, thread_map):
        if not text: return None
        cleaned_target = clean_text(text).lower()
        
        # Try exact match on cleaned text first
        for key in thread_map.keys():
            if cleaned_target == clean_text(key).lower():
                return thread_map[key]
        
        # Try substring match
        for key in thread_map.keys():
            cleaned_key = clean_text(key).lower()
            if cleaned_target in cleaned_key or cleaned_key in cleaned_target:
                return thread_map[key]
        
        # Try fuzzy match on cleaned text
        best_ratio = 0
        best_thread = None
        for key in thread_map.keys():
            ratio = difflib.SequenceMatcher(None, cleaned_target, clean_text(key).lower()).ratio()
            if ratio > 0.5 and ratio > best_ratio:
                best_ratio = ratio
                best_thread = thread_map[key]
        return best_thread

    # 1. Initialize thread structures for top-level arguments
    bull_threads = {a.claim: {"arg": a, "replies": []} for a in rounds[0].bull_arguments}
    bear_threads = {a.claim: {"arg": a, "replies": []} for a in rounds[0].bear_arguments}
    
    # 2. Build a mapping to track which thread any piece of text belongs to
    # We include both Bull and Bear threads so rebuttals can find their targets anywhere
    text_to_thread = {}
    for claim, thread in bull_threads.items():
        text_to_thread[claim] = thread
    for claim, thread in bear_threads.items():
        text_to_thread[claim] = thread
        
    # 3. Process rounds 2 onwards to collect all replies
    for r_idx, r in enumerate(rounds[1:], start=2):
        # Bear's rebuttals (attacking Bull's points)
        for reb in r.bear_rebuttals:
            thread = find_best_thread(reb.target_claim, text_to_thread)
            if thread:
                thread["replies"].append({"from": "🐻 Bear", "content": reb.counter_evidence, "round": r_idx})
                # Register the counter_evidence so Bull can rebut it in next round
                text_to_thread[reb.counter_evidence] = thread
            else:
                # If no thread found, maybe it's a general attack, but we usually want it linked
                pass
                
        # Bull's rebuttals (attacking Bear's points)
        for reb in r.bull_rebuttals:
            thread = find_best_thread(reb.target_claim, text_to_thread)
            if thread:
                thread["replies"].append({"from": "🐂 Bull", "content": reb.counter_evidence, "round": r_idx})
                # Register the counter_evidence so Bear can rebut it
                text_to_thread[reb.counter_evidence] = thread


    def render_threads(threads, side_class):
        html = ""
        for claim, data in threads.items():
            arg = data["arg"]
            html += f'''
            <div class="argument-group">
                <div class="argument {side_class}">
                    <div class="arg-header">
                        <span class="strength">Strength: {arg.strength}/10</span>
                        <h3>{arg.claim}</h3>
                    </div>
                    <p>{arg.evidence}</p>
                </div>
            '''
            for reply in data["replies"]:
                label = "Counter" if reply["round"] == 2 else "Rebuttal"
                html += f'''
                <div class="rebuttal-reply">
                    <div class="reply-header">{reply["from"]} {label} (R{reply["round"]}):</div>
                    <p>{reply["content"]}</p>
                </div>
                '''
            html += '</div>'
        return html

    rounds_html = f'''
    <div class="debate-section">
        <div class="column bull">
            <h2>🐂 Phe Bò (Bull Arguments)</h2>
            {render_threads(bull_threads, "bull")}
        </div>
        <div class="column bear">
            <h2>🐻 Phe Gấu (Bear Arguments)</h2>
            {render_threads(bear_threads, "bear")}
        </div>
    </div>
    '''
        
    # Render Horizons
    def render_horizon(title, h):
        def fmt(val):
            return f"{val:,.0f}" if val else "N/A"
        
        return f'''
        <div class="horizon-card">
            <h3>{title} <span style="font-size:0.8em; color:var(--text-muted); font-weight:normal;">({h.outlook})</span></h3>
            <div class="horizon-confidence">Hành động: <strong style="color:{get_color_for_text(h.action)}; font-size:1.1em;">{h.action.upper()}</strong> | Tin cậy: {h.horizon_confidence}%</div>
            <div class="horizon-data">
                <div><span>Entry</span><strong>{fmt(h.entry_price)}</strong></div>
                <div><span>Target</span><strong style="color:var(--bull-color)">{fmt(h.target_price)}</strong></div>
                <div><span>Stop Loss</span><strong style="color:var(--bear-color)">{fmt(h.stop_loss)}</strong></div>
                <div><span>R:R</span><strong>{h.risk_reward_ratio if h.risk_reward_ratio else "N/A"}</strong></div>
            </div>
            <p style="font-size:0.9rem; color:var(--text-muted);">{h.rationale}</p>
        </div>
        '''

    html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>XAlpha Debate Report: {ticker}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
    <style>{styles}</style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>XAlpha Debate Report: {ticker}</h1>
            <p>Generated on {date_str} | AI Multi-Agent Consensus</p>
        </div>

        <div class="verdict-banner">
            <div style="color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.1em; font-size: 0.9rem;">Đánh Giá Định Tính (Qualitative)</div>
            <div class="decision" style="color: {get_color_for_text(verdict.decision)};">{verdict.decision}</div>
            <div style="color: #cbd5e1;">Overall Confidence: {verdict.confidence_score}%</div>
            
            <div class="score-board">
                <div class="bull">🐂 Bull Score: {verdict.bull_score}</div>
                <div class="bear">🐻 Bear Score: {verdict.bear_score}</div>
            </div>
            
            <div class="synthesis">"{verdict.judge_synthesis}"</div>
        </div>
"""
    if referee_history:
        for i, ref in reversed(list(enumerate(referee_history))):
            ref_action_label = ref.action
            if ref.action == "VOID":
                ref_action_label = "VOID (Vô hiệu)"
                ref_action_color = "var(--bear-color)"
            else:
                ref_action_color = "var(--bull-color)" if ref.action == "CONFIRM" else "var(--bear-color)" if ref.action == "OVERRIDE" else "#f59e0b"
            
            val_status = "✅ Valid" if ref.is_valid else "❌ Invalid"
            
            hallucinations_html = ""
            if ref.hallucinations_detected:
                hallucinations_html = f'<div style="margin-top:0.5rem;"><strong style="color:var(--bear-color);">⚠️ Hallucinations:</strong><ul>'
                for h in ref.hallucinations_detected:
                    hallucinations_html += f"<li>{h}</li>"
                hallucinations_html += "</ul></div>"
                
            flaws_html = ""
            if ref.logic_flaws:
                flaws_html = f'<div style="margin-top:0.5rem;"><strong style="color:var(--bear-color);">⚠️ Logic Flaws:</strong><ul>'
                for f in ref.logic_flaws:
                    flaws_html += f"<li>{f}</li>"
                flaws_html += "</ul></div>"
 
            html_content += f"""
            <div style="background-color: var(--card-bg); border-left: 4px solid {ref_action_color}; padding: 1.5rem; border-radius: 8px; margin-bottom: 2rem;">
                <h3 style="margin-top:0; border-bottom: 1px solid #334155; padding-bottom: 0.5rem;">🛡️ Referee Verification (Round {i+1})</h3>
                <div style="display: flex; gap: 2rem; margin-bottom: 1rem;">
                    <div><span style="color: var(--text-muted);">Action:</span> <strong style="color:{ref_action_color}">{ref_action_label}</strong></div>
                    <div><span style="color: var(--text-muted);">Status:</span> <strong>{val_status}</strong></div>
                    <div><span style="color: var(--text-muted);">Bias Check:</span> <strong>{ref.bias_assessment}</strong></div>
                </div>
                <p style="font-style: italic; color: #cbd5e1;">"{ref.referee_synthesis}"</p>
                {hallucinations_html}
                {flaws_html}
            </div>
            """

    html_content += f"""
        <h2 style="border-bottom: 2px solid #334155; padding-bottom: 0.5rem; margin-bottom: 2rem;">Chiến lược Giao dịch (Trading Horizons)</h2>
        <div class="horizons">
            {render_horizon('Ngắn hạn (1 Tháng)', verdict.short_term)}
            {render_horizon('Trung hạn (6 Tháng)', verdict.medium_term)}
            {render_horizon('Dài hạn (1 Năm)', verdict.long_term)}
        </div>

        <h2 style="border-bottom: 2px solid #334155; padding-bottom: 0.5rem; margin-top: 4rem; margin-bottom: 2rem;">Biên bản Tranh biện Chi tiết</h2>
        {rounds_html}
        
    </div>
</body>
</html>
"""
    return html_content

def save_report(ticker: str, html_content: str) -> str:
    """Saves the HTML report to the disk and returns the file path."""
    reports_dir = os.path.join(os.getcwd(), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{ticker}_debate_report_{timestamp}.html"
    filepath = os.path.join(reports_dir, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    return filepath
