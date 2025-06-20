from decimal import Decimal

import pytest

from apps.matching.models import CandidateMatch


@pytest.mark.parametrize(
    "score,expected",
    [
        (Decimal("0.0"), 1),
        (Decimal("0.25"), 2),
        (Decimal("0.49"), 5),
        (Decimal("0.50"), 5),
        (Decimal("0.55"), 6),
        (Decimal("0.56"), 6),
        (Decimal("0.65"), 7),
        (Decimal("0.80"), 8),
        (Decimal("0.85"), 9),
        (Decimal("0.96"), 10),
    ],
)
def test_score_to_rating(score, expected):
    candidate_match = CandidateMatch()
    assert candidate_match._score_to_rating(score) == expected
