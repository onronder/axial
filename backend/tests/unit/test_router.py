"""
Test Suite for LLM Router Service

Production-grade tests for model tier enforcement:
- BASIC tier users ALWAYS get GPT-4o-mini (no GPT-4o leaks)
- HYBRID tier users get smart routing based on complexity
- PREMIUM tier users get GPT-4o priority

This is critical for cost control and plan enforcement.
"""


import pytest

from core.config import settings
from core.quotas import QUOTA_LIMITS
from services.router import LLMRouter, ModelSelection, llm_router


class TestModelTierEnforcement:
    """
    Critical tests for plan-based model gating.

    These tests ensure that users on lower-tier plans cannot
    access expensive models regardless of query complexity.
    """

    @pytest.fixture
    def router(self):
        """Create a fresh router instance for each test."""
        return LLMRouter()

    # =========================================================================
    # BASIC TIER TESTS (Free/Starter plans - strictest gate)
    # =========================================================================

    @pytest.mark.unit
    def test_basic_tier_always_returns_speed_model_for_simple_query(self, router):
        """BASIC tier must use GPT-4o-mini even for simple queries."""
        result = router.select_model(plan="free", complexity="SIMPLE")

        assert result.provider == "openai"
        assert "gpt-4o-mini" in result.model.lower()
        assert "Standard tier" in result.reason

    @pytest.mark.unit
    def test_basic_tier_blocks_gpt4o_for_complex_query(self, router):
        """
        CRITICAL: BASIC tier users must NEVER get GPT-4o regardless of complexity.
        This is the core cost protection mechanism.
        """
        result = router.select_model(plan="free", complexity="COMPLEX")

        # Must NOT be GPT-4o (the intelligence model)
        assert "gpt-4o-mini" in result.model.lower(), f"Got {result.model} instead of gpt-4o-mini"
        assert result.model.lower() != "gpt-4o", "BASIC tier should not get GPT-4o"

        # Must be GPT-4o-mini (the speed model)
        assert result.provider == "openai"

    @pytest.mark.unit
    def test_starter_plan_uses_basic_tier(self, router):
        """Starter plan should be on BASIC tier (GPT-4o-mini only)."""
        result = router.select_model(plan="starter", complexity="COMPLEX")

        assert result.provider == "openai"
        assert "gpt-4o-mini" in result.model.lower()

    @pytest.mark.unit
    def test_free_plan_complex_query_no_intelligence_leak(self, router):
        """
        Regression test: Ensure complex queries from free users
        cannot exploit routing logic to reach GPT-4o.
        """
        # Try various complexity values that might bypass checks
        for complexity in ["COMPLEX", "complex", "VERY_COMPLEX", None, ""]:
            result = router.select_model(plan="free", complexity=complexity)

            # Should always be speed model
            assert result.provider == "openai", f"Leaked to {result.provider} with complexity={complexity}"

    # =========================================================================
    # HYBRID TIER TESTS (Pro plan - smart routing)
    # =========================================================================

    @pytest.mark.unit
    def test_hybrid_tier_routes_simple_to_speed_model(self, router):
        """HYBRID tier should use GPT-4o-mini for simple queries (cost efficiency)."""
        result = router.select_model(plan="pro", complexity="SIMPLE")

        assert result.provider == "openai"
        assert "gpt-4o-mini" in result.model.lower()
        assert "speed" in result.reason.lower() or "simple" in result.reason.lower()

    @pytest.mark.unit
    def test_hybrid_tier_routes_complex_to_intelligence_model(self, router):
        """HYBRID tier should use GPT-4o for complex queries."""
        result = router.select_model(plan="pro", complexity="COMPLEX")

        assert result.provider == "openai"
        assert "gpt" in result.model.lower()

    @pytest.mark.unit
    def test_intent_keywords_force_smart_routing(self, router):
        """Intent keywords should force smart routing on premium plans."""
        result = router.select_model(
            plan="pro",
            complexity="SIMPLE",
            query_text="Please refactor this module",
        )
        assert result.provider == "openai"
        assert settings.PRIMARY_MODEL_NAME.lower() in result.model.lower()

    @pytest.mark.unit
    def test_hybrid_tier_complexity_classification_matters(self, router):
        """Different complexity levels should yield different models for HYBRID."""
        simple_result = router.select_model(plan="pro", complexity="SIMPLE")
        complex_result = router.select_model(plan="pro", complexity="COMPLEX")

        # Should be different models (both from OpenAI but different model names)
        assert simple_result.model != complex_result.model, \
            f"Expected different models, got {simple_result.model} and {complex_result.model}"
        # Simple should use speed model, complex should use intelligence model
        assert "gpt-4o-mini" in simple_result.model.lower()
        assert "gpt-4o" in complex_result.model.lower()

    # =========================================================================
    # PREMIUM TIER TESTS (Enterprise plan - best quality)
    # =========================================================================

    @pytest.mark.unit
    def test_premium_tier_uses_hybrid_routing(self, router):
        """PREMIUM tier should use Hybrid routing (Speed for Simple, Intelligence for Complex)."""
        # Simple -> Speed
        result_simple = router.select_model(plan="enterprise", complexity="SIMPLE")
        assert result_simple.provider == "openai"
        assert "gpt-4o-mini" in result_simple.model.lower()

        # Complex -> Intelligence
        result_complex = router.select_model(plan="enterprise", complexity="COMPLEX")
        assert result_complex.provider == "openai"
        assert "gpt" in result_complex.model.lower()

    @pytest.mark.unit
    def test_premium_tier_complex_uses_gpt4o(self, router):
        """PREMIUM tier should use GPT-4o for complex as well."""
        result = router.select_model(plan="enterprise", complexity="COMPLEX")

        assert result.provider == "openai"
        assert "gpt" in result.model.lower()

    # =========================================================================
    # EDGE CASES AND SECURITY TESTS
    # =========================================================================

    @pytest.mark.unit
    def test_unknown_plan_defaults_to_basic_tier(self, router):
        """Unknown plans should default to BASIC for security."""
        result = router.select_model(plan="unknown_plan", complexity="COMPLEX")

        # Should NOT give premium access
        assert result.provider == "openai"
        assert "gpt-4o-mini" in result.model.lower()

    @pytest.mark.unit
    def test_intent_keywords_respect_standard_tier(self, router):
        """Keyword forcing should not bypass standard tier gates."""
        result = router.select_model(
            plan="free",
            complexity="SIMPLE",
            query_text="optimize the architecture",
        )
        assert result.provider == "openai"
        assert "gpt-4o-mini" in result.model.lower()

    @pytest.mark.unit
    def test_unknown_plan_logs_and_defaults_when_limits_raise(self, monkeypatch, router):
        monkeypatch.setattr("services.router.get_plan_limits", lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("bad plan")))
        result = router.select_model(plan="mystery", complexity="SIMPLE")
        assert result.provider == "openai"

    @pytest.mark.unit
    def test_none_plan_defaults_to_basic_tier(self, router):
        """None plan should default to BASIC for security."""
        result = router.select_model(plan=None, complexity="COMPLEX")

        assert result.provider == "openai"
        assert "gpt-4o-mini" in result.model.lower()

    @pytest.mark.unit
    def test_empty_plan_defaults_to_basic_tier(self, router):
        """Empty string plan should default to BASIC for security."""
        result = router.select_model(plan="", complexity="COMPLEX")

        assert result.provider == "openai"
        assert "gpt-4o-mini" in result.model.lower()

    @pytest.mark.unit
    def test_get_model_for_plan_handles_limits_error(self, monkeypatch, router):
        monkeypatch.setattr("services.router.get_plan_limits", lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("bad plan")))
        result = router.get_model_for_plan("unknown")
        assert result.provider == "openai"

    @pytest.mark.unit
    def test_case_insensitive_plan_handling(self, router):
        """Plan names should be case-insensitive."""
        results = [
            router.select_model(plan="FREE", complexity="SIMPLE"),
            router.select_model(plan="Free", complexity="SIMPLE"),
            router.select_model(plan="free", complexity="SIMPLE"),
        ]

        # All should route to same model
        assert all(r.provider == results[0].provider for r in results)
        assert all(r.model == results[0].model for r in results)

    @pytest.mark.unit
    def test_case_insensitive_complexity_handling(self, router):
        """Complexity values should be case-insensitive."""
        results_simple = [
            router.select_model(plan="pro", complexity="SIMPLE"),
            router.select_model(plan="pro", complexity="simple"),
            router.select_model(plan="pro", complexity="Simple"),
        ]

        assert all(r.provider == results_simple[0].provider for r in results_simple)

    @pytest.mark.unit
    def test_none_complexity_defaults_to_simple(self, router):
        """None complexity should default to SIMPLE."""
        result = router.select_model(plan="pro", complexity=None)

        # For HYBRID tier with SIMPLE, should use speed model
        assert result.provider == "openai"

    # =========================================================================
    # MODEL SELECTION RESPONSE STRUCTURE
    # =========================================================================

    @pytest.mark.unit
    def test_model_selection_has_required_fields(self, router):
        """ModelSelection should have provider, model, and reason."""
        result = router.select_model(plan="pro", complexity="COMPLEX")

        assert isinstance(result, ModelSelection)
        assert hasattr(result, "provider")
        assert hasattr(result, "model")
        assert hasattr(result, "reason")

        assert result.provider is not None
        assert result.model is not None
        assert result.reason is not None
        assert len(result.reason) > 0


class TestGetModelForPlan:
    """Tests for get_model_for_plan helper method."""

    @pytest.fixture
    def router(self):
        return LLMRouter()

    @pytest.mark.unit
    def test_premium_plan_gets_default_model(self, router):
        """get_model_for_plan defaults to speed model for efficiency."""
        result = router.get_model_for_plan("enterprise")

        assert result.provider == "openai"
        assert "gpt-4o-mini" in result.model.lower()

    @pytest.mark.unit
    def test_non_premium_plan_gets_speed_model(self, router):
        """Non-PREMIUM tiers should get speed model as default."""
        for plan in ["free", "starter", "pro"]:
            result = router.get_model_for_plan(plan)

            assert result.provider == "openai", f"Plan {plan} got wrong provider"




class TestPlanConfigurationConsistency:
    """Tests to ensure router aligns with QUOTA_LIMITS configuration."""

    @pytest.mark.unit
    def test_all_plans_have_model_tier(self):
        """Every plan in QUOTA_LIMITS should have a model_tier defined."""
        for plan_name, limits in QUOTA_LIMITS.items():
            assert hasattr(limits, "model_tier"), f"Plan {plan_name} missing model_tier"
            assert isinstance(limits.model_tier, str)

    @pytest.mark.unit
    def test_free_and_starter_are_standard_tier(self):
        """Free and Starter should be STANDARD to control costs."""
        assert QUOTA_LIMITS["free"].model_tier == "standard"
        assert QUOTA_LIMITS["starter"].model_tier == "standard"

    @pytest.mark.unit
    def test_pro_is_premium_tier(self):
        """Pro should be PREMIUM for smart routing."""
        assert QUOTA_LIMITS["pro"].model_tier == "premium"

    @pytest.mark.unit
    def test_enterprise_is_premium_tier(self):
        """Enterprise should be PREMIUM for best quality."""
        assert QUOTA_LIMITS["enterprise"].model_tier == "premium"


class TestSingletonInstance:
    """Test that llm_router singleton is properly configured."""

    @pytest.mark.unit
    def test_singleton_exists(self):
        """Singleton instance should be available."""
        assert llm_router is not None
        assert isinstance(llm_router, LLMRouter)

    @pytest.mark.unit
    def test_singleton_has_model_configs(self):
        """Singleton should have model configurations."""
        assert hasattr(llm_router, "SPEED_MODEL")
        assert hasattr(llm_router, "INTELLIGENCE_MODEL")

        assert "provider" in llm_router.SPEED_MODEL
        assert "model" in llm_router.SPEED_MODEL
        assert "provider" in llm_router.INTELLIGENCE_MODEL
        assert "model" in llm_router.INTELLIGENCE_MODEL


class TestFallbackModels:
    @pytest.fixture
    def router(self):
        return LLMRouter()

    @pytest.mark.unit
    def test_fallbacks_include_configured_providers(self, monkeypatch, router):
        monkeypatch.setattr(settings, "GROK_API_KEY", "test-key")
        monkeypatch.setattr(settings, "GROK_MODEL_NAME", "grok-test")
        monkeypatch.setattr(settings, "GROQ_API_KEY", "test-key")
        monkeypatch.setattr(settings, "GROQ_CHAT_MODEL_NAME", "llama-test")

        fallbacks = router.get_fallback_models()
        providers = {fallback.provider for fallback in fallbacks}
        assert "grok" in providers
        assert "groq" in providers
