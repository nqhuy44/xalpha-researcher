import pandas as pd
import numpy as np

def compute_rsi(close_series: pd.Series, period: int = 14) -> pd.Series:
    """
    Computes the Relative Strength Index (RSI).
    """
    delta = close_series.diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    
    # Use exponential moving average for smoothing
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    # Handle edge case where avg_loss is 0
    rsi[avg_loss == 0] = 100
    
    return rsi

def compute_macd(close_series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """
    Computes MACD, MACD Signal, and MACD Histogram.
    Returns a DataFrame with columns: ['MACD', 'MACD_Signal', 'MACD_Hist']
    """
    ema_fast = close_series.ewm(span=fast, adjust=False).mean()
    ema_slow = close_series.ewm(span=slow, adjust=False).mean()
    
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    macd_hist = macd_line - signal_line
    
    return pd.DataFrame({
        'MACD': macd_line,
        'MACD_Signal': signal_line,
        'MACD_Hist': macd_hist
    })
