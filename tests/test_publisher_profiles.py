"""Tests for the local publisher profile database and template field mapping."""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import publisher_profiles as profiles  # noqa: E402


def sample_profile(name="Éditions Exemple"):
    return {
        "publisher_name": name,
        "contact_name": "Camille Martin",
        "contact_title": "Foreign Rights Manager",
        "contact_email": "camille@example.org",
        "contact_phone": "+33 1 23 45 67 89",
        "website": "https://example.org",
        "address_line1": "12 Rue de Paris",
        "address_line2": "Bâtiment B",
        "city": "Lyon",
        "region": "Auvergne-Rhône-Alpes",
        "postal_code": "69002",
        "country": "France",
        "notes": "Prefers email correspondence.",
    }


def test_profile_crud_round_trip(tmp_path):
    store = profiles.PublisherProfileStore(tmp_path / "publishers.sqlite3")
    profile_id = store.save_profile(sample_profile())

    saved = store.get_profile(profile_id)
    assert saved["publisher_name"] == "Éditions Exemple"
    assert saved["contact_name"] == "Camille Martin"
    assert saved["country"] == "France"
    assert len(store.list_profiles()) == 1

    updated = sample_profile()
    updated["contact_name"] = "Alexandre Dupont"
    updated["notes"] = "Updated contact."
    assert store.save_profile(updated, profile_id) == profile_id

    saved = store.get_profile(profile_id)
    assert saved["contact_name"] == "Alexandre Dupont"
    assert saved["notes"] == "Updated contact."
    assert len(store.list_profiles()) == 1

    assert store.delete_profile(profile_id) is True
    assert store.get_profile(profile_id) is None
    assert store.delete_profile(profile_id) is False


def test_publisher_names_are_unique_with_unicode_casefolding(tmp_path):
    store = profiles.PublisherProfileStore(tmp_path / "publishers.sqlite3")
    store.save_profile(sample_profile("Éditions Exemple"))

    with pytest.raises(ValueError, match="already exists"):
        store.save_profile(sample_profile("ÉDITIONS EXEMPLE"))


def test_profile_requires_publisher_name(tmp_path):
    store = profiles.PublisherProfileStore(tmp_path / "publishers.sqlite3")
    with pytest.raises(ValueError, match="publisher name"):
        store.save_profile({"contact_name": "Someone"})


def test_formatted_address_uses_only_populated_parts():
    profile = sample_profile()
    assert profiles.format_address(profile) == (
        "12 Rue de Paris\nBâtiment B\nLyon, Auvergne-Rhône-Alpes 69002\nFrance"
    )
    assert profiles.format_address({"city": "Lyon", "country": "France"}) == "Lyon\nFrance"


def test_template_field_mapping_uses_exact_template_labels():
    profile = sample_profile()
    mapped = profiles.values_for_template(
        profile,
        [
            "International Publisher Name",
            "International Publisher's Contact",
            "International Publisher Address",
            "International Publisher Contact Email",
            "International Publisher Country",
            "Agreement Date",
        ],
    )
    assert mapped == {
        "International Publisher Name": "Éditions Exemple",
        "International Publisher's Contact": "Camille Martin",
        "International Publisher Address": (
            "12 Rue de Paris, Bâtiment B, Lyon, Auvergne-Rhône-Alpes 69002, France"
        ),
        "International Publisher Contact Email": "camille@example.org",
        "International Publisher Country": "France",
    }


def test_empty_profile_values_do_not_overwrite_template_fields():
    profile = {"publisher_name": "Example Publishing", "contact_name": ""}
    assert profiles.values_for_template(
        profile, ["International Publisher Name", "International Publisher Contact"]
    ) == {"International Publisher Name": "Example Publishing"}
