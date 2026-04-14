"""Structural tests for the Inno Setup installer script (#834).

These validate that the .iss file contains all required sections and
configuration without requiring Inno Setup to be installed.
"""

from pathlib import Path

import pytest

INSTALLER_DIR = Path(__file__).resolve().parent.parent.parent.parent / "installer"
ISS_FILE = INSTALLER_DIR / "spicegui.iss"
COMBINED_LICENSE = INSTALLER_DIR / "LICENSE-COMBINED.txt"


@pytest.fixture
def iss_content():
    return ISS_FILE.read_text(encoding="utf-8")


class TestIssFileExists:
    def test_iss_file_exists(self):
        assert ISS_FILE.is_file(), f"Expected {ISS_FILE}"

    def test_combined_license_exists(self):
        assert COMBINED_LICENSE.is_file(), f"Expected {COMBINED_LICENSE}"


class TestSetupSection:
    def test_app_name(self, iss_content):
        assert "AppName={#MyAppName}" in iss_content

    def test_app_version(self, iss_content):
        assert "#define MyAppVersion" in iss_content

    def test_default_dir(self, iss_content):
        assert "DefaultDirName=" in iss_content

    def test_privileges_lowest(self, iss_content):
        assert "PrivilegesRequired=lowest" in iss_content

    def test_privileges_override(self, iss_content):
        assert "PrivilegesRequiredOverridesAllowed=dialog" in iss_content

    def test_license_file_referenced(self, iss_content):
        assert "LicenseFile=" in iss_content

    def test_output_filename(self, iss_content):
        assert "SpiceGUI-v" in iss_content
        assert "win64-setup" in iss_content

    def test_uninstall_display(self, iss_content):
        assert "UninstallDisplayName=" in iss_content


class TestTasksSection:
    def test_desktop_icon_task(self, iss_content):
        assert "desktopicon" in iss_content

    def test_file_association_task(self, iss_content):
        assert "fileassoc" in iss_content
        assert ".spice" in iss_content


class TestFilesSection:
    def test_dist_source(self, iss_content):
        assert r"dist\SpiceGUI\*" in iss_content

    def test_license_files_included(self, iss_content):
        assert "LICENSE-COMBINED.txt" in iss_content
        assert "NGSPICE-LICENSE.txt" in iss_content


class TestIconsSection:
    def test_start_menu_shortcut(self, iss_content):
        assert "{group}" in iss_content

    def test_desktop_shortcut(self, iss_content):
        assert "{autodesktop}" in iss_content


class TestRegistrySection:
    def test_spice_file_association(self, iss_content):
        assert r"Software\Classes\.spice" in iss_content
        assert "SpiceGUI.Circuit" in iss_content

    def test_open_command(self, iss_content):
        assert r"shell\open\command" in iss_content


class TestRunSection:
    def test_post_install_launch(self, iss_content):
        assert "postinstall" in iss_content


class TestCombinedLicense:
    def test_contains_mit_license(self):
        text = COMBINED_LICENSE.read_text(encoding="utf-8")
        assert "MIT License" in text

    def test_contains_ngspice_bsd(self):
        text = COMBINED_LICENSE.read_text(encoding="utf-8")
        assert "ngspice" in text
        assert "BSD" in text
