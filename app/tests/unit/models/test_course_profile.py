"""Tests for the CourseProfile dataclass and built-in profiles."""

import pytest
from models.course_profile import BUILTIN_PROFILES, CourseProfile


class TestCourseProfileDataclass:
    """Tests for the CourseProfile dataclass itself."""

    def test_create_profile(self):
        profile = CourseProfile(
            id="test",
            name="Test Profile",
            description="A test profile.",
            allowed_components=["Resistor"],
            allowed_analyses=["op"],
            show_advanced_panels=False,
        )
        assert profile.id == "test"
        assert profile.name == "Test Profile"
        assert profile.description == "A test profile."
        assert profile.allowed_components == ["Resistor"]
        assert profile.allowed_analyses == ["op"]
        assert profile.show_advanced_panels is False

    def test_defaults(self):
        profile = CourseProfile(id="x", name="X", description="X")
        assert profile.allowed_components == []
        assert profile.allowed_analyses == []
        assert profile.show_advanced_panels is False

    def test_frozen(self):
        profile = CourseProfile(id="x", name="X", description="X")
        with pytest.raises(AttributeError):
            profile.name = "changed"

    def test_equality(self):
        a = CourseProfile(id="a", name="A", description="A")
        b = CourseProfile(id="a", name="A", description="A")
        assert a == b

    def test_inequality(self):
        a = CourseProfile(id="a", name="A", description="A")
        b = CourseProfile(id="b", name="B", description="B")
        assert a != b


class TestBuiltinProfiles:
    """Tests for the five built-in profiles."""

    EXPECTED_IDS = {"ee120", "circuits1", "circuits2", "me301", "full"}

    def test_all_builtin_ids_present(self):
        assert set(BUILTIN_PROFILES.keys()) == self.EXPECTED_IDS

    def test_count(self):
        assert len(BUILTIN_PROFILES) == 5

    @pytest.mark.parametrize("profile_id", ["ee120", "circuits1", "circuits2", "me301", "full"])
    def test_profile_has_required_fields(self, profile_id):
        p = BUILTIN_PROFILES[profile_id]
        assert isinstance(p.id, str) and p.id
        assert isinstance(p.name, str) and p.name
        assert isinstance(p.description, str) and p.description
        assert isinstance(p.allowed_components, list)
        assert isinstance(p.allowed_analyses, list)
        assert isinstance(p.show_advanced_panels, bool)

    def test_ee120_dc_only(self):
        p = BUILTIN_PROFILES["ee120"]
        assert p.allowed_analyses == ["op"]
        assert "Resistor" in p.allowed_components
        assert "Capacitor" not in p.allowed_components
        assert p.show_advanced_panels is False

    def test_full_has_all_components(self):
        p = BUILTIN_PROFILES["full"]
        assert len(p.allowed_components) >= 10
        assert p.show_advanced_panels is True

    def test_circuits2_includes_opamp(self):
        p = BUILTIN_PROFILES["circuits2"]
        assert "Op-Amp" in p.allowed_components
        assert p.show_advanced_panels is True

    def test_me301_no_ac(self):
        p = BUILTIN_PROFILES["me301"]
        assert "ac" not in p.allowed_analyses
        assert "tran" in p.allowed_analyses
