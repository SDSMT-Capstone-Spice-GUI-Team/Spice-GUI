"""Tests for the ProfileManager singleton controller."""

import pytest
from controllers.profile_manager import ProfileManager
from models.course_profile import BUILTIN_PROFILES


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Reset the ProfileManager singleton before each test."""
    ProfileManager._instance = None
    yield
    ProfileManager._instance = None


class TestSingleton:
    def test_same_instance(self):
        a = ProfileManager()
        b = ProfileManager()
        assert a is b

    def test_default_profile_is_full(self):
        pm = ProfileManager()
        assert pm.get_profile().id == "full"


class TestGetAndSetProfile:
    def test_set_profile(self):
        pm = ProfileManager()
        pm.set_profile("ee120")
        assert pm.get_profile().id == "ee120"

    def test_set_profile_unknown_raises(self):
        pm = ProfileManager()
        with pytest.raises(KeyError, match="Unknown profile id"):
            pm.set_profile("nonexistent")

    def test_set_same_profile_no_notify(self):
        pm = ProfileManager()
        calls = []
        pm.register_observer(lambda p: calls.append(p))
        pm.set_profile("full")  # already active
        assert len(calls) == 0

    def test_set_profile_round_trip(self):
        pm = ProfileManager()
        pm.set_profile("ee120")
        pm.set_profile("full")
        assert pm.get_profile().id == "full"


class TestListProfiles:
    def test_returns_all_builtin(self):
        pm = ProfileManager()
        profiles = pm.list_profiles()
        ids = {p.id for p in profiles}
        assert ids == set(BUILTIN_PROFILES.keys())

    def test_sorted_by_id(self):
        pm = ProfileManager()
        profiles = pm.list_profiles()
        ids = [p.id for p in profiles]
        assert ids == sorted(ids)


class TestObserverPattern:
    def test_register_and_notify(self):
        pm = ProfileManager()
        received = []
        pm.register_observer(lambda p: received.append(p))
        pm.set_profile("ee120")
        assert len(received) == 1
        assert received[0].id == "ee120"

    def test_multiple_observers(self):
        pm = ProfileManager()
        a, b = [], []
        pm.register_observer(lambda p: a.append(p.id))
        pm.register_observer(lambda p: b.append(p.id))
        pm.set_profile("circuits1")
        assert a == ["circuits1"]
        assert b == ["circuits1"]

    def test_remove_observer(self):
        pm = ProfileManager()
        calls = []

        def cb(p):
            calls.append(p.id)

        pm.register_observer(cb)
        pm.set_profile("ee120")
        pm.remove_observer(cb)
        pm.set_profile("circuits1")
        assert calls == ["ee120"]

    def test_duplicate_register_ignored(self):
        pm = ProfileManager()
        calls = []

        def cb(p):
            calls.append(1)

        pm.register_observer(cb)
        pm.register_observer(cb)
        pm.set_profile("ee120")
        assert calls == [1]

    def test_remove_nonexistent_observer_no_error(self):
        pm = ProfileManager()
        pm.remove_observer(lambda p: None)  # should not raise

    def test_observer_exception_does_not_break_others(self):
        pm = ProfileManager()
        results = []

        def bad_observer(p):
            raise RuntimeError("boom")

        pm.register_observer(bad_observer)
        pm.register_observer(lambda p: results.append(p.id))
        pm.set_profile("ee120")
        assert results == ["ee120"]
