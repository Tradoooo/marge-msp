"""Annex B field plan: what must be read out of a contract (spec 9.2).

The field plan is the single source of truth shared by the Bedrock Data
Automation job, the local deterministic extractor and the evaluation harness.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from ..domain import ContractFields, SlaCommitment

AMOUNT_NOISE = re.compile(
    r"(?i)(eur|usd|gbp|chf|€|\$|ht|excl\.?\s*vat|excl\.?\s*tax|vat|tax|heures?|hours?|%)"
)
"""Words that never carry a digit: currencies, tax markers, units."""

FIELD_PLAN: tuple[str, ...] = (
    "customer_name",
    "start_date",
    "end_date",
    "renewal_terms",
    "termination_notice",
    "monthly_subscription",
    "currency",
    "included_hours_per_month",
    "extra_hour_rate",
    "services_included",
    "exclusions",
    "service_hours",
    "sla_commitments",
    "penalties",
    "indexation_clause",
    "covered_accounts_or_resources",
)

MONEY_FIELDS = ("monthly_subscription", "extra_hour_rate")
DATE_FIELDS = ("start_date", "end_date")
NUMBER_FIELDS = ("included_hours_per_month", "covered_accounts_or_resources")
LIST_FIELDS = ("services_included", "exclusions")


@dataclass(frozen=True, slots=True)
class FieldPlanEntry:
    """One field of the plan, with the hint given to the extractor."""

    name: str
    kind: str
    hint: str


FIELD_HINTS: tuple[FieldPlanEntry, ...] = (
    FieldPlanEntry("customer_name", "text", "Legal name of the client"),
    FieldPlanEntry("start_date", "date", "Effective date of the contract"),
    FieldPlanEntry("end_date", "date", "End date"),
    FieldPlanEntry("renewal_terms", "text", "Renewal terms (automatic or not, duration)"),
    FieldPlanEntry("termination_notice", "text", "Termination notice"),
    FieldPlanEntry("monthly_subscription", "money", "Monthly subscription excluding tax"),
    FieldPlanEntry("currency", "text", "Currency of the contract"),
    FieldPlanEntry("included_hours_per_month", "number", "Included hours per month"),
    FieldPlanEntry("extra_hour_rate", "money", "Hourly rate beyond the included hours"),
    FieldPlanEntry("services_included", "list", "List of the included services"),
    FieldPlanEntry("exclusions", "list", "List of the exclusions"),
    FieldPlanEntry("service_hours", "text", "Service windows"),
    FieldPlanEntry("sla_commitments", "list", "Service level commitments"),
    FieldPlanEntry("penalties", "text", "How the penalties are computed"),
    FieldPlanEntry("indexation_clause", "text", "Price indexation clause"),
    FieldPlanEntry("covered_accounts_or_resources", "number", "Covered accounts or resources"),
)


BLUEPRINT_CLASS = "ManagedServicesContract"
BLUEPRINT_DESCRIPTION = (
    "A managed services contract between an IT services provider (the MSP) and "
    "its client. It states the monthly subscription, the hours included, the "
    "hourly rate beyond the quota, the services covered, the exclusions that "
    "delimit the scope, the service level commitments and the renewal terms."
)

# Le schéma d'un blueprint Bedrock Data Automation est un document de type
# JSON-Schema : une `class`, une `description`, et `properties` qui associent un
# nom de champ en UPPER_SNAKE à {type, inferenceType, instruction}. Format lu
# depuis le blueprint public `bedrock-data-automation-public-invoice` le
# 2026-11-11 : la charge `{"fields": {...}}` est refusée par l'API avec
# « Request has invalid blueprint schema ». Les dates et les montants restent
# des chaînes, converties par ce module : aucun chiffre n'est interprété par le
# modèle (ENF-IA-01).
_BDA_TYPES = {"text": "string", "date": "string", "money": "string", "number": "number", "list": "array"}


def blueprint_schema() -> dict[str, Any]:
    """The Annex B field plan as a Bedrock Data Automation blueprint schema."""
    properties: dict[str, Any] = {}
    for entry in FIELD_HINTS:
        field_type = _BDA_TYPES[entry.kind]
        spec: dict[str, Any] = {
            "type": field_type,
            "inferenceType": "explicit",
            "instruction": entry.hint,
        }
        if field_type == "array":
            spec["items"] = {"type": "string"}
        properties[entry.name.upper()] = spec
    return {"class": BLUEPRINT_CLASS, "description": BLUEPRINT_DESCRIPTION, "properties": properties}


def field_plan_payload() -> dict[str, Any]:
    """Alias kept for the callers written before the schema was corrected."""
    return blueprint_schema()


def parse_money(raw: object) -> Decimal:
    """Parse ``EUR 4,600.00`` / ``4 000,00 €`` / ``4000.00`` into a Decimal.

    The last separator written is the decimal one: ``4,600.00`` and
    ``4 600,00`` both give ``4600.00``.
    """
    text = AMOUNT_NOISE.sub(" ", str(raw or "0"))
    cleaned = "".join(ch for ch in text if ch.isdigit() or ch in ".,-")
    cleaned = _decimal_separator(cleaned)
    try:
        return Decimal(cleaned or "0")
    except InvalidOperation:
        return Decimal("0")


def _decimal_separator(text: str) -> str:
    """One decimal separator, thousands removed."""
    if "," in text and "." in text:
        if text.rfind(".") > text.rfind(","):
            return text.replace(",", "")
        return text.replace(".", "").replace(",", ".")
    if "," in text:
        return text.replace(",", ".")
    return text


MONTHS: dict[str, int] = {
    "january": 1,
    "janvier": 1,
    "february": 2,
    "fevrier": 2,
    "février": 2,
    "march": 3,
    "mars": 3,
    "april": 4,
    "avril": 4,
    "may": 5,
    "mai": 5,
    "june": 6,
    "juin": 6,
    "july": 7,
    "juillet": 7,
    "august": 8,
    "aout": 8,
    "août": 8,
    "september": 9,
    "septembre": 9,
    "october": 10,
    "octobre": 10,
    "november": 11,
    "novembre": 11,
    "december": 12,
    "decembre": 12,
    "décembre": 12,
}


def parse_date(raw: object) -> date | None:
    """Parse ``31/12/2026``, ``2026-12-31`` or ``31 December 2026``."""
    import re

    text = str(raw or "").strip()
    if not text:
        return None
    iso = re.match(r"(\d{4})-(\d{2})-(\d{2})", text)
    if iso:
        return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
    french = re.match(r"(\d{1,2})[/.](\d{1,2})[/.](\d{4})", text)
    if french:
        return date(int(french.group(3)), int(french.group(2)), int(french.group(1)))
    words = re.match(r"(\d{1,2})\s+([A-Za-zÀ-ÿ]+)\s+(\d{4})", text)
    if words:
        month = MONTHS.get(words.group(2).lower())
        if month:
            return date(int(words.group(3)), month, int(words.group(1)))
    return None


def parse_list(raw: object) -> tuple[str, ...]:
    """A list field: JSON list, bullet list or a single line."""
    if isinstance(raw, (list, tuple)):
        return tuple(str(item).strip() for item in raw if str(item).strip())
    lines = [line.strip(" -•\t") for line in str(raw or "").splitlines()]
    return tuple(line for line in lines if line)


def to_contract_fields(payload: dict[str, Any]) -> ContractFields:
    """Build ``ContractFields`` from an extractor payload (Annex B)."""
    sla_raw = payload.get("sla_commitments") or []
    sla = tuple(
        SlaCommitment(
            subject=str(item.get("subject", "")),
            target=str(item.get("target", "")),
            penalty_rule=str(item.get("penalty_rule", "")),
        )
        if isinstance(item, dict)
        else SlaCommitment(subject=str(item), target="")
        for item in sla_raw
    )
    hours = payload.get("included_hours_per_month")
    covered = payload.get("covered_accounts_or_resources")
    fields = ContractFields(
        customer_name=str(payload.get("customer_name", "") or ""),
        start_date=parse_date(payload.get("start_date")),
        end_date=parse_date(payload.get("end_date")),
        renewal_terms=str(payload.get("renewal_terms", "") or ""),
        termination_notice=str(payload.get("termination_notice", "") or ""),
        monthly_subscription=parse_money(payload.get("monthly_subscription")),
        currency=str(payload.get("currency", "EUR") or "EUR"),
        included_hours_per_month=parse_money(hours) if hours not in (None, "") else None,
        extra_hour_rate=parse_money(payload.get("extra_hour_rate")),
        services_included=parse_list(payload.get("services_included")),
        exclusions=parse_list(payload.get("exclusions")),
        service_hours=str(payload.get("service_hours", "") or ""),
        sla_commitments=sla,
        penalties=str(payload.get("penalties", "") or ""),
        indexation_clause=str(payload.get("indexation_clause", "") or ""),
        covered_accounts_or_resources=int(parse_money(covered)) if covered not in (None, "") else None,
    )
    fields.normalise_amounts()
    return fields


def validate_fields(fields: ContractFields) -> list[str]:
    """Return the list of blocking problems (empty means usable)."""
    problems: list[str] = []
    if not fields.customer_name.strip():
        problems.append("customer_name is empty")
    if fields.start_date is None:
        problems.append("start_date is missing")
    if fields.end_date is None:
        problems.append("end_date is missing")
    if fields.monthly_subscription <= 0:
        problems.append("monthly_subscription must be positive")
    if not fields.services_included:
        problems.append("services_included is empty")
    if not fields.exclusions:
        problems.append("exclusions is empty: the classifier needs the boundary")
    return problems
