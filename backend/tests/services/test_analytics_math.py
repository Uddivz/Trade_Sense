import pytest
from decimal import Decimal
from app.services.analytics import math

def test_calculate_pgr():
    assert math.calculate_pgr(Decimal("50.0"), Decimal("50.0")) == Decimal("0.5")
    assert math.calculate_pgr(Decimal("0.0"), Decimal("100.0")) == Decimal("0.0")
    assert math.calculate_pgr(Decimal("100.0"), Decimal("0.0")) == Decimal("1.0")
    assert math.calculate_pgr(Decimal("0.0"), Decimal("0.0")) == Decimal("0.0")
    
    with pytest.raises(ValueError):
        math.calculate_pgr(Decimal("-10.0"), Decimal("10.0"))

def test_calculate_plr():
    assert math.calculate_plr(Decimal("30.0"), Decimal("70.0")) == Decimal("0.3")
    assert math.calculate_plr(Decimal("0.0"), Decimal("0.0")) == Decimal("0.0")

def test_calculate_disposition_effect():
    assert math.calculate_disposition_effect(Decimal("0.6"), Decimal("0.2")) == Decimal("0.4")
    assert math.calculate_disposition_effect(Decimal("0.2"), Decimal("0.8")) == Decimal("-0.6")

def test_calculate_hhi():
    # 2 equal positions -> 50% each -> 2500 + 2500 = 5000
    assert math.calculate_hhi([Decimal("100.0"), Decimal("100.0")]) == Decimal("5000.0")
    # 1 position -> 100% -> 10000
    assert math.calculate_hhi([Decimal("500.0")]) == Decimal("10000.0")
    # Empty
    assert math.calculate_hhi([]) == Decimal("0.0")
    # Zeros
    assert math.calculate_hhi([Decimal("0.0"), Decimal("0.0")]) == Decimal("0.0")

def test_calculate_ptr():
    assert math.calculate_ptr(Decimal("100.0"), Decimal("50.0"), Decimal("1000.0")) == Decimal("0.05")
    assert math.calculate_ptr(Decimal("0.0"), Decimal("0.0"), Decimal("1000.0")) == Decimal("0.0")
    assert math.calculate_ptr(Decimal("50.0"), Decimal("50.0"), Decimal("0.0")) == Decimal("0.0")

def test_calculate_cost_drag():
    assert math.calculate_cost_drag(Decimal("15.0"), Decimal("1000.0")) == Decimal("0.015")
    assert math.calculate_cost_drag(Decimal("0.0"), Decimal("0.0")) == Decimal("0.0")
