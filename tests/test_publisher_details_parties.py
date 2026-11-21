"""Publisher details, parties, starter fields and field help (T-046-C, T-046-D, T-043-D, T-043-E)."""
import io
import pathlib
import sqlite3
import sys

from docx import Document
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import core  # noqa: E402
import publisher_parties as pp  # noqa: E402
import publisher_profiles as profiles  # noqa: E402
import starter_fields  # noqa: E402
from library import ComponentLibrary  # noqa: E402


def profile(name, **extra):
    base = {"publisher_name": name, "city": "Lyon", "region": "Rhône",
            "address_line1": "1 Invented Street", "contact_name": "A. Contact"}
    base.update(extra)
    return base


@pytest.fixture
def store(tmp_path):
    return profiles.PublisherProfileStore(tmp_path / "db.sqlite3")


def user_version(path):
    with sqlite3.connect(path) as connection:
        return connection.execute("PRAGMA user_version").fetchone()[0]


# ---- schema -------------------------------------------------------------

def test_upgrade_from_v6_adds_the_tables_backs_up_and_keeps_profiles(tmp_path, monkeypatch):
    path = tmp_path / "db.sqlite3"
    monkeypatch.setattr(profiles, "SCHEMA_VERSION", 6)
    monkeypatch.setattr(profiles, "_MIGRATIONS", {k: v for k, v in profiles._MIGRATIONS.items() if k <= 6})
    old = profiles.PublisherProfileStore(path)
    first = old.save_profile(profile("Old Publisher"))
    assert user_version(path) == 6
    monkeypatch.undo()
    new = profiles.PublisherProfileStore(path)
    assert user_version(path) == profiles.SCHEMA_VERSION >= 7
    assert (tmp_path / "db.sqlite3.bak-6").exists()
    assert new.get_profile_with_details(first)["publisher_name"] == "Old Publisher"
    assert new.get_profile_with_details(first)["details"] == {}
    assert new.list_parties() == []


# ---- details --------------------------------------------------------------

def test_a_detail_with_allowed_values_is_checked_and_stored_as_defined(store):
    store.add_detail_definition("Publisher type", ["Non-profit", "Sole proprietor", "Company"])
    first = store.save_profile(profile("Alpha", details={"Publisher type": "non-profit"}))
    assert store.get_profile_with_details(first)["details"] == {"Publisher type": "Non-profit"}
    with pytest.raises(ValueError, match="Publisher type must be one of: Non-profit, Sole proprietor, Company"):
        store.save_profile(profile("Beta", details={"Publisher type": "Charity"}))
    assert [p["publisher_name"] for p in store.list_profiles()] == ["Alpha"]


def test_a_detail_nobody_defined_is_refused_and_a_blank_one_is_ignored(store):
    with pytest.raises(ValueError, match="not one of the details you defined"):
        store.save_profile(profile("Alpha", details={"Made up": "x"}))
    first = store.save_profile(profile("Alpha", details={"Made up": ""}))
    assert store.get_profile_with_details(first)["details"] == {}


def test_updating_a_profile_without_details_keeps_them_and_clearing_removes_them(store):
    store.add_detail_definition("Publisher type", ["Non-profit", "Company"])
    pid = store.save_profile(profile("Alpha", details={"Publisher type": "Company"}))
    store.save_profile(profile("Alpha", city="Paris"), pid)                 # no details key
    assert store.get_profile_with_details(pid)["details"] == {"Publisher type": "Company"}
    store.save_profile(profile("Alpha", details={"Publisher type": ""}), pid)
    assert store.get_profile_with_details(pid)["details"] == {}


def test_a_free_text_detail_has_no_allowed_values(store):
    store.add_detail_definition("Tax number")
    pid = store.save_profile(profile("Alpha", details={"Tax number": "  123-45  "}))
    assert store.get_profile_with_details(pid)["details"] == {"Tax number": "123-45"}


def test_details_are_removed_with_their_publisher_and_get_profile_is_unchanged(store):
    store.add_detail_definition("Publisher type", ["Company"])
    pid = store.save_profile(profile("Alpha", details={"Publisher type": "Company"}))
    assert "details" not in store.get_profile(pid)
    store.delete_profile(pid)
    with sqlite3.connect(store.path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM publisher_details").fetchone()[0] == 0


def test_a_detail_is_also_an_ordinary_field_definition(store):
    store.add_detail_definition("Publisher type", ["Non-profit"])
    library = ComponentLibrary(store.path)
    definition = next(d for d in library.list_field_definitions() if d["name"] == "Publisher type")
    assert definition["publisher_detail_name"] == "Publisher type"
    assert definition["allowed_values"] == ["Non-profit"]
    with pytest.raises(ValueError, match="already exists"):
        store.add_detail_definition("publisher  TYPE")


# ---- parties --------------------------------------------------------------

def test_parties_can_be_added_renamed_and_removed(store):
    one = store.save_party("Publisher One", "Proprietor")
    store.save_party("Publisher Two")
    assert [p["name"] for p in store.list_parties()] == ["Publisher One", "Publisher Two"]
    with pytest.raises(ValueError, match="already exists"):
        store.save_party("publisher  one")
    store.save_party("First Publisher", "Proprietor", one)
    assert "First Publisher" in [p["name"] for p in store.list_parties()]
    assert store.delete_party(one) and len(store.list_parties()) == 1
    with pytest.raises(ValueError, match="Enter a name"):
        store.save_party("  ")


# ---- matching fields ------------------------------------------------------

PARTIES = [
    {"name": "Publisher One", "name_key": "publisher one", "role": "Proprietor"},
    {"name": "Publisher Two", "name_key": "publisher two", "role": "Publisher"},
]
LINKS = {"publisher type": "Publisher type"}


@pytest.mark.parametrize("field", [
    "Publisher One’s Address", "Publisher One's Address", "publisher one address", "PUBLISHER  ONE’S ADDRESS",
])
def test_curly_and_straight_apostrophes_and_capitals_make_no_difference(field):
    found = pp.resolve_field(field, parties=PARTIES, detail_links=LINKS)
    assert found == pp.Resolution("Publisher One", column="formatted_address")


def test_each_party_field_is_matched_without_listing_names():
    expect = {
        "Publisher One (Proprietor)": ("Publisher One", "publisher_name"),
        "Publisher One": ("Publisher One", "publisher_name"),
        "Publisher One’s State": ("Publisher One", "region"),
        "Publisher Two’s Contact": ("Publisher Two", "contact_name"),
        "Publisher Two Email": ("Publisher Two", "contact_email"),
        "Publisher Two’s City": ("Publisher Two", "city"),
        "Publisher Two (Publisher)": ("Publisher Two", "publisher_name"),
    }
    for name, (party, column) in expect.items():
        assert pp.resolve_field(name, parties=PARTIES, detail_links=LINKS) == pp.Resolution(party, column=column), name


def test_a_party_can_fill_a_detail_and_ordinary_fields_still_work():
    assert pp.resolve_field("Publisher Two’s Publisher Type", parties=PARTIES, detail_links=LINKS) == \
        pp.Resolution("Publisher Two", detail="Publisher type")
    assert pp.resolve_field("Publisher Type", parties=PARTIES, detail_links=LINKS) == \
        pp.Resolution(None, detail="Publisher type")
    assert pp.resolve_field("City", parties=PARTIES, detail_links=LINKS) == pp.Resolution(None, column="city")
    assert pp.resolve_field("Fee", parties=PARTIES, detail_links=LINKS) is None


def test_the_longest_party_name_wins():
    parties = [
        {"name": "Publisher", "name_key": "publisher", "role": ""},
        {"name": "Publisher Two", "name_key": "publisher two", "role": ""},
    ]
    assert pp.resolve_field("Publisher Two’s City", parties=parties).party == "Publisher Two"


def test_with_no_parties_nothing_changes_for_a_single_publisher_document():
    for name, column in (("Publisher Name", "publisher_name"), ("Contact Email", "contact_email"),
                         ("Publisher Address", "formatted_address")):
        assert pp.resolve_field(name) == pp.Resolution(None, column=column)


def test_a_users_own_match_still_applies_and_parties_in_follow_the_form_order():
    r = pp.resolutions_for(
        ["Licensor", "Publisher Two’s City", "Publisher One’s City"],
        parties=PARTIES, user_matches={"Licensor": "publisher_name"},
    )
    assert r["Licensor"] == pp.Resolution(None, column="publisher_name")
    assert pp.parties_in(r) == ["Publisher Two", "Publisher One"]


def test_fill_values_for_two_parties_use_two_profiles_and_leave_the_rest():
    fields = ["Publisher One (Proprietor)", "Publisher One’s Address", "Publisher Two (Publisher)",
              "Publisher Two’s Contact", "Publisher Two’s Publisher Type", "Fee"]
    r = pp.resolutions_for(fields, parties=PARTIES, detail_links=LINKS)
    one = {"publisher_name": "Alpha", "city": "Lyon", "address_line1": "1 Street"}
    two = {"publisher_name": "Beta", "contact_name": "B. Contact", "details": {}}
    first = pp.fill_values(one, r, "Publisher One")
    assert first.values == {"Publisher One (Proprietor)": "Alpha", "Publisher One’s Address": "1 Street, Lyon"}
    second = pp.fill_values(two, r, "Publisher Two")
    assert second.values == {"Publisher Two (Publisher)": "Beta", "Publisher Two’s Contact": "B. Contact"}
    assert second.no_value == [("Publisher Two’s Publisher Type", "Publisher type")]   # says why
    assert pp.fill_values(one, r, None).values == {}                                   # Fee is the user's


def test_one_field_can_be_filled_alone():
    r = pp.resolutions_for(["Publisher One’s City", "Publisher One’s State"], parties=PARTIES)
    result = pp.fill_values({"city": "Lyon", "region": "Rhône"}, r, "Publisher One", only_field="Publisher One’s State")
    assert result.values == {"Publisher One’s State": "Rhône"}


# ---- end to end: the publisher's type chooses the wording ------------------

def build_template(tmp_path):
    document = Document()
    document.add_paragraph("Agreement with {{Publisher Name}}.")
    document.add_paragraph("{{#if Publisher Type = Non-profit}}")
    document.add_paragraph("A non-profit clause applies.")
    document.add_paragraph("{{else}}")
    document.add_paragraph("A standard clause applies.")
    document.add_paragraph("{{/if}}")
    path = tmp_path / "template.docx"
    document.save(path)
    return core.Template(path)


def text_after_fill(template, store, publisher_id):
    profile_data = store.get_profile_with_details(publisher_id)
    names = [f.name for f in template.field_list()]
    resolutions = pp.resolutions_for(
        names, parties=store.list_parties(), user_matches=store.field_match_map(),
        detail_links=store.detail_links(),
    )
    values = pp.fill_values(profile_data, resolutions, None).values
    rendered, _report = core.render(template, values)
    return "\n".join(p.text for p in Document(io.BytesIO(rendered)).paragraphs)


def test_two_publishers_of_different_types_produce_different_wording(tmp_path, store):
    store.add_detail_definition("Publisher Type", ["Non-profit", "Sole proprietor", "Company"])
    charity = store.save_profile(profile("Helping Hands", details={"Publisher Type": "Non-profit"}))
    shop = store.save_profile(profile("Corner Books", details={"Publisher Type": "Sole proprietor"}))
    template = build_template(tmp_path)
    first = text_after_fill(template, store, charity)
    second = text_after_fill(template, store, shop)
    assert "Agreement with Helping Hands." in first and "A non-profit clause applies." in first
    assert "standard clause" not in first
    assert "Agreement with Corner Books." in second and "A standard clause applies." in second
    assert "non-profit clause" not in second


# ---- starter fields (T-043-E) ---------------------------------------------

def test_starter_fields_are_copied_into_the_users_own_list(store):
    library = ComponentLibrary(store.path)
    added, skipped = starter_fields.add_starter_fields(library)
    assert added == starter_fields.starter_names() and skipped == []
    by_name = {d["name"]: d for d in library.list_field_definitions()}
    assert by_name["Works"]["default_format"] == "list"
    assert by_name["Publisher type"]["allowed_values"] == ["Non-profit", "Sole proprietor", "Company"]
    assert by_name["Publisher type"]["publisher_detail_name"] == "Publisher type"
    assert [d["name"] for d in store.list_detail_definitions()] == ["Publisher type"]


def test_starter_fields_are_never_added_twice_or_after_being_archived(store):
    library = ComponentLibrary(store.path)
    starter_fields.add_starter_fields(library)
    again = starter_fields.add_starter_fields(library)
    assert again == ([], starter_fields.starter_names())
    territory = next(d for d in library.list_field_definitions() if d["name"] == "Territory")
    library.archive_field_definition(territory["id"])
    added, skipped = starter_fields.add_starter_fields(library)
    assert added == [] and "Territory" in skipped          # the user's archive sticks


def test_a_starter_field_the_user_already_has_is_left_alone(store):
    library = ComponentLibrary(store.path)
    library.add_field_definition("works", description="my own wording", default_format="")
    added, skipped = starter_fields.add_starter_fields(library)
    assert "Works" in skipped and "Works" not in added
    mine = next(d for d in library.list_field_definitions() if d["name"].lower() == "works")
    assert mine["description"] == "my own wording"


def test_the_starter_list_holds_only_invented_generic_names():
    assert starter_fields.starter_names() == [
        "Works", "Publisher type", "Territory", "Term in years", "Effective Date",
    ]


# ---- help text (T-043-D) --------------------------------------------------

def test_help_text_is_found_ignoring_capitals_spacing_and_possessives(store):
    library = ComponentLibrary(store.path)
    library.add_field_definition("Signing Deadline", description="Thirty days after the effective date.")
    library.add_field_definition("No Help Here")
    help_map = store.field_help_map()
    assert profiles.field_help_for(help_map, "signing   DEADLINE") == "Thirty days after the effective date."
    assert profiles.field_help_for(help_map, "Signing Deadline’s") == "Thirty days after the effective date."
    assert profiles.field_help_for(help_map, "No Help Here") == ""
    assert profiles.field_help_for(help_map, "Unknown") == ""


def test_archived_fields_give_no_help(store):
    library = ComponentLibrary(store.path)
    field_id = library.add_field_definition("Old", description="gone")
    library.archive_field_definition(field_id)
    assert store.field_help_map() == {}
