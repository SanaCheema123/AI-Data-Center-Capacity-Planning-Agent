from app.ai.providers.local import LocalRulesProvider


def test_local_provider_requires_context() -> None:
    provider = LocalRulesProvider()
    assert provider.health_check() is True
    assert provider.generate_text("question", context={}) == "Insufficient data for reliable recommendation."
