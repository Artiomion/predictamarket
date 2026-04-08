"""
Integration tests for edgar-service.
Requires: edgar-service on :8007, EDGAR data seeded for at least AAPL.
"""

import httpx
import pytest

BASE = "http://localhost:8007/api/edgar"
PRO = {"X-User-Id": "00000000-0000-0000-0000-000000000001", "X-User-Tier": "pro"}
FREE = {"X-User-Id": "00000000-0000-0000-0000-000000000001", "X-User-Tier": "free"}


class TestAccessControl:
    def test_free_blocked(self) -> None:
        r = httpx.get(f"{BASE}/AAPL/income", headers=FREE)
        assert r.status_code == 403
        assert "pro" in r.json()["detail"].lower() or "premium" in r.json()["detail"].lower()

    def test_no_auth_blocked(self) -> None:
        r = httpx.get(f"{BASE}/AAPL/income")
        assert r.status_code == 401

    def test_pro_allowed(self) -> None:
        r = httpx.get(f"{BASE}/AAPL/income", headers=PRO)
        assert r.status_code == 200

    def test_premium_allowed(self) -> None:
        headers = {"X-User-Id": "00000000-0000-0000-0000-000000000001", "X-User-Tier": "premium"}
        r = httpx.get(f"{BASE}/AAPL/income", headers=headers)
        assert r.status_code == 200


class TestIncomeStatement:
    def test_structure(self) -> None:
        r = httpx.get(f"{BASE}/AAPL/income", headers=PRO)
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 4, f"Expected >=4 income records, got {len(data)}"
        for field in ["period_end", "revenue", "net_income", "eps_basic"]:
            assert field in data[0], f"Field {field} missing"

    def test_revenue_positive(self) -> None:
        data = httpx.get(f"{BASE}/AAPL/income?limit=5", headers=PRO).json()
        for row in data:
            if row["revenue"] is not None:
                assert row["revenue"] > 0, f"Revenue should be positive: {row}"

    def test_sorted_by_date_desc(self) -> None:
        data = httpx.get(f"{BASE}/AAPL/income", headers=PRO).json()
        dates = [r["period_end"] for r in data]
        assert dates == sorted(dates, reverse=True), "Should be sorted by period_end descending"


class TestBalanceSheet:
    def test_structure(self) -> None:
        data = httpx.get(f"{BASE}/AAPL/balance", headers=PRO).json()
        assert len(data) >= 4
        for field in ["period_end", "total_assets", "total_liabilities", "stockholders_equity"]:
            assert field in data[0], f"Field {field} missing"

    def test_accounting_equation(self) -> None:
        """Assets ≈ Liabilities + Equity (within 5% tolerance)."""
        data = httpx.get(f"{BASE}/AAPL/balance?limit=3", headers=PRO).json()
        for item in data:
            a = item.get("total_assets")
            l = item.get("total_liabilities")
            e = item.get("stockholders_equity")
            if a and l and e and a > 0:
                diff_pct = abs(a - (l + e)) / a
                assert diff_pct < 0.05, \
                    f"Accounting equation violated: A={a}, L={l}, E={e}, diff={diff_pct:.2%}"


class TestCashFlow:
    def test_structure(self) -> None:
        data = httpx.get(f"{BASE}/AAPL/cashflow", headers=PRO).json()
        assert len(data) >= 4
        for field in ["period_end", "operating_cash_flow", "free_cash_flow"]:
            assert field in data[0], f"Field {field} missing"

    def test_fcf_computed(self) -> None:
        """Free cash flow = operating CF - capex."""
        data = httpx.get(f"{BASE}/AAPL/cashflow?limit=3", headers=PRO).json()
        for item in data:
            ocf = item.get("operating_cash_flow")
            capex = item.get("capital_expenditures")
            fcf = item.get("free_cash_flow")
            if ocf and capex and fcf:
                expected = ocf - abs(capex)
                assert abs(fcf - expected) < 1, \
                    f"FCF mismatch: {fcf} != {ocf} - {abs(capex)}"


class TestFilings:
    def test_filings_list(self) -> None:
        r = httpx.get(f"{BASE}/AAPL/filings", headers=PRO)
        assert r.status_code == 200
        filings = r.json()
        assert len(filings) > 0
        f = filings[0]
        assert "filing_type" in f
        assert "filing_date" in f
        assert "ticker" in f
        assert f["ticker"] == "AAPL"


class TestEdgeCases:
    def test_unknown_ticker_empty(self) -> None:
        """Unknown ticker returns empty list (no data, not 404)."""
        r = httpx.get(f"{BASE}/ZZZZ_NOTREAL/income", headers=PRO)
        assert r.status_code == 200
        assert r.json() == []

    def test_limit_param(self) -> None:
        r3 = httpx.get(f"{BASE}/AAPL/income?limit=3", headers=PRO).json()
        r10 = httpx.get(f"{BASE}/AAPL/income?limit=10", headers=PRO).json()
        assert len(r3) <= 3
        assert len(r10) <= 10
        assert len(r3) < len(r10) or len(r10) <= 3
