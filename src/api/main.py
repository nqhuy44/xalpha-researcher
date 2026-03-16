import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, update, text

from src.db.session import get_db_session, async_session_factory
from src.db.models.portfolio import PortfolioPosition, PortfolioSuggestion
from src.db.models.finance import StockEOD
from src.config.settings import settings
from src.api.auth import get_current_user, create_access_token, authenticate_admin
import datetime
import uuid
import os
import glob
import markdown
import structlog


from src.db.models.analyst import DebateVerdict

logger = structlog.get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("portfolio_api_started")
    analysis_manager.start(lifespan_tasks)
    yield
    analysis_manager.stop()
    logger.info("portfolio_api_shutdown")

app = FastAPI(title="Portfolio API", lifespan=lifespan)

# Add CORS middleware to handle preflight requests from the dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the exact frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the ui and reports directory
ui_dir = os.path.join(os.path.dirname(__file__), "..", "..", "ui")
reports_dir = os.path.join(os.path.dirname(__file__), "..", "..", "reports")
os.makedirs(reports_dir, exist_ok=True)
# app.mount("/reports", StaticFiles(directory=reports_dir), name="reports")

@app.get("/reports/{filename}")
async def serve_report(filename: str, user: str = Depends(get_current_user)):
    """Serves a report file, protected by JWT."""
    file_path = os.path.join(reports_dir, filename)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(file_path)

class PortfolioUpdateCommand(BaseModel):
    action: str = "BUY" # BUY, SELL, DEPOSIT, WITHDRAW, INIT
    symbol: str
    shares: int
    avg_price: float
    notes: str | None = None

@app.get("/")
async def serve_ui():
    return FileResponse(os.path.join(ui_dir, "portfolio.html"))

class LoginRequest(BaseModel):
    password: str

@app.post("/api/v1/login")
async def login(payload: LoginRequest):
    if authenticate_admin(payload.password):
        token = create_access_token(data={"sub": "admin"})
        return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Invalid password")


@app.get("/api/v1/auth/me")
async def get_me(user: str = Depends(get_current_user)):
    return {"status": "ok", "user": user}

@app.get("/api/v1/analysis/recent")
async def get_recent_analysis(limit: int = 50, db: AsyncSession = Depends(get_db_session), user: str = Depends(get_current_user)):
    stmt = select(PortfolioSuggestion).where(
        PortfolioSuggestion.is_active == True
    ).order_by(desc(PortfolioSuggestion.created_at)).limit(limit)
    
    result = await db.execute(stmt)
    suggestions = result.scalars().all()
    
    data = []
    for sug in suggestions:
        now = datetime.datetime.now(datetime.timezone.utc)
        sug_time = sug.created_at
        if sug_time.tzinfo is None:
            sug_time = sug_time.replace(tzinfo=datetime.timezone.utc)
            
        is_expired = (now - sug_time).days > 7
        
        data.append({
            "id": str(sug.verdict_id or sug.id),
            "symbol": sug.symbol,
            "analyst_decision": sug.analyst_decision,
            "analyst_confidence": sug.analyst_confidence,
            "suggested_action": sug.suggested_action,
            "suggested_shares": sug.suggested_shares,
            "suggested_price": sug.suggested_cost / sug.suggested_shares if sug.suggested_shares > 0 else 0.0,
            "rationale": sug.rationale,
            "report_path": sug.report_path,
            "created_at": sug.created_at.isoformat(),
            "is_expired": is_expired
        })
        
    return {"suggestions": data}

@app.get("/api/v1/analysis/history")
async def get_analysis_history(limit: int = 50, db: AsyncSession = Depends(get_db_session), user: str = Depends(get_current_user)):
    stmt = select(PortfolioSuggestion).order_by(desc(PortfolioSuggestion.created_at)).limit(limit)
    result = await db.execute(stmt)
    suggestions = result.scalars().all()
    
    data = []
    for sug in suggestions:
        data.append({
            "id": str(sug.verdict_id or sug.id),
            "ticker": sug.symbol,
            "suggested_action": sug.suggested_action,
            "created_at": sug.created_at.isoformat(),
            "analyst_decision": sug.analyst_decision,
            "analyst_confidence": sug.analyst_confidence,
            "suggested_shares": sug.suggested_shares,
            "suggested_price": sug.suggested_cost / sug.suggested_shares if sug.suggested_shares > 0 else 0.0,
            "is_active": sug.is_active
        })
    return {"history": data}

# Track active analysis symbols in memory
import asyncio

class AnalysisManager:
    def __init__(self, concurrency=3):
        self.queue = asyncio.Queue()
        self.active_symbols = set()
        self.queued_symbols = []
        self.concurrency = concurrency
        self.workers = []

    async def add_task(self, symbol: str):
        symbol = symbol.upper()
        if symbol in self.active_symbols or symbol in self.queued_symbols:
            return False
        self.queued_symbols.append(symbol)
        await self.queue.put(symbol)
        return True

    async def worker(self):
        while True:
            symbol = await self.queue.get()
            try:
                if symbol in self.queued_symbols:
                    self.queued_symbols.remove(symbol)
                
                self.active_symbols.add(symbol)
                logger.info("Worker starting analysis", symbol=symbol)
                await run_analysis_background(symbol, async_session_factory)
            except Exception as e:
                logger.error("Worker error during analysis", symbol=symbol, error=str(e))
            finally:
                if symbol in self.active_symbols:
                    self.active_symbols.remove(symbol)
                self.queue.task_done()
                logger.info("Worker finished analysis", symbol=symbol)

    def start(self, app_lifespan_tasks):
        for _ in range(self.concurrency):
            task = asyncio.create_task(self.worker())
            self.workers.append(task)
            app_lifespan_tasks.append(task)

    def stop(self):
        for w in self.workers:
            w.cancel()

analysis_manager = AnalysisManager(concurrency=3)
lifespan_tasks = []

@app.get("/api/v1/analysis/stats")
async def get_stats(db: AsyncSession = Depends(get_db_session), current_user: str = Depends(get_current_user)):
    # 1. Active ones in DB (suggestions that are still valid/active)
    active_stmt = select(PortfolioSuggestion).where(PortfolioSuggestion.is_active == True)
    active_result = await db.execute(active_stmt)
    db_active_count = len(active_result.scalars().all())
    
    # 2. Check DB Health
    try:
        await db.execute(text("SELECT 1"))
        db_health = True
    except:
        db_health = False

    health_percent = "98.4%" if db_health else "10.0%"
    
    return {
        "system_health": health_percent,
        "pending_tasks": len(analysis_manager.active_symbols) + len(analysis_manager.queued_symbols),
        "active_symbols": list(analysis_manager.active_symbols),
        "queued_symbols": analysis_manager.queued_symbols,
        "db_active_count": db_active_count
    }

@app.get("/api/v1/analysis/{verdict_id}")
async def get_analysis_detail(verdict_id: uuid.UUID, db: AsyncSession = Depends(get_db_session), current_user: str = Depends(get_current_user)):
    stmt = select(DebateVerdict).where(DebateVerdict.id == verdict_id)
    result = await db.execute(stmt)
    verdict = result.scalar_one_or_none()
    if not verdict:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return verdict

async def run_analysis_background(symbol: str, db_factory):
    """Background task to run the debate engine and portfolio engine."""
    from src.agents.analyst.engine import DebateEngine
    from src.agents.analyst.report_generator import generate_html_report

    symbol = symbol.upper()
    # Note: caller should handle active_symbols management
    
    try:
        # 1. Trigger analysis (Engines handle their own archiving)
        from src.config.settings import settings
        engine = DebateEngine(max_rebuttals=settings.debate.max_rebuttals)
        result = await engine.analyze(symbol)
        
        if not result:
            logger.error("analysis_failed_no_verdict", symbol=symbol)
            return
            
        verdict_obj, referee_history, transcript_str, final_rounds_list = result
        
        # 2. Generate Report
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"{symbol}_{timestamp}.html"
        report_path = os.path.join(reports_dir, report_filename)
        
        html_doc = generate_html_report(symbol, verdict_obj, final_rounds_list, referee_history)
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html_doc)
            
        # 3. Link Report Path to the NEW suggestion created by PortfolioEngine
        async with db_factory() as db:
            stmt = select(PortfolioSuggestion).where(
                PortfolioSuggestion.symbol == symbol,
                PortfolioSuggestion.is_active == True
            ).order_by(desc(PortfolioSuggestion.created_at)).limit(1)
            
            sug_result = await db.execute(stmt)
            sug = sug_result.scalar_one_or_none()
            if sug:
                logger.info("Linking report path to suggestion", symbol=symbol, sug_id=sug.id, verdict_id=sug.verdict_id)
                sug.report_path = f"/reports/{report_filename}"
                await db.commit()
                logger.info("analysis_completed_successfully", symbol=symbol)
            else:
                logger.warning("No active suggestion found to link report path", symbol=symbol)

    except Exception as e:
        logger.error("background_analysis_error", symbol=symbol, error=str(e), exc_info=True)

@app.post("/api/v1/portfolio/{symbol}/analyze")
async def analyze_portfolio_symbol(
    symbol: str, 
    background_tasks: BackgroundTasks,
    user: str = Depends(get_current_user)
):
    """Triggers the Analyst Engine asynchronously."""
    symbol = symbol.upper()
    started = await analysis_manager.add_task(symbol)
    if not started:
        return {"status": "already_queued_or_analyzing", "symbol": symbol}
        
    return {"status": "started", "symbol": symbol}
    
@app.get("/api/v1/portfolio")
async def get_portfolio(db: AsyncSession = Depends(get_db_session), user: str = Depends(get_current_user)):
    stmt = select(PortfolioPosition).order_by(PortfolioPosition.symbol)
    result = await db.execute(stmt)
    positions = result.scalars().all()
    
    portfolio_data = []
    
    for pos in positions:
        avg_price = 0.0
        market_price = 0.0
        shares_to_show = pos.shares
        
        if pos.symbol == "CASH":
            market_price = 1.0 # Cash is 1:1
            avg_price = 1.0
            shares_to_show = pos.cost_basis # Use cost_basis as the "shares" for display (Value)
            market_value = pos.cost_basis
            cost_value = pos.cost_basis
        else:
            shares_to_show = pos.shares
            avg_price = pos.cost_basis / pos.shares if pos.shares > 0 else 0.0
            price_stmt = select(StockEOD.close).where(StockEOD.ticker == pos.symbol).order_by(desc(StockEOD.trade_date)).limit(1)
            price_result = await db.execute(price_stmt)
            latest_price = price_result.scalar_one_or_none()
            if latest_price is not None:
                market_price = latest_price * 1000 if latest_price < 1000 else latest_price
            else:
                market_price = avg_price

        # Calculate PnL
        cost_value = pos.cost_basis
        market_value = pos.shares * market_price
        pnl_percent = 0.0
        if cost_value > 0 and pos.symbol != "CASH":
            pnl_percent = ((market_value - cost_value) / cost_value) * 100
        elif pos.symbol == "CASH":
            cost_value = pos.cost_basis
            market_value = pos.cost_basis
            pnl_percent = 0.0

        # Get latest active suggestion
        suggestion_stmt = select(PortfolioSuggestion).where(
            PortfolioSuggestion.symbol == pos.symbol,
            PortfolioSuggestion.is_active == True
        ).order_by(desc(PortfolioSuggestion.created_at)).limit(1)
        sug_result = await db.execute(suggestion_stmt)
        sug = sug_result.scalar_one_or_none()
        
        suggestion_data = None
        if sug:
            # Check if older than 7 days
            now = datetime.datetime.now(datetime.timezone.utc)
            # handle timezone unaware vs aware depending on DB
            sug_time = sug.created_at
            if sug_time.tzinfo is None:
                sug_time = sug_time.replace(tzinfo=datetime.timezone.utc)
                
            is_expired = (now - sug_time).days > 7
            
            suggestion_data = {
                "id": str(sug.verdict_id or sug.id),
                "analyst_decision": sug.analyst_decision,
                "analyst_confidence": sug.analyst_confidence,
                "suggested_action": sug.suggested_action,
                "suggested_shares": sug.suggested_shares,
                "suggested_price": sug.suggested_cost / sug.suggested_shares if sug.suggested_shares > 0 else 0.0,
                "rationale": sug.rationale,
                "report_path": sug.report_path,
                "created_at": sug.created_at.isoformat(),
                "is_expired": is_expired
            }

        portfolio_data.append({
            "symbol": pos.symbol,
            "shares": shares_to_show,
            "avg_price": avg_price,
            "market_price": market_price,
            "cost_value": cost_value,
            "market_value": market_value,
            "pnl_percent": pnl_percent,
            "notes": pos.notes,
            "suggestion": suggestion_data
        })
        
    # Calculate Weight and totals
    total_nav = sum(item["market_value"] for item in portfolio_data)
    total_cost = sum(item["cost_value"] for item in portfolio_data)
    total_pnl = total_nav - total_cost
    
    for item in portfolio_data:
        if total_nav != 0:
            item["weight_percent"] = (item["market_value"] / total_nav) * 100
        else:
            item["weight_percent"] = 0.0
        
    return {
        "summary": {
            "total_nav": total_nav,
            "total_cost": total_cost,
            "total_pnl": total_pnl,
            "cash_balance": sum(item["market_value"] for item in portfolio_data if item["symbol"] == "CASH"),
            "stock_value": sum(item["market_value"] for item in portfolio_data if item["symbol"] != "CASH")
        },
        "holdings": portfolio_data
    }

@app.post("/api/v1/analysis/bulk")
async def bulk_analyze(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session), 
    user: str = Depends(get_current_user)
):
    stmt = select(PortfolioPosition.symbol).where(PortfolioPosition.symbol != "CASH")
    result = await db.execute(stmt)
    symbols = result.scalars().all()
    
    triggered = []
    already_in = []
    for symbol in symbols:
        symbol = symbol.upper()
        if await analysis_manager.add_task(symbol):
            triggered.append(symbol)
        else:
            already_in.append(symbol)
            
    return {
        "status": "success", 
        "message": f"Queued analysis for {len(triggered)} symbols", 
        "symbols": triggered,
        "already_running_or_queued": already_in
    }

@app.post("/api/v1/portfolio/sync")
async def sync_portfolio_data(db: AsyncSession = Depends(get_db_session), user: str = Depends(get_current_user)):
    """
    Manually triggers an EOD sync for all tickers currently in the portfolio.
    """
    from src.agents.financial.collector import FinancialCollector
    collector = FinancialCollector()
    
    stmt = select(PortfolioPosition.symbol).where(PortfolioPosition.symbol != "CASH")
    result = await db.execute(stmt)
    tickers = result.scalars().all()
    
    if not tickers:
        return {"message": "No tickers in portfolio to sync"}
        
    logger.info(f"Manual sync triggered for: {tickers}")
    
    # We run them sequentially to avoid overwhelming the VNStock rate limit
    results = []
    for ticker in tickers:
        try:
            count = await collector.sync_eod(ticker)
            results.append({"ticker": ticker, "updated_records": count})
            await asyncio.sleep(0.5) # Small buffer
        except Exception as e:
            results.append({"ticker": ticker, "error": str(e)})
    
    success_count = sum(1 for r in results if r.get("updated_records", 0) > 0)
    
    return {
        "message": f"Sync completed for {len(tickers)} tickers",
        "updated_count": success_count,
        "details": results
    }

@app.post("/api/v1/portfolio/update")
async def update_portfolio(payload: PortfolioUpdateCommand, db: AsyncSession = Depends(get_db_session), user: str = Depends(get_current_user)):
    stmt = select(PortfolioPosition).where(PortfolioPosition.symbol == payload.symbol)
    result = await db.execute(stmt)
    pos = result.scalar_one_or_none()
    
    cash_stmt = select(PortfolioPosition).where(PortfolioPosition.symbol == "CASH")
    cash_result = await db.execute(cash_stmt)
    cash_pos = cash_result.scalar_one_or_none()
    
    if payload.action in ["DEPOSIT", "WITHDRAW"]:
        if not cash_pos:
            cash_pos = PortfolioPosition(symbol="CASH", shares=0, cost_basis=0)
            db.add(cash_pos)
            
        if payload.action == "DEPOSIT":
            cash_pos.cost_basis += payload.shares
        elif payload.action == "WITHDRAW":
            cash_pos.cost_basis -= payload.shares
            
    elif payload.action in ["BUY", "SELL", "INIT"]:
        # Handle decimal separators (inputting 95.271 instead of 95271)
        normalized_price = payload.avg_price
        if normalized_price > 0 and normalized_price < 1000:
            normalized_price *= 1000
            
        if payload.action in ["BUY", "SELL"]:
            if not cash_pos:
                cash_pos = PortfolioPosition(symbol="CASH", shares=0, cost_basis=0)
                db.add(cash_pos)
            
            # Centralized accounting logic
            transaction_value = payload.shares * normalized_price
            commission = int(transaction_value * 0.0015)  # 0.15% commission as integer
            
            if payload.action == "BUY":
                total_deduction = int(transaction_value + commission)
                if cash_pos.cost_basis < total_deduction:
                    raise HTTPException(status_code=400, detail="Không đủ tiền mặt để mua")
                cash_pos.cost_basis -= total_deduction
            elif payload.action == "SELL":
                tax = int(transaction_value * 0.001)  # 0.1% personal income tax
                net_addition = int(transaction_value - commission - tax)
                cash_pos.cost_basis += net_addition

        if payload.action == "INIT":
            if not pos:
                pos = PortfolioPosition(
                    symbol=payload.symbol.upper(),
                    shares=payload.shares if payload.symbol.upper() != "CASH" else 0,
                    cost_basis=int(payload.shares * normalized_price) if payload.symbol.upper() != "CASH" else payload.shares,
                    notes=payload.notes
                )
                db.add(pos)
            else:
                pos.shares = payload.shares if payload.symbol.upper() != "CASH" else 0
                pos.cost_basis = int(payload.shares * normalized_price) if payload.symbol.upper() != "CASH" else payload.shares
                if payload.notes:
                    pos.notes = payload.notes
        elif payload.action == "BUY":
            if not pos:
                pos = PortfolioPosition(
                    symbol=payload.symbol.upper(),
                    shares=payload.shares,
                    cost_basis=int(transaction_value),
                    notes=payload.notes
                )
                db.add(pos)
            else:
                pos.cost_basis += int(transaction_value)
                pos.shares += payload.shares
                if payload.notes:
                    pos.notes = payload.notes
                
        elif payload.action == "SELL":
            if not pos or pos.shares < payload.shares:
                raise HTTPException(status_code=400, detail="Không đủ cổ phiếu để bán")
            
            # Reduce cost basis proportionally (FIFO/Avg cost logic)
            cost_of_sold = int((payload.shares / pos.shares) * pos.cost_basis)
            pos.cost_basis -= cost_of_sold
            pos.shares -= payload.shares
            
            if payload.notes:
                pos.notes = payload.notes
            
            if pos.shares <= 0:
                await db.delete(pos)
                
    await db.commit()
    return {"status": "success", "symbol": payload.symbol}

@app.delete("/api/v1/portfolio/{symbol}")
async def delete_portfolio(symbol: str, db: AsyncSession = Depends(get_db_session), user: str = Depends(get_current_user)):
    stmt = select(PortfolioPosition).where(PortfolioPosition.symbol == symbol.upper())
    result = await db.execute(stmt)
    pos = result.scalar_one_or_none()
    
    if not pos:
        raise HTTPException(status_code=404, detail="Symbol not found in portfolio")
        
    await db.delete(pos)
    await db.commit()
    return {"status": "success", "message": f"Deleted {symbol}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True, 
        reload_dirs=["src", "ui", "docs"]
    )
