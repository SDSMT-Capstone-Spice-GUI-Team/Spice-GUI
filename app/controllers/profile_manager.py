"""
profile_manager.py - Singleton manager for course profiles.

Follows the same singleton + observer pattern as ThemeManager.
No Qt imports.
"""

from __future__ import annotations

import logging
from typing import Callable, Dict, List, Optional

from models.course_profile import BUILTIN_PROFILES, CourseProfile

logger = logging.getLogger(__name__)


class ProfileManager:
    """
    Singleton manager for the active course profile.

    Usage:
        from controllers.profile_manager import profile_manager

        profile_manager.get_profile()          # current CourseProfile
        profile_manager.set_profile("ee120")   # switch and notify
        profile_manager.list_profiles()        # all registered profiles

        profile_manager.register_observer(my_callback)
    """

    _instance: Optional["ProfileManager"] = None
    _profile: CourseProfile
    _profiles: Dict[str, CourseProfile]
    _observers: List[Callable[[CourseProfile], None]]

    def __new__(cls) -> "ProfileManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._profiles = dict(BUILTIN_PROFILES)
            cls._instance._profile = cls._instance._profiles["full"]
            cls._instance._observers = []
        return cls._instance

    # ── Query ───────────────────────────────────────────────────────

    def get_profile(self) -> CourseProfile:
        """Return the currently active course profile."""
        return self._profile

    def list_profiles(self) -> List[CourseProfile]:
        """Return all registered profiles sorted by id."""
        return sorted(self._profiles.values(), key=lambda p: p.id)

    # ── Mutation ────────────────────────────────────────────────────

    def set_profile(self, profile_id: str) -> None:
        """Activate a profile by id and notify observers.

        Args:
            profile_id: The id of a registered profile.

        Raises:
            KeyError: If no profile with the given id exists.
        """
        if profile_id not in self._profiles:
            raise KeyError(f"Unknown profile id: {profile_id!r}")
        new_profile = self._profiles[profile_id]
        if new_profile is not self._profile:
            self._profile = new_profile
            self._notify_observers()

    # ── Observer pattern ────────────────────────────────────────────

    def register_observer(self, callback: Callable[[CourseProfile], None]) -> None:
        """Register a callback invoked when the active profile changes."""
        if callback not in self._observers:
            self._observers.append(callback)

    def remove_observer(self, callback: Callable[[CourseProfile], None]) -> None:
        """Remove a previously registered observer."""
        if callback in self._observers:
            self._observers.remove(callback)

    def _notify_observers(self) -> None:
        """Notify all registered observers of a profile change."""
        for callback in self._observers:
            try:
                callback(self._profile)
            except Exception:
                logger.exception("Error notifying profile observer")


# Module-level singleton instance for easy import
profile_manager = ProfileManager()
