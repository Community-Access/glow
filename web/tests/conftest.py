import pytest
from acb_large_print_web import ai_features

# Environment variables that point the support hub at a real GitHub repository
# with a real token. A developer machine or a deploy shell has them set, and
# tests/test_app.py::TestFeedback posts feedback without stubbing the sender --
# so running the suite filed live issues in Community-Access/support, one pair
# per run. Neutralised for every test, everywhere.
_SUPPORT_HUB_ENV = (
    "SUPPORT_HUB_GITHUB_TOKEN",
    "FEEDBACK_GITHUB_TOKEN",
    "SUPPORT_HUB_GITHUB_REPO",
    "FEEDBACK_GITHUB_REPO",
    "SUPPORT_HUB_GITHUB_ASSIGNEE",
    "FEEDBACK_GITHUB_ASSIGNEE",
    "SUPPORT_HUB_GITHUB_LABELS",
    "FEEDBACK_GITHUB_LABELS",
    "SUPPORT_HUB_API_TOKEN",
    "FEEDBACK_API_TOKEN",
    "SUPPORT_HUB_ISSUE_CATEGORIES",
)


@pytest.fixture(autouse=True)
def _isolate_support_hub_env(monkeypatch):
    """No test may reach the real support tracker, whatever the shell carries.

    A test that wants this configuration sets it explicitly with monkeypatch,
    which still works: this only clears what leaked in from outside.
    """
    for name in _SUPPORT_HUB_ENV:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def _isolate_rate_limits():
    """Give every test its own rate-limit budget.

    The limiter is a module-level singleton with process-wide storage, and every
    test client presents the same remote address, so requests accumulate across
    test files. Without this, adding a rate limit to any route can make an
    unrelated test fail with a spurious 429 depending purely on ordering. Tests
    that mean to exercise throttling still can -- they just start from clean.
    """
    from acb_large_print_web.app import limiter

    try:
        limiter.reset()
    except Exception:
        pass
    yield


def _ai_available() -> bool:
    try:
        return ai_features.ai_chat_enabled()
    except Exception:
        return False


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "ai_live: mark test as requiring a live AI provider (OpenRouter) and skip when AI is disabled",
    )
    config.addinivalue_line(
        "markers",
        "ai_whisper: mark test as requiring the Whisper audio feature and skip when disabled",
    )


def pytest_runtest_setup(item):
    # If a test is marked ai_live, skip when AI platform is not available
    if item.get_closest_marker("ai_live") and not _ai_available():
        pytest.skip("AI not configured or disabled")

    # If a test is marked ai_whisper, ensure whisperer feature is enabled
    if item.get_closest_marker("ai_whisper"):
        try:
            if not ai_features.ai_whisperer_enabled():
                pytest.skip("AI whisperer disabled via feature flags")
        except Exception:
            pytest.skip("AI whisperer check failed; skipping")


@pytest.fixture
def require_ai_feature():
    """Callable fixture tests can call to require a particular AI feature at runtime.

    Usage in tests::
        def test_x(require_ai_feature):
            require_ai_feature('whisper')
            ...
    """

    def _require(feature: str) -> None:
        if feature == "whisper":
            if not ai_features.ai_whisperer_enabled():
                pytest.skip("AI whisperer disabled")
        else:
            if not _ai_available():
                pytest.skip(f"AI feature '{feature}' unavailable")

    return _require


@pytest.fixture
def feature_flags_fixture(tmp_path):
    """Fixture to temporarily override server-side feature flags for tests.

    Usage::
        def test_x(feature_flags_fixture):
            feature_flags_fixture.set('GLOW_ENABLE_AI_CHAT', False)
    """
    from acb_large_print_web import feature_flags

    # Snapshot current flags and restore after test
    orig = feature_flags.get_all_flags()

    class _Ctl:
        def set(self, name: str, value: bool) -> None:
            feature_flags.set_flag(name, bool(value))

        def get(self, name: str) -> bool:
            return feature_flags.get_flag(name)

        def all(self) -> dict:
            return feature_flags.get_all_flags()

    ctl = _Ctl()
    yield ctl

    # restore
    for k, v in orig.items():
        feature_flags.set_flag(k, v)
