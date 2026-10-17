"""§5.2 Hazard gate — deterministic keyword/pattern check.

Hazard warnings are STATIC CURATED TEXT, clearly labeled "General safety notice, not from the manual".
For gas and refrigerant: never generate step-by-step procedures. Show cited passages + referral.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class HazardResult:
    is_hazard: bool
    category: str = ""  # "mains_voltage" | "gas" | "refrigerant" | "general"
    warning_text: str = ""
    block_generation: bool = False  # True for gas/refrigerant procedures


# ── Static curated warnings ────────────────────────────────────────────────────

_VOLTAGE_WARNING = (
    "⚠️  GENERAL SAFETY NOTICE (not from the manual)\n"
    "Working with mains voltage is dangerous and can cause serious injury or death. "
    "Always unplug the appliance or disconnect power at the breaker before any inspection "
    "or service. If you need to perform live-voltage tests, engage a licensed appliance "
    "repair technician. This system can show you the relevant manual passages, but cannot "
    "safely guide you through live-voltage procedures step by step."
)

_GAS_WARNING = (
    "⚠️  GENERAL SAFETY NOTICE (not from the manual)\n"
    "Gas appliance service must be performed by a licensed technician. "
    "Improper gas work can cause fire, explosion, or carbon monoxide poisoning. "
    "Do not attempt to repair gas connections, valves, or burners yourself. "
    "If you smell gas, leave the building immediately and call your gas supplier. "
    "The manual passages below are shown for reference only."
)

_REFRIGERANT_WARNING = (
    "⚠️  GENERAL SAFETY NOTICE (not from the manual)\n"
    "Refrigerant handling requires EPA Section 608 certification and specialized equipment. "
    "Improper refrigerant service is illegal and dangerous. "
    "Refer all refrigerant work to a certified HVAC/R technician. "
    "The manual passages below are shown for reference only."
)

_GENERAL_HAZARD_WARNING = (
    "⚠️  GENERAL SAFETY NOTICE (not from the manual)\n"
    "This question involves a potentially hazardous procedure. "
    "Always follow all safety precautions in the manufacturer manual. "
    "When in doubt, consult a licensed repair technician."
)


# ── Patterns (with synonyms and common misspellings) ──────────────────────────

_VOLTAGE_PATTERNS = re.compile(
    r"""
    \b(
        mains\s+voltage | live\s+wire | live\s+circuit | live\s+terminal |
        120v | 240v | 230v | 110v |
        high\s+voltage | lethal\s+voltage |
        shock | electrocution | electrocute |
        voltmeter\s+on\s+live | probe\s+(the\s+)?live |
        dont\s+unplug | without\s+unplugging | while\s+plugged\s+in |
        bypass\s+(the\s+)?capacitor | discharge\s+capacitor |
        capacitor\s+charge | stored\s+charge
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

_GAS_PATTERNS = re.compile(
    r"""
    \b(
        gas\s+line | gas\s+pipe | gas\s+valve | gas\s+leak | gas\s+connection |
        natural\s+gas | propane | gas\s+burner | gas\s+supply |
        relight\s+pilot | pilot\s+light | gas\s+pressure |
        smell\s+(of\s+)?gas | gas\s+smell |
        gaz | gaas   # common misspellings
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

_REFRIGERANT_PATTERNS = re.compile(
    r"""
    \b(
        refrigerant | r-?134a | r-?410a | r-?22 | freon | puron |
        recharge\s+(the\s+)?system | recharge\s+(the\s+)?ac |
        add\s+refrigerant | recover\s+refrigerant | evacuate\s+system |
        compressor\s+oil | refrigerant\s+leak | hvac\s+cert
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)


def check_hazard(symptom: str, question: str = "") -> HazardResult:
    """
    Check symptom and question for hazard patterns.
    Returns HazardResult. block_generation=True for gas/refrigerant procedure requests.
    """
    combined = f"{symptom} {question}".strip()

    if _GAS_PATTERNS.search(combined):
        return HazardResult(
            is_hazard=True,
            category="gas",
            warning_text=_GAS_WARNING,
            block_generation=True,
        )

    if _REFRIGERANT_PATTERNS.search(combined):
        return HazardResult(
            is_hazard=True,
            category="refrigerant",
            warning_text=_REFRIGERANT_WARNING,
            block_generation=True,
        )

    if _VOLTAGE_PATTERNS.search(combined):
        # If requesting to bypass ground/fuse or touch/tap live wires, block generation
        is_unsafe_tampering = bool(re.search(r"\b(bypass|without\s+unplugging|while\s+running|tap\s+directly)\b", combined, re.I))
        return HazardResult(
            is_hazard=True,
            category="mains_voltage",
            warning_text=_VOLTAGE_WARNING,
            block_generation=is_unsafe_tampering,
        )

    return HazardResult(is_hazard=False)
