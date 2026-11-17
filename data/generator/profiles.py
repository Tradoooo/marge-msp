"""The fake MSP: client and contract *types* plus the shared service catalogue.

The twelve concrete clients live in :mod:`generator.profile_data`; the prose,
the PDF and ``expected/contract_fields.json`` all derive from these objects, so
a contract value is written exactly once (no duplication).

The contracts are written in **English** (legal form ``LTD``): they are shown
to the judges and to the video audience. The rest of the generated data (tickets,
billing, invoices) stays French — it is what a French MSP would have on disk —
and the code around it is English (docs/CONTRACT.md rule 10).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

MSP_LEGAL_NAME = "ATLANTIQUE SYSTEMS LTD"
MSP_BRAND = "Atlantique Systems"
MSP_ADDRESS = "12 Shipyard Street, 44000 Nantes"

ACCOUNT_MANAGERS = ("am-01", "am-02", "am-03", "am-04")

CATALOGUE_INCLUDED = (
    "24/7 infrastructure monitoring",
    "Data backup and restoration",
    "Operating system patch management",
    "Infrastructure incident management",
    "Access and account management",
    "AWS cost optimisation",
)

CATALOGUE_EXCLUDED = (
    "application development and modification of the Client's code",
    "training of the Client's teams",
    "purchase of hardware and third-party licences",
    "application migration projects",
    "application security audits",
)

VAGUE_EXCLUSION = "evolving maintenance whose scale exceeds what a reasonable routine intervention covers"
"""The deliberately ambiguous exclusion of c-007 (spec 19.1).

"reasonable" makes the boundary impossible to apply, which is exactly the
situation the classifier must report as UNCERTAIN (spec 13.2).
"""


@dataclass(frozen=True, slots=True)
class SlaSpec:
    """One Annex B service level commitment: an object and a delay."""

    subject: str
    target: str


@dataclass(frozen=True, slots=True)
class ContractSpec:
    """Every Annex B field of one contract version, before rendering."""

    contract_id: str
    client_id: str
    version: int
    customer_name: str
    start_date: date
    end_date: date
    renewal_terms: str
    termination_notice: str
    monthly_subscription: Decimal
    included_hours_per_month: Decimal | None
    extra_hour_rate: Decimal
    services_included: tuple[str, ...]
    exclusions: tuple[str, ...]
    service_hours: str
    sla_commitments: tuple[SlaSpec, ...]
    penalties: str
    indexation_clause: str
    covered_accounts_or_resources: int
    style: str
    currency: str = "EUR"
    status: str = "VALIDATED"
    ambiguous_clause: bool = False
    amendment_of: int | None = None
    amendment_effective: date | None = None
    amendment_reason: str = ""

    @property
    def key(self) -> str:
        """``ctr-003-v1`` — the key of ``expected/contract_fields.json``."""
        return f"{self.contract_id}-v{self.version}"

    @property
    def effective_from(self) -> date:
        """The date this version starts to apply (a v2 amends mid-contract)."""
        if self.version == 1 or self.amendment_effective is None:
            return self.start_date
        return self.amendment_effective


@dataclass(frozen=True, slots=True)
class ClientProfile:
    """A client of the fake MSP plus the knobs that drive its six months."""

    client_id: str
    name: str
    sector: str
    account_manager_id: str
    onboarded_on: date
    managed_resource_count: int
    itsm_alias: str
    billing_alias: str
    invoice_alias: str
    contract: ContractSpec
    monthly_volume: int
    monthly_hours: tuple[Decimal, ...]
    level_mix: tuple[Decimal, Decimal, Decimal, Decimal]
    out_of_scope_share: Decimal
    aws_costs_usd: tuple[Decimal, ...]
    aws_markup: Decimal
    penalties: tuple[tuple[str, Decimal, str], ...]
    extra_hours: tuple[tuple[str, Decimal, Decimal], ...]
    projects: tuple[tuple[str, Decimal], ...]
    amendment: ContractSpec | None = None
    ambiguous_share: Decimal = Decimal("0")
    poor_coverage_month: str | None = None

    @property
    def contracts(self) -> tuple[ContractSpec, ...]:
        if self.amendment is None:
            return (self.contract,)
        return (self.contract, self.amendment)

    @property
    def unvalidated(self) -> bool:
        return self.contract.status != "VALIDATED"

    @property
    def aliases(self) -> tuple[tuple[str, str, str], ...]:
        """``(source, source_id, name_variant)`` — drives EF-REF-01."""
        slug = self.name.lower().replace(" ", "-")
        return (
            ("itsm", self.itsm_alias, self.name),
            ("billing", self.billing_alias, f"{slug}-prod"),
            ("contract", self.contract.contract_id, self.contract.customer_name),
            ("invoice", self.invoice_alias, self.contract.customer_name.title()),
        )


def days(values: tuple[str, ...]) -> tuple[Decimal, ...]:
    """Turn a tuple of decimal strings into :class:`Decimal` amounts."""
    return tuple(Decimal(value) for value in values)


def mix(n1: str, n2: str, n3: str, architect: str) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Level weights, in the N1 / N2 / N3 / ARCHITECT order."""
    return (Decimal(n1), Decimal(n2), Decimal(n3), Decimal(architect))


SLA_STANDARD_247 = (
    SlaSpec("Take-over of a critical incident", "30 minutes, 24/7"),
    SlaSpec("Availability of the supervised platform", "99.5% per month"),
    SlaSpec("Restoration of a backup", "4 business hours"),
)

SLA_STANDARD_OUVRE = (
    SlaSpec("Take-over of a blocking incident", "2 business hours"),
    SlaSpec("Availability of the supervised platform", "99.0% per month"),
    SlaSpec("Restoration of a backup", "8 business hours"),
)

PENALTY_STANDARD = (
    "2 % of the monthly subscription for each critical incident taken over beyond the committed "
    "delay, capped at 15 % of the monthly subscription."
)

INDEXATION_STANDARD = (
    "Annual price review on 1 January, on presentation of the Syntec index, within a limit of 3 % per year."
)
