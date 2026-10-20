"""
Consistency checks for docs/statement-of-applicability-v2.md.

The table in section 3 is the source of truth. These tests verify that it
lists exactly the 93 controls of ISO/IEC 27001:2022 Annex A, and that the
summary in section 4 matches the counts computed from the table.
"""

import re
from collections import Counter
from pathlib import Path

SOA_PATH = Path(__file__).resolve().parents[2] / "docs" / "statement-of-applicability-v2.md"

EXPECTED_IDS = (
    [f"A.5.{n}" for n in range(1, 38)]
    + [f"A.6.{n}" for n in range(1, 9)]
    + [f"A.7.{n}" for n in range(1, 15)]
    + [f"A.8.{n}" for n in range(1, 35)]
)
VALID_STATUSES = {"I", "P", "Pl", "NA"}
ROW = re.compile(r"^\|\s*(A\.\d+\.\d+)\s*\|[^|]*\|\s*([^|]+?)\s*\|")


def _rows():
    text = SOA_PATH.read_text(encoding="utf-8")
    table = text.split("## 3.", 1)[1].split("## 4.", 1)[0]
    rows = []
    for line in table.splitlines():
        m = ROW.match(line)
        if m:
            rows.append((m.group(1), m.group(2)))
    return rows


def _summary():
    text = SOA_PATH.read_text(encoding="utf-8")
    section = text.split("## 4.", 1)[1]

    def grab(label):
        m = re.search(rf"\*\*{re.escape(label)}:\*\*\s*(\d+)", section)
        assert m, f"campo em falta na secao 4: {label}"
        return int(m.group(1))

    planned_ids = re.search(r"\*\*Planned:\*\*\s*\d+\s*\(([^)]*)\)", section)
    return {
        "total": grab("Total controls"),
        "applicable": grab("Applicable"),
        "na": grab("Not Applicable"),
        "implemented_partial": grab("Implemented / Partial"),
        "planned": grab("Planned"),
        "planned_ids": (
            sorted(i.strip() for i in planned_ids.group(1).split(","))
            if planned_ids
            else []
        ),
    }


def test_soa_has_exactly_the_93_annex_a_controls():
    ids = [i for i, _ in _rows()]
    duplicates = [i for i, c in Counter(ids).items() if c > 1]
    missing = sorted(set(EXPECTED_IDS) - set(ids))
    unknown = sorted(set(ids) - set(EXPECTED_IDS))
    assert duplicates == [], f"duplicados: {duplicates}"
    assert missing == [], f"ausentes: {missing}"
    assert unknown == [], f"desconhecidos: {unknown}"
    assert len(ids) == 93


def test_soa_statuses_are_valid():
    invalid = [(i, s) for i, s in _rows() if s not in VALID_STATUSES]
    assert invalid == [], f"estados invalidos: {invalid}"


def test_soa_summary_matches_table():
    rows = _rows()
    counts = Counter(s for _, s in rows)
    summary = _summary()
    assert summary["total"] == len(rows)
    assert summary["na"] == counts["NA"]
    assert summary["applicable"] == len(rows) - counts["NA"]
    assert summary["implemented_partial"] == counts["I"] + counts["P"]
    assert summary["planned"] == counts["Pl"]
    assert summary["planned_ids"] == sorted(i for i, s in rows if s == "Pl")
