from manga_volume_migrator.core import Chapter, compute_target_path, parse_mangadex_aggregate, plan_migrations

AGGREGATE_SAMPLE = {
    "result": "ok",
    "volumes": {
        "1": {
            "volume": "1",
            "chapters": {
                "1": {"chapter": "1", "id": "abc", "others": [], "count": 1},
                "2": {"chapter": "2", "id": "def", "others": [], "count": 1},
            },
        },
        "2": {
            "volume": "2",
            "chapters": {
                "9":  {"chapter": "9",  "id": "ghi", "others": [], "count": 1},
                "10": {"chapter": "10", "id": "jkl", "others": [], "count": 1},
            },
        },
        "none": {
            "volume": "none",
            "chapters": {
                "380": {"chapter": "380", "id": "mno", "others": [], "count": 1},
            },
        },
    },
}


# --- parse_mangadex_aggregate ---

def test_parse_mangadex_aggregate_maps_chapter_to_volume():
    result = parse_mangadex_aggregate(AGGREGATE_SAMPLE)
    assert result["1"] == "1"
    assert result["2"] == "1"
    assert result["9"] == "2"
    assert result["10"] == "2"


def test_parse_mangadex_aggregate_maps_none_volume():
    result = parse_mangadex_aggregate(AGGREGATE_SAMPLE)
    assert result["380"] == "none"


def test_parse_mangadex_aggregate_returns_empty_on_no_volumes():
    assert parse_mangadex_aggregate({"result": "ok", "volumes": {}}) == {}


def test_parse_mangadex_aggregate_returns_empty_on_missing_volumes_key():
    assert parse_mangadex_aggregate({"result": "ok"}) == {}


# --- compute_target_path ---

def test_compute_target_path_with_volume_returns_subdirectory_path():
    assert compute_target_path("Berserk", "1", "1") == "Berserk Vol 1/Berserk - Ch.1.cbz"


def test_compute_target_path_preserves_chapter_number_as_given():
    assert compute_target_path("Berserk", "10", "2") == "Berserk Vol 2/Berserk - Ch.10.cbz"


def test_compute_target_path_without_volume_returns_flat_path():
    assert compute_target_path("Berserk", "380", None) == "Berserk - Ch.380.cbz"


def test_compute_target_path_with_none_volume_string_returns_flat_path():
    assert compute_target_path("Berserk", "380", "none") == "Berserk - Ch.380.cbz"


def test_compute_target_path_preserves_decimal_chapter_number():
    assert compute_target_path("Dandadan", "1.5", "1") == "Dandadan Vol 1/Dandadan - Ch.1.5.cbz"


def test_compute_target_path_handles_manga_name_with_spaces():
    assert compute_target_path("One Punch-Man", "1", "1") == "One Punch-Man Vol 1/One Punch-Man - Ch.1.cbz"


def test_compute_target_path_handles_large_volume_number():
    assert compute_target_path("Berserk", "100", "12") == "Berserk Vol 12/Berserk - Ch.100.cbz"


# --- plan_migrations ---

def test_plan_migrations_includes_chapter_that_needs_moving():
    chapters = [Chapter("c1", "1", None, "Berserk - Ch.1.cbz")]
    migrations = plan_migrations("Berserk", chapters, {"1": "1"})
    assert len(migrations) == 1
    assert migrations[0].old_filename == "Berserk - Ch.1.cbz"
    assert migrations[0].new_filename == "Berserk Vol 1/Berserk - Ch.1.cbz"
    assert migrations[0].volume == 1
    assert migrations[0].key == "c1"


def test_plan_migrations_excludes_chapter_already_at_correct_path():
    chapters = [Chapter("c1", "1", 1, "Berserk Vol 1/Berserk - Ch.1.cbz")]
    migrations = plan_migrations("Berserk", chapters, {"1": "1"})
    assert migrations == []


def test_plan_migrations_excludes_chapter_not_in_volume_map():
    chapters = [Chapter("c999", "999", None, "Berserk - Ch.999.cbz")]
    migrations = plan_migrations("Berserk", chapters, {})
    assert migrations == []


def test_plan_migrations_excludes_chapter_with_none_volume():
    chapters = [Chapter("c380", "380", None, "Berserk - Ch.380.cbz")]
    migrations = plan_migrations("Berserk", chapters, {"380": "none"})
    assert migrations == []


def test_plan_migrations_only_returns_chapters_needing_moves():
    chapters = [
        Chapter("c1", "1", None, "Berserk - Ch.1.cbz"),
        Chapter("c2", "2", 1, "Berserk Vol 1/Berserk - Ch.2.cbz"),
    ]
    migrations = plan_migrations("Berserk", chapters, {"1": "1", "2": "1"})
    assert len(migrations) == 1
    assert migrations[0].key == "c1"
