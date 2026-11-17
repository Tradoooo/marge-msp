"""English prose of the contract sections (Annex B fields, in context).

Every section returns plain paragraphs; lists are rendered as ``-`` bullets.
Three phrasing variants exist so the twelve contracts do not read the same.
"""

from __future__ import annotations

from .common import english_date, english_hours, english_money
from .profiles import MSP_ADDRESS, MSP_LEGAL_NAME, ContractSpec

PARTIES = "parties"
OBJECT = "object"
DURATION = "duration"
RESOURCES = "resources"
PRICE = "price"
INCLUDED = "included"
EXCLUDED = "excluded"
SERVICE_HOURS = "service_hours"
SLA = "sla"
PENALTIES = "penalties"
INDEXATION = "indexation"
TERMINATION = "termination"

TITLES = {
    PARTIES: "Parties to the contract",
    OBJECT: "Purpose of the contract",
    DURATION: "Term and renewal",
    RESOURCES: "Covered accounts and resources",
    PRICE: "Financial terms",
    INCLUDED: "Included services",
    EXCLUDED: "Exclusions",
    SERVICE_HOURS: "Service windows",
    SLA: "Service level commitments",
    PENALTIES: "Penalties",
    INDEXATION: "Price indexation",
    TERMINATION: "Termination",
}


def _bullets(items: tuple[str, ...]) -> list[str]:
    return [f"- {item}" for item in items]


def parties(spec: ContractSpec) -> list[str]:
    return [
        "Between the undersigned:",
        f"{MSP_LEGAL_NAME}, whose registered office is at {MSP_ADDRESS}, "
        "registered with the Companies Registry, "
        'hereinafter the "Provider",',
        f'and {spec.customer_name}, hereinafter the "Client",',
        "the following has been agreed.",
    ]


def object_(spec: ContractSpec) -> list[str]:
    paragraphs = [
        "The Provider delivers the managed services described in this contract on behalf of the "
        "Client, under the service levels and the scope set out below."
    ]
    if spec.version > 1:
        paragraphs.insert(
            0,
            f"This amendment no.{spec.version - 1} modifies contract {spec.contract_id} with effect "
            f"from {english_date(spec.effective_from)}. Reason: {spec.amendment_reason}.",
        )
    return paragraphs


def duration(spec: ContractSpec, phrasing: int = 0) -> list[str]:
    start, end = english_date(spec.start_date), english_date(spec.end_date)
    notice = spec.termination_notice
    variants = (
        f"The contract takes effect on {start} and ends on {end}. "
        f"It is renewed on the following terms: {spec.renewal_terms.lower()}. "
        f"The termination notice is {notice}.",
        f"Term: from {start} to {end} inclusive. {spec.renewal_terms}. "
        f"Any termination is notified with {notice} of notice.",
        f"This contract is concluded for the period from {start} to {end}. "
        f"At its end, {spec.renewal_terms.lower()}. "
        f"Either party may end it with {notice} of notice.",
    )
    return [variants[phrasing % len(variants)]]


def resources(spec: ContractSpec) -> list[str]:
    return [
        f"The scope covers {spec.covered_accounts_or_resources} managed accounts or resources, "
        "whose list is kept up to date by the Provider and shared with the Client "
        "at every quarterly review."
    ]


def price(spec: ContractSpec, phrasing: int = 0) -> list[str]:
    amount = english_money(spec.monthly_subscription, spec.currency)
    rate = english_money(spec.extra_hour_rate, spec.currency)
    quota = (
        "an unlimited number of hours"
        if spec.included_hours_per_month is None
        else english_hours(spec.included_hours_per_month)
    )
    variants = (
        f"In return, the Client pays a monthly subscription of {amount} excluding VAT, "
        f"covering {quota} per month. Hours worked beyond that allowance are "
        f"billed at the out-of-package hourly rate of {rate}.",
        f"The monthly subscription is set at {amount} excluding VAT. It includes "
        f"{quota} per month. Any additional hour is billed at {rate}.",
        f"Financial terms: a monthly subscription of {amount} excluding VAT for {quota} "
        f"included every month; beyond that, the out-of-package hourly rate is {rate}.",
    )
    return [variants[phrasing % len(variants)]]


def included(spec: ContractSpec) -> list[str]:
    return ["The Provider delivers the following services:", *_bullets(spec.services_included)]


def excluded(spec: ContractSpec) -> list[str]:
    return ["The following are not covered by the contract scope:", *_bullets(spec.exclusions)]


def service_hours(spec: ContractSpec) -> list[str]:
    return [f"The services are delivered during the following windows: {spec.service_hours}."]


def sla(spec: ContractSpec) -> list[str]:
    items = tuple(f"{item.subject}: {item.target}" for item in spec.sla_commitments)
    return ["The Provider commits to the following service levels:", *_bullets(items)]


def penalties(spec: ContractSpec) -> list[str]:
    return [f"Penalties: {spec.penalties}"]


def indexation(spec: ContractSpec) -> list[str]:
    return [f"Price indexation clause: {spec.indexation_clause}"]


def termination(spec: ContractSpec) -> list[str]:
    return [
        f"The contract may be terminated by either party with {spec.termination_notice} of notice, "
        f"notified by registered letter with acknowledgement of receipt. "
        f"{spec.renewal_terms}. In case of a serious breach, termination takes effect "
        "thirty days after formal notice that has remained unanswered."
    ]


BUILDERS = {
    PARTIES: parties,
    OBJECT: object_,
    RESOURCES: resources,
    INCLUDED: included,
    EXCLUDED: excluded,
    SERVICE_HOURS: service_hours,
    SLA: sla,
    PENALTIES: penalties,
    INDEXATION: indexation,
    TERMINATION: termination,
}


def build_section(key: str, spec: ContractSpec, phrasing: int) -> list[str]:
    """Paragraphs of one section, phrasing-aware for price and duration."""
    if key == PRICE:
        return price(spec, phrasing)
    if key == DURATION:
        return duration(spec, phrasing)
    return BUILDERS[key](spec)
