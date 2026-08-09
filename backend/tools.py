"""
Clinical intake tool functions.

These are exposed to the LLM as callable "function tools" during the
conversation. Each call is logged into an in-memory session record that
is written out as a structured summary at the end of the call.

This module intentionally has NO database dependency — session state is
held in memory for the duration of the call. Swap `SessionStore` for a
real persistence layer (e.g. Supabase) when you're ready to add memory
across visits.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Optional

from livekit.agents import function_tool

logger = logging.getLogger("medivoice.tools")


# --------------------------------------------------------------------------
# In-memory session record
# --------------------------------------------------------------------------

@dataclass
class IntakeSession:
    patient_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    phone: Optional[str] = None

    chief_complaint: Optional[str] = None
    symptoms: list = field(default_factory=list)  # list[dict]

    urgency: str = "unset"  # low | medium | high | emergency
    urgency_reason: Optional[str] = None

    conditions: list = field(default_factory=list)
    medications: list = field(default_factory=list)
    allergies: list = field(default_factory=list)
    surgeries: list = field(default_factory=list)

    insurance_provider: Optional[str] = None
    insurance_member_id: Optional[str] = None
    insurance_group_number: Optional[str] = None

    appointment: Optional[dict] = None

    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


class SessionStore:
    """Holds the single active intake session for this call."""

    def __init__(self) -> None:
        self.session = IntakeSession()

    def reset(self) -> None:
        self.session = IntakeSession()


# --------------------------------------------------------------------------
# Tool factory
# --------------------------------------------------------------------------
# Tools are built as closures over a SessionStore instance so each LiveKit
# call/room gets its own isolated state without any globals.

def build_tools(store: SessionStore) -> list:
    """Return the list of function_tool-decorated callables for this session."""

    @function_tool()
    async def identify_patient(name: str, date_of_birth: str, phone: str) -> str:
        """Record the patient's identity at the start of the call.

        Args:
            name: Patient's full name.
            date_of_birth: Date of birth, e.g. '1990-04-12'.
            phone: Patient's phone number.
        """
        store.session.patient_name = name
        store.session.date_of_birth = date_of_birth
        store.session.phone = phone
        logger.info("identify_patient: %s / %s", name, date_of_birth)
        return f"Patient identified: {name}, DOB {date_of_birth}."

    @function_tool()
    async def record_symptoms(
        description: str,
        onset: str,
        severity: int,
        location: str = "",
        duration: str = "",
        aggravating_factors: str = "",
    ) -> str:
        """Record a symptom reported by the patient.

        Args:
            description: What the symptom is, in the patient's words.
            onset: When it started, e.g. 'three days ago'.
            severity: Severity on a 1-10 scale.
            location: Where on the body, if applicable.
            duration: How long each episode lasts, if applicable.
            aggravating_factors: What makes it worse, if mentioned.
        """
        severity = max(1, min(10, severity))
        entry = {
            "description": description,
            "onset": onset,
            "severity": severity,
            "location": location,
            "duration": duration,
            "aggravating_factors": aggravating_factors,
        }
        store.session.symptoms.append(entry)
        if not store.session.chief_complaint:
            store.session.chief_complaint = description
        logger.info("record_symptoms: %s", entry)
        return f"Symptom recorded: {description} (severity {severity}/10)."

    @function_tool()
    async def set_urgency_flag(level: str, reason: str) -> str:
        """Set the triage urgency level for this patient.

        Args:
            level: One of 'low', 'medium', 'high', 'emergency'.
            reason: Brief clinical reason for this level.
        """
        level = level.lower().strip()
        if level not in {"low", "medium", "high", "emergency"}:
            level = "medium"
        store.session.urgency = level
        store.session.urgency_reason = reason
        logger.warning("set_urgency_flag: %s -> %s", level, reason)
        return f"Urgency set to {level}: {reason}"

    @function_tool()
    async def update_medical_history(
        conditions: str = "",
        medications: str = "",
        allergies: str = "",
        surgeries: str = "",
    ) -> str:
        """Add to the patient's medical history. Pass comma-separated items.

        Args:
            conditions: Comma-separated known conditions to add.
            medications: Comma-separated current medications to add.
            allergies: Comma-separated known allergies to add.
            surgeries: Comma-separated past surgeries to add.
        """
        def _split(s: str) -> list[str]:
            return [x.strip() for x in s.split(",") if x.strip()]

        store.session.conditions.extend(_split(conditions))
        store.session.medications.extend(_split(medications))
        store.session.allergies.extend(_split(allergies))
        store.session.surgeries.extend(_split(surgeries))
        logger.info("update_medical_history updated")
        return "Medical history updated."

    @function_tool()
    async def record_insurance(provider: str, member_id: str, group_number: str = "") -> str:
        """Record the patient's insurance details.

        Args:
            provider: Insurance provider name.
            member_id: Member/policy ID.
            group_number: Group number, if provided.
        """
        store.session.insurance_provider = provider
        store.session.insurance_member_id = member_id
        store.session.insurance_group_number = group_number
        logger.info("record_insurance: %s", provider)
        return f"Insurance recorded: {provider}."

    @function_tool()
    async def book_appointment(preferred_doctor: str, preferred_time: str, notes: str = "") -> str:
        """Book a follow-up appointment based on the intake so far.

        Args:
            preferred_doctor: Doctor or specialty requested, if any.
            preferred_time: Patient's preferred date/time window.
            notes: Any extra scheduling notes.
        """
        store.session.appointment = {
            "preferred_doctor": preferred_doctor,
            "preferred_time": preferred_time,
            "notes": notes,
            "urgency_context": store.session.urgency,
        }
        logger.info("book_appointment: %s", store.session.appointment)
        return f"Appointment request logged for {preferred_time} with {preferred_doctor or 'any available provider'}."

    @function_tool()
    async def generate_intake_summary() -> str:
        """Generate the final structured clinical intake summary.

        Call this once, at the end of the conversation, after all other
        information has been collected.
        """
        summary = store.session.to_dict()
        logger.info("generate_intake_summary: %s", json.dumps(summary, default=str))
        # In production this would render a PDF and push it to a clinic
        # dashboard / EHR. Here we just return the structured JSON so the
        # agent can confirm completion to the patient.
        return (
            "Intake summary generated for "
            f"{summary.get('patient_name') or 'the patient'}. "
            f"Urgency: {summary.get('urgency')}. "
            f"Chief complaint: {summary.get('chief_complaint') or 'not specified'}."
        )

    return [
        identify_patient,
        record_symptoms,
        set_urgency_flag,
        update_medical_history,
        record_insurance,
        book_appointment,
        generate_intake_summary,
    ]
