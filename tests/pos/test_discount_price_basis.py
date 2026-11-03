"""Regression tests for POS discount price-basis validation."""

import pytest

from pos.transactions import validate_discount_price_basis


@pytest.mark.parametrize(
    "price_basis",
    ["listed", "realized", "unknown"],
)
def test_valid_price_basis_is_accepted(price_basis):
    assert validate_discount_price_basis(price_basis) == price_basis


@pytest.mark.parametrize(
    "price_basis",
    ["", "gross", "net", "LISTED", "discounted"],
)
def test_invalid_price_basis_is_rejected(price_basis):
    with pytest.raises(ValueError, match="Price basis must be"):
        validate_discount_price_basis(price_basis)
