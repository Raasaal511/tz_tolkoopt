"""Тесты recommend_price: обычный расчёт, сбой источника и границы правил."""

import asyncio
import unittest
from decimal import Decimal

from starter import recommend_price, sample_fetch_offers


def _offers(status, offers):
    async def fetch():
        return {"status": status, "offers": offers}

    return fetch


def _run(fetch, current_price, min_price, timeout_s=2.0):
    return asyncio.run(recommend_price(
        fetch,
        current_price=Decimal(current_price),
        min_price=Decimal(min_price),
        timeout_s=timeout_s,
    ))


class RecommendPriceTest(unittest.TestCase):
    def test_sample_calculation_applies_undercut(self):
        result = asyncio.run(recommend_price(
            sample_fetch_offers,
            current_price=Decimal("4900.00"),
            min_price=Decimal("4500.00"),
        ))

        self.assertEqual(result["price"], Decimal("4728.00"))
        self.assertEqual(result["decision"], "APPLY")
        self.assertIsInstance(result["price"], Decimal)

    def test_timeout_holds_current_price(self):
        async def slow_fetch():
            await asyncio.sleep(1)
            return {"status": "success", "offers": []}

        result = _run(slow_fetch, "4900.00", "4500.00", timeout_s=0.05)

        self.assertEqual(result["price"], Decimal("4900.00"))
        self.assertEqual(result["decision"], "HOLD")

    def test_source_exception_holds_current_price(self):
        async def broken_fetch():
            raise RuntimeError("площадка недоступна")

        result = _run(broken_fetch, "4900.00", "4500.00")

        self.assertEqual(result["price"], Decimal("4900.00"))
        self.assertEqual(result["decision"], "HOLD")

    def test_error_status_holds_current_price(self):
        result = _run(_offers("error", []), "4900.00", "4500.00")

        self.assertEqual(result["price"], Decimal("4900.00"))
        self.assertEqual(result["decision"], "HOLD")

    def test_no_suitable_offers_keeps_price_below_minimum(self):
        offers = [
            {"seller": "MyShop", "price": Decimal("10.00"), "delivery_days": 1},
            {"seller": "FAR", "price": Decimal("10.00"), "delivery_days": None},
            {"seller": "SLOW", "price": Decimal("10.00"), "delivery_days": 7},
        ]
        result = _run(_offers("success", offers), "100.00", "150.00")

        self.assertEqual(result["price"], Decimal("100.00"))
        self.assertEqual(result["decision"], "HOLD")

    def test_undercut_rounds_down_to_kopeck(self):
        offers = [
            {"seller": "PARTS", "price": Decimal("101.00"), "delivery_days": 6},
        ]
        result = _run(_offers("success", offers), "100.00", "50.00")

        self.assertEqual(result["price"], Decimal("99.48"))
        self.assertEqual(result["decision"], "APPLY")

    def test_recommendation_does_not_fall_below_min_price(self):
        offers = [
            {"seller": "PARTS", "price": Decimal("4800.00"), "delivery_days": 3},
        ]
        result = _run(_offers("success", offers), "4900.00", "4800.00")

        self.assertEqual(result["price"], Decimal("4800.00"))
        self.assertEqual(result["decision"], "APPLY")

    def test_exactly_thirty_percent_is_apply(self):
        offers = [
            {"seller": "PARTS", "price": Decimal("100.00"), "delivery_days": 1},
        ]
        result = _run(_offers("success", offers), "100.00", "130.00")

        self.assertEqual(result["price"], Decimal("130.00"))
        self.assertEqual(result["decision"], "APPLY")

    def test_change_above_thirty_percent_needs_review(self):
        offers = [
            {"seller": "PARTS", "price": Decimal("70.00"), "delivery_days": 1},
        ]
        result = _run(_offers("success", offers), "100.00", "50.00")

        self.assertEqual(result["price"], Decimal("68.95"))
        self.assertEqual(result["decision"], "REVIEW")


if __name__ == "__main__":
    unittest.main()
