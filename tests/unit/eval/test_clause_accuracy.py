"""Clause accuracy (R3) and the local extractor that feeds it (spec 13.1)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from generator.build import generate
from marge.domain import Contract, ContractStatus
from marge.eval.clause_accuracy import clause_accuracy, contract_key
from marge.eval.local_extractor import extract_contract, extract_fields


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    out = tmp_path_factory.mktemp("contracts")
    generate(out)
    return out


def _contracts(root: Path) -> list[Contract]:
    return [
        extract_contract(root / "contracts" / f"{stem}.txt", "c-001", ContractStatus.VALIDATED)
        for stem in ("ctr-001-v1", "ctr-004-v1", "ctr-007-v1")
    ]


def test_extractor_reads_the_scalar_fields_of_a_contract(generated):
    fields = extract_fields((generated / "contracts" / "ctr-001-v1.txt").read_text("utf-8"))
    assert fields.customer_name == "CALDER LOGISTICS LTD"
    assert fields.start_date == date(2024, 1, 11)
    assert fields.monthly_subscription == Decimal("5000.00")
    assert fields.extra_hour_rate == Decimal("110.00")
    assert fields.included_hours_per_month == Decimal("60.00")
    assert fields.currency == "EUR"
    assert fields.covered_accounts_or_resources == 40


def test_extractor_keeps_the_scope_lists_whole(generated):
    fields = extract_fields((generated / "contracts" / "ctr-001-v1.txt").read_text("utf-8"))
    assert len(fields.services_included) >= 6
    assert len(fields.exclusions) >= 5
    assert len(fields.sla_commitments) == 3
    assert all(item.subject and item.target for item in fields.sla_commitments)


def test_extractor_flags_the_ambiguous_clause_and_only_that_one(generated):
    ambiguous = extract_fields((generated / "contracts" / "ctr-007-v1.txt").read_text("utf-8"))
    clean = extract_fields((generated / "contracts" / "ctr-004-v1.txt").read_text("utf-8"))
    assert "ambiguous_clause" in ambiguous.spans
    assert "reasonable" in ambiguous.spans["ambiguous_clause"].quote
    assert "ambiguous_clause" not in clean.spans


def test_extractor_reads_a_table_layout_contract(generated):
    fields = extract_fields((generated / "contracts" / "ctr-004-v1.txt").read_text("utf-8"))
    assert fields.customer_name == "MARCHETTI SUPPLY LTD"
    assert fields.monthly_subscription == Decimal("2900.00")


def test_contract_key_matches_the_expected_json_keys(generated):
    contract = _contracts(generated)[0]
    assert contract_key(contract) == "ctr-001-v1"


def _ctr001_expected() -> list[dict]:
    """The hand-written ground truth of ctr-001-v1 (R3)."""
    return [
        {
            "contract_id": "ctr-001",
            "version": 1,
            "customer_name": "CALDER LOGISTICS LTD",
            "start_date": "2024-01-11",
            "end_date": "2027-01-10",
            "renewal_terms": "Automatic renewal for a period of 12 months",
            "termination_notice": "3 months",
            "monthly_subscription": "5000.00",
            "currency": "EUR",
            "included_hours_per_month": "60.00",
            "extra_hour_rate": "110.00",
            "services_included": [
                "24/7 infrastructure monitoring",
                "Data backup and restoration",
                "Operating system patch management",
                "Infrastructure incident management",
                "Access and account management",
                "AWS cost optimisation",
                "Monitoring of the backups and quarterly restoration test",
            ],
            "exclusions": [
                "application development and modification of the Client's code",
                "training of the Client's teams",
                "purchase of hardware and third-party licences",
                "application migration projects",
                "application security audits",
            ],
            "service_hours": "24/7, seven days a week",
            "sla_commitments": [
                {"subject": "Take-over of a critical incident", "target": "30 minutes, 24/7"},
                {"subject": "Availability of the supervised platform", "target": "99.5% per month"},
                {"subject": "Restoration of a backup", "target": "4 business hours"},
            ],
            "penalties": (
                "2 % of the monthly subscription for each critical incident taken over beyond the "
                "committed delay, capped at 15 % of the monthly subscription."
            ),
            "indexation_clause": (
                "Annual price review on 1 January, on presentation of the Syntec index, "
                "within a limit of 3 % per year."
            ),
            "covered_accounts_or_resources": 40,
            "ambiguous_clause": False,
        }
    ]


def test_clause_accuracy_passes_on_the_generated_contracts(generated):
    expected = _ctr001_expected()
    score = clause_accuracy(_contracts(generated)[:1], expected)
    assert score.passed is True
    assert score.value == Decimal("1")


def test_clause_accuracy_fails_when_a_field_is_wrong(generated):
    expected = [
        {
            "contract_id": "ctr-001",
            "version": 1,
            "customer_name": "AUTRE CLIENT",
            "monthly_subscription": "1.00",
            "extra_hour_rate": "1.00",
        }
    ]
    score = clause_accuracy(_contracts(generated)[:1], expected)
    assert score.passed is False
    assert "customer_name" in " ".join(score.detail)


def test_clause_accuracy_reports_a_contract_that_was_not_extracted():
    score = clause_accuracy([], [{"contract_id": "ctr-001", "version": 1}])
    assert score.passed is False
    assert any("not extracted" in line for line in score.detail)
