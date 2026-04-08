from unittest.mock import AsyncMock, patch

import pytest

from services.faithfulness_guard import FaithfulnessResult, faithfulness_guard


@pytest.mark.asyncio
async def test_faithfulness_guard_returns_warning_for_low_score():
    docs = [{"content": "Policy allows refunds within 30 days.", "title": "policy.md"}]

    with patch(
        "services.faithfulness_guard.guardrail_service.run_json_prompt",
        new=AsyncMock(
            return_value={
                "faithful": False,
                "score": 0.2,
                "unsupported_claims": ["refunds are available for 90 days"],
                "reason": "answer overstates the refund window",
            }
        ),
    ):
        result = await faithfulness_guard.check(
            answer="Customers can request refunds within 90 days.",
            docs=docs,
        )

    assert isinstance(result, FaithfulnessResult)
    assert result.checked is True
    assert result.faithful is False
    assert result.warning is not None
    assert result.score == 0.2


@pytest.mark.asyncio
async def test_faithfulness_guard_fails_open_on_model_error():
    docs = [{"content": "Policy allows refunds within 30 days.", "title": "policy.md"}]

    with patch(
        "services.faithfulness_guard.guardrail_service.run_json_prompt",
        new=AsyncMock(side_effect=RuntimeError("boom")),
    ):
        result = await faithfulness_guard.check(
            answer="Customers can request refunds within 90 days.",
            docs=docs,
        )

    assert result.checked is True
    assert result.faithful is True
    assert result.score == 0.5
    assert result.warning is None
