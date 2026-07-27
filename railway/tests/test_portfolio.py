from datetime import date, timedelta

from fastapi.testclient import TestClient

from railway.app.main import app
from railway.app.models import PortfolioEntry
from railway.app.scoring import (
    combine_ppm,
    entries_before_deadline,
    locality_score,
    portfolio_ppm,
    select_for_budget,
)


client = TestClient(app)


def in_days(n: int) -> str:
    return (date.today() + timedelta(days=n)).isoformat()


def test_a_parcel_is_worth_the_same_from_anywhere():
    assert locality_score("shipped", True, 5) == 100
    assert locality_score("digital", False, 5) == 100
    # A ticket in Cyprus stays a ticket in Cyprus.
    assert locality_score("location_bound", True, 5) == 5


def test_shipped_prize_that_does_not_reach_germany_is_worthless():
    assert locality_score("shipped", False, 90) == 0


def test_daily_contest_counts_as_many_tickets():
    assert entries_before_deadline("once", in_days(20)) == 1
    assert entries_before_deadline("daily", in_days(20)) == 21
    assert entries_before_deadline("weekly", in_days(20)) == 3
    assert entries_before_deadline("daily", in_days(-1)) == 0


def test_repeat_entry_compounds():
    single = 10_000  # 1%
    assert combine_ppm(single, 1) == single
    twenty = combine_ppm(single, 20)
    assert 180_000 < twenty < 185_000  # ~18.2%, not 20%


def test_portfolio_beats_any_single_entry():
    chances = [10_000] * 100  # a hundred 1% draws
    combined = portfolio_ppm(chances)
    assert combined > 630_000  # better than 63%
    assert combined < 1_000_000


def test_budget_picks_highest_value_per_minute_first():
    entries = [
        # cheap, low value
        PortfolioEntry(contest_id=1, chance_ppm=100_000,
                       friction_minutes=2, prize_value_eur=20),
        # expensive in time, huge value -> best rate anyway
        PortfolioEntry(contest_id=2, chance_ppm=10_000,
                       friction_minutes=5, prize_value_eur=4_000),
        # pure time sink
        PortfolioEntry(contest_id=3, chance_ppm=1_000,
                       friction_minutes=20, prize_value_eur=50),
    ]
    selected, minutes, marginal = select_for_budget(entries, 10)
    assert selected[0] == 2
    assert 3 not in selected
    assert minutes <= 10
    assert len(marginal) == len(selected)


def test_marginal_gain_shrinks_as_the_portfolio_grows():
    entries = [
        PortfolioEntry(contest_id=i, chance_ppm=200_000,
                       friction_minutes=1, prize_value_eur=100)
        for i in range(1, 8)
    ]
    _selected, _minutes, marginal = select_for_budget(entries, 60)
    assert marginal == sorted(marginal, reverse=True)
    assert marginal[0] > marginal[-1]


def test_portfolio_endpoint_needs_no_credentials():
    response = client.post(
        "/v1/portfolio",
        json={
            "entries": [
                {"contest_id": 1, "chance_ppm": 20_000,
                 "friction_minutes": 2, "prize_value_eur": 300},
                {"contest_id": 2, "chance_ppm": 5_000,
                 "friction_minutes": 3, "prize_value_eur": 900},
            ],
            "minutes_available": 30,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body["selected_ids"]) == {1, 2}
    assert body["win_something_ppm"] > 24_000
    assert body["expected_value_eur"] > 10
