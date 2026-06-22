"""
TradeSense — Pure Mathematical Core for Behavioral Analytics
Deterministic, stateless functions. No database access.
"""
from decimal import Decimal


def calculate_pgr(realized_gains: Decimal, paper_gains: Decimal) -> Decimal:
    """
    Proportion of Gains Realized (PGR).
    Formula: Realized Gains / (Realized Gains + Paper Gains)
    
    Args:
        realized_gains: Absolute positive value of realized profits.
        paper_gains: Absolute positive value of unrealized profits.
        
    Returns:
        Decimal representing PGR (0.0 to 1.0)
    """
    if realized_gains < 0 or paper_gains < 0:
        raise ValueError("Gains must be non-negative.")
        
    total_gains = realized_gains + paper_gains
    if total_gains == Decimal("0"):
        return Decimal("0.0")
        
    return realized_gains / total_gains


def calculate_plr(realized_losses: Decimal, paper_losses: Decimal) -> Decimal:
    """
    Proportion of Losses Realized (PLR).
    Formula: Realized Losses / (Realized Losses + Paper Losses)
    
    Args:
        realized_losses: Absolute positive value of realized losses.
        paper_losses: Absolute positive value of unrealized losses.
        
    Returns:
        Decimal representing PLR (0.0 to 1.0)
    """
    if realized_losses < 0 or paper_losses < 0:
        raise ValueError("Losses must be non-negative absolute values.")
        
    total_losses = realized_losses + paper_losses
    if total_losses == Decimal("0"):
        return Decimal("0.0")
        
    return realized_losses / total_losses


def calculate_disposition_effect(pgr: Decimal, plr: Decimal) -> Decimal:
    """
    Disposition Effect Score.
    Formula: PGR - PLR
    Positive score (>0) indicates a bias towards selling winners and holding losers.
    """
    return pgr - plr


def calculate_hhi(market_values: list[Decimal]) -> Decimal:
    """
    Herfindahl-Hirschman Index (HHI) for Portfolio Concentration.
    Formula: sum( (market_value_i / total_market_value * 100)^2 )
    
    Args:
        market_values: List of market values for all active holdings.
        
    Returns:
        HHI score. < 1500 (diversified), 1500-2500 (moderate concentration), > 2500 (highly concentrated).
        Max value is 10000 (single asset).
    """
    total_market_value = sum(market_values)
    if total_market_value == Decimal("0"):
        return Decimal("0.0")
        
    hhi = Decimal("0.0")
    for mv in market_values:
        if mv < 0:
            raise ValueError("Market values cannot be negative.")
        if mv == Decimal("0"):
            continue
        share = (mv / total_market_value) * Decimal("100")
        hhi += share ** Decimal("2")
        
    return hhi


def calculate_ptr(total_buys: Decimal, total_sells: Decimal, avg_portfolio_value: Decimal) -> Decimal:
    """
    Portfolio Turnover Ratio (PTR).
    Formula: Min(Total Buys, Total Sells) / Average Portfolio Value
    
    Args:
        total_buys: Gross value of all buy transactions in period.
        total_sells: Gross value of all sell transactions in period.
        avg_portfolio_value: Average value of portfolio over period.
        
    Returns:
        Decimal representing turnover percentage (e.g. 0.10 = 10%)
    """
    if total_buys < 0 or total_sells < 0 or avg_portfolio_value < 0:
        raise ValueError("Values must be non-negative.")
        
    if avg_portfolio_value == Decimal("0"):
        return Decimal("0.0")
        
    return min(total_buys, total_sells) / avg_portfolio_value


def calculate_cost_drag(total_costs: Decimal, total_traded_value: Decimal) -> Decimal:
    """
    Cost Drag Percentage.
    Formula: (Brokerage + STT + Fees) / Total Traded Value
    
    Args:
        total_costs: Sum of all fees, brokerage, STT, and other charges.
        total_traded_value: Sum of gross transaction values.
        
    Returns:
        Decimal representing percentage drag (e.g., 0.015 = 1.5%)
    """
    if total_costs < 0 or total_traded_value < 0:
        raise ValueError("Costs and traded value must be non-negative.")
        
    if total_traded_value == Decimal("0"):
        return Decimal("0.0")
        
    return total_costs / total_traded_value
