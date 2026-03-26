"""
Custom Hypothesis strategies for Ghostwrench Chainlit UI property-based tests.
"""

import struct
from hypothesis import strategies as st

from src.models.workflow import WorkflowPhase


# ── Text & message strategies ─────────────────────────────────────────────────

def text_messages():
    """Non-empty strings suitable for chat messages."""
    return st.text(min_size=1, max_size=500).filter(lambda s: s.strip())


# ── Image strategies ──────────────────────────────────────────────────────────

def _minimal_jpeg() -> bytes:
    """Return a minimal valid JPEG byte sequence (SOI + EOI markers)."""
    return b"\xff\xd8\xff\xe0" + b"\x00" * 20 + b"\xff\xd9"


def _minimal_png() -> bytes:
    """Return a minimal valid PNG byte sequence (signature + IHDR + IEND)."""
    sig = b"\x89PNG\r\n\x1a\n"
    # Minimal IHDR: 1x1, 8-bit RGB
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr_crc = b"\x00" * 4
    ihdr = struct.pack(">I", 13) + b"IHDR" + ihdr_data + ihdr_crc
    iend = struct.pack(">I", 0) + b"IEND" + b"\x00" * 4
    return sig + ihdr + iend


def image_bytes():
    """Valid JPEG or PNG byte sequences."""
    return st.sampled_from([_minimal_jpeg(), _minimal_png()])


def unsupported_mime_types():
    """MIME types NOT in the supported set."""
    return st.sampled_from([
        "image/gif", "image/webp", "image/svg+xml",
        "application/pdf", "text/plain", "video/mp4",
    ])


# ── Workflow strategies ───────────────────────────────────────────────────────

def workflow_phases():
    """Sample from WorkflowPhase enum."""
    return st.sampled_from(list(WorkflowPhase))


def workflow_states():
    """Generate minimal WorkflowState-like dicts for testing."""
    return st.fixed_dictionaries({
        "session_id": st.uuids().map(str),
        "current_phase": workflow_phases(),
        "technician_id": st.text(min_size=1, max_size=20),
        "site_id": st.text(min_size=1, max_size=20),
    })


# ── Agent result strategies ───────────────────────────────────────────────────

def diagnosis_results():
    """Generate diagnosis-result-like dicts."""
    return st.fixed_dictionaries({
        "issue_type": st.sampled_from(["hardware_defect", "electrical_malfunction", "network_failure"]),
        "severity": st.sampled_from(["critical", "high", "medium", "low"]),
        "confidence": st.floats(min_value=0.0, max_value=1.0),
        "root_cause": st.text(min_size=5, max_size=100),
        "recommended_actions": st.lists(st.text(min_size=3, max_size=50), min_size=1, max_size=3),
    })


def procurement_states():
    """Generate procurement-state-like dicts."""
    return st.fixed_dictionaries({
        "parts_count": st.integers(min_value=1, max_value=20),
        "total_cost": st.floats(min_value=0.01, max_value=100000.0, allow_nan=False),
        "estimated_delivery_date": st.sampled_from(["2026-04-01", "2026-04-15", "TBD"]),
    })


def escalation_data():
    """Generate escalation dicts for safety/budget/confidence types."""
    return st.one_of(
        st.fixed_dictionaries({
            "escalation_type": st.just("safety"),
            "escalation_id": st.uuids().map(str),
            "reason": st.text(min_size=5, max_size=100),
            "precautions": st.text(min_size=5, max_size=100),
            "required_ppe": st.text(min_size=3, max_size=50),
        }),
        st.fixed_dictionaries({
            "escalation_type": st.just("budget"),
            "escalation_id": st.uuids().map(str),
            "total_cost": st.floats(min_value=100, max_value=50000, allow_nan=False),
            "budget_limit": st.floats(min_value=100, max_value=50000, allow_nan=False),
            "approval_level": st.sampled_from(["supervisor", "manager", "director"]),
        }),
        st.fixed_dictionaries({
            "escalation_type": st.just("confidence"),
            "escalation_id": st.uuids().map(str),
            "reason": st.text(min_size=5, max_size=100),
            "confidence": st.floats(min_value=0.0, max_value=1.0),
        }),
    )


def guidance_steps():
    """Generate guidance-step-like dicts."""
    return st.fixed_dictionaries({
        "step_number": st.integers(min_value=1, max_value=20),
        "instruction": st.text(min_size=10, max_size=200),
        "safety_checks": st.lists(st.text(min_size=3, max_size=50), max_size=3),
        "expected_outcome": st.text(min_size=5, max_size=100),
    })


def voice_responses():
    """Generate voice-response-like dicts."""
    return st.fixed_dictionaries({
        "transcription": st.text(min_size=1, max_size=200),
        "audio_response": st.just(b"[audio]"),
        "requires_human_escalation": st.booleans(),
        "intent": st.sampled_from(["next_step", "repeat", "clarification", "emergency", "completion"]),
    })
