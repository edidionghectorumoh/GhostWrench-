"""
Ghostwrench AFE — Chainlit Web UI

Entry point for the Chainlit-based chat interface. Handles text messages,
image uploads, workflow phase visualization, escalation prompts, voice
guidance, session persistence, and the guided demo mode.
"""

import uuid
import asyncio
import logging
from typing import Dict, Any, Optional

import chainlit as cl

from config import WEAVIATE_URL, ENABLE_VALIDATION
from src.orchestration.OrchestrationLayer import OrchestrationLayer
from src.models.agents import (
    FieldRequest,
    RequestType,
    FieldResponse,
)
from src.models.workflow import WorkflowPhase

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

SUPPORTED_IMAGE_FORMATS = {"image/jpeg", "image/png", "image/bmp", "image/tiff"}

# In-memory session store (swap for Redis / DynamoDB in production)
SESSION_STORE: Dict[str, Any] = {}
_session_locks: Dict[str, asyncio.Lock] = {}

PHASE_LABELS = {
    WorkflowPhase.INTAKE: "📋 INTAKE",
    WorkflowPhase.DIAGNOSIS: "🔍 DIAGNOSIS",
    WorkflowPhase.PROCUREMENT: "🛒 PROCUREMENT",
    WorkflowPhase.GUIDANCE: "🔧 GUIDANCE",
    WorkflowPhase.COMPLETION: "✅ COMPLETION",
}


# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_session_lock(session_id: str) -> asyncio.Lock:
    """Return a per-session asyncio lock for thread-safe writes."""
    if session_id not in _session_locks:
        _session_locks[session_id] = asyncio.Lock()
    return _session_locks[session_id]


async def save_session(session_id: str, workflow_state: Any) -> None:
    """Persist workflow state to the in-memory store."""
    lock = _get_session_lock(session_id)
    async with lock:
        SESSION_STORE[session_id] = workflow_state


async def load_session(session_id: str) -> Optional[Any]:
    """Load workflow state from the in-memory store."""
    return SESSION_STORE.get(session_id)


def format_phase_summary(phase: WorkflowPhase, response: FieldResponse) -> str:
    """Build a human-readable summary for a completed workflow phase."""
    data = response.data or {}

    if phase == WorkflowPhase.DIAGNOSIS and response.diagnosis:
        diag = response.diagnosis
        return (
            f"**Issue:** {diag.issue_type.value}  \n"
            f"**Severity:** {diag.severity.value}  \n"
            f"**Confidence:** {diag.confidence:.0%}  \n"
            f"**Root cause:** {diag.root_cause}  \n"
            f"**Actions:** {', '.join(a.description for a in diag.recommended_actions)}"
        )

    if phase == WorkflowPhase.PROCUREMENT:
        parts = data.get("parts_count", "?")
        cost = data.get("total_cost", "?")
        delivery = data.get("estimated_delivery_date", "TBD")
        return (
            f"**Parts:** {parts}  \n"
            f"**Total cost:** ${cost}  \n"
            f"**Est. delivery:** {delivery}"
        )

    return response.message or "Phase complete."


# ── Chainlit lifecycle ────────────────────────────────────────────────────────


@cl.on_chat_start
async def on_chat_start():
    """Initialize a new Ghostwrench session or resume an existing one."""
    # Check for a reconnecting session (Chainlit passes session id on reconnect)
    existing_id = cl.user_session.get("session_id")
    restored = False

    if existing_id:
        saved_state = await load_session(existing_id)
        if saved_state:
            try:
                orchestrator = OrchestrationLayer(enable_validation=ENABLE_VALIDATION)
                orchestrator.sessions[existing_id] = saved_state
                cl.user_session.set("orchestrator", orchestrator)
                restored = True

                phase_label = PHASE_LABELS.get(saved_state.current_phase, saved_state.current_phase.value)
                await cl.Message(
                    content=f"Welcome back. Your session has been restored — currently in **{phase_label}** phase."
                ).send()

                # Re-display pending escalations
                if saved_state.has_unresolved_escalations():
                    await cl.Message(content="⚠️ You have unresolved escalations:").send()
                    for esc in saved_state.escalations:
                        if not esc.is_resolved():
                            await handle_escalation(
                                {"escalation_id": esc.escalation_id, "escalation_type": esc.escalation_type.value, "reason": esc.reason},
                                existing_id,
                                orchestrator,
                            )
            except Exception:
                logger.exception("Failed to restore session")
                restored = False

    if not restored:
        session_id = str(uuid.uuid4())

        try:
            orchestrator = OrchestrationLayer(enable_validation=ENABLE_VALIDATION)
        except Exception:
            logger.exception("Failed to initialize OrchestrationLayer")
            orchestrator = OrchestrationLayer(enable_validation=False)

        cl.user_session.set("session_id", session_id)
        cl.user_session.set("orchestrator", orchestrator)

        await cl.Message(
            content=(
                "Welcome to **Ghostwrench AFE**. "
                "Describe your issue or upload an equipment photo to get started.\n\n"
                "_Type **demo** to run a guided walkthrough of all five workflow phases._"
            )
        ).send()


@cl.on_message
async def on_message(message: cl.Message):
    """Route incoming text (and optional image attachments) to the orchestration pipeline."""
    session_id: str = cl.user_session.get("session_id")
    orchestrator: OrchestrationLayer = cl.user_session.get("orchestrator")

    # ── Demo mode shortcut ────────────────────────────────────────────────
    if message.content.strip().lower() == "demo":
        await _run_demo(session_id, orchestrator)
        return

    try:
        # ── Build FieldRequest ────────────────────────────────────────────
        image_bytes = None

        if message.elements:
            for elem in message.elements:
                mime = getattr(elem, "mime", None) or ""
                if mime not in SUPPORTED_IMAGE_FORMATS:
                    await cl.Message(
                        content=(
                            f"⚠️ Unsupported image format: `{mime}`. "
                            f"Supported formats: JPEG, PNG, BMP, TIFF."
                        )
                    ).send()
                    return

                image_bytes = await elem.read() if asyncio.iscoroutinefunction(getattr(elem, "read", None)) else elem.content

        field_request = FieldRequest(
            session_id=session_id,
            technician_id="technician-1",
            site_id="site-1",
            request_type=RequestType.DIAGNOSIS,
            # image_data requires full ImageData with resolution/geo/metadata;
            # raw bytes are stored in the session for the diagnosis agent to consume.
        )

        # Stash raw image bytes in the user session for downstream agents
        if image_bytes:
            cl.user_session.set("pending_image", image_bytes)

        # ── Process through orchestration ─────────────────────────────────
        response: FieldResponse = orchestrator.process_field_request(field_request)

        # ── Display response ──────────────────────────────────────────────
        await cl.Message(content=response.message or "Processing complete.").send()

        # Render annotated image if present
        if response.diagnosis and hasattr(response.diagnosis, "visual_evidence"):
            ve = response.diagnosis.visual_evidence
            if ve and ve.annotated_image:
                img_el = cl.Image(content=ve.annotated_image, name="annotated", display="inline")
                await cl.Message(content="Annotated diagnosis image:", elements=[img_el]).send()

        # Persist session state
        await save_session(session_id, orchestrator.sessions.get(session_id))

    except Exception:
        logger.exception("Unhandled error in on_message")
        await cl.Message(
            content="Something went wrong while processing your request. Please try again."
        ).send()


# ── Escalation handling ───────────────────────────────────────────────────────

ESCALATION_TIMEOUT_SECONDS = 300  # 5 minutes


async def handle_escalation(escalation: dict, session_id: str, orchestrator: OrchestrationLayer):
    """
    Present an escalation prompt to the user and forward their response.

    Supports safety, budget, and confidence escalation types.
    """
    esc_type = escalation.get("escalation_type", "unknown")
    esc_id = escalation.get("escalation_id", "")

    if esc_type == "safety":
        prompt_text = (
            "⚠️ **Safety Escalation**\n\n"
            f"**Violation:** {escalation.get('reason', 'N/A')}\n"
            f"**Precautions:** {escalation.get('precautions', 'N/A')}\n"
            f"**Required PPE:** {escalation.get('required_ppe', 'N/A')}\n\n"
            "Please acknowledge to continue."
        )
    elif esc_type == "budget":
        prompt_text = (
            "💰 **Budget Escalation**\n\n"
            f"**Total cost:** ${escalation.get('total_cost', '?')}\n"
            f"**Budget limit:** ${escalation.get('budget_limit', '?')}\n"
            f"**Approval level:** {escalation.get('approval_level', 'N/A')}\n\n"
            "Reply **approve**, **reject**, or **alternatives**."
        )
    else:
        # confidence / generic
        prompt_text = (
            "🔎 **Confidence Escalation**\n\n"
            f"**Details:** {escalation.get('reason', 'N/A')}\n"
            f"**Confidence:** {escalation.get('confidence', '?')}\n\n"
            "Reply **confirm**, **reject**, or **re-diagnose**."
        )

    res = await cl.AskUserMessage(content=prompt_text, timeout=ESCALATION_TIMEOUT_SECONDS).send()

    if res:
        orchestrator.resolve_escalation(esc_id, resolution_notes=res.get("output", res.get("content", "")))
    else:
        await cl.Message(content="⏰ Escalation timed out. Please respond to continue.").send()


# ── Workflow phase visualization ──────────────────────────────────────────────


async def handle_phase_step(phase: WorkflowPhase, coro):
    """
    Wrap a workflow phase execution inside a Chainlit Step for visual tracking.

    Args:
        phase: The workflow phase being executed.
        coro: An awaitable that runs the phase logic and returns a FieldResponse.

    Returns:
        The FieldResponse produced by *coro*.
    """
    label = PHASE_LABELS.get(phase, phase.value.upper())
    async with cl.Step(name=label) as step:
        step.output = "Processing…"
        response: FieldResponse = await coro
        step.output = format_phase_summary(phase, response)
    return response


async def stream_status(messages: list[str], delay: float = 0.6):
    """Send a sequence of short status messages with a small delay between each."""
    for msg in messages:
        await cl.Message(content=msg).send()
        await asyncio.sleep(delay)


# ── Demo mode ─────────────────────────────────────────────────────────────────

DEMO_PHASE_ANNOTATIONS = {
    WorkflowPhase.INTAKE: "📋 **INTAKE** — Capturing field request",
    WorkflowPhase.DIAGNOSIS: "🔍 **DiagnosisAgent** powered by *Amazon Nova 2 Lite*",
    WorkflowPhase.PROCUREMENT: "🛒 **ActionAgent** powered by *Amazon Nova Act* (UI Automation)",
    WorkflowPhase.GUIDANCE: "🔧 **GuidanceAgent** powered by *Amazon Nova 2 Sonic* (Voice AI)",
    WorkflowPhase.COMPLETION: "✅ **Workflow complete** — validated by *Claude 3.5 Sonnet*",
}


async def _run_demo(session_id: str, orchestrator: OrchestrationLayer):
    """Execute the guided demo flow through all five phases."""
    await cl.Message(content="🎬 Starting Ghostwrench AFE demo walkthrough…").send()

    demo_request = FieldRequest(
        session_id=session_id,
        technician_id="demo-tech-001",
        site_id="demo-site-001",
        request_type=RequestType.DIAGNOSIS,
    )

    for phase in WorkflowPhase:
        annotation = DEMO_PHASE_ANNOTATIONS.get(phase, "")
        if annotation:
            await cl.Message(content=annotation).send()

        try:
            response = orchestrator.process_field_request(demo_request)
            summary = format_phase_summary(phase, response)
            await cl.Message(content=summary).send()
        except Exception:
            logger.exception(f"Demo phase {phase.value} failed")
            await cl.Message(content=f"⚠️ {phase.value} phase encountered an error.").send()

    # Summary card
    await cl.Message(
        content=(
            "---\n"
            "### 🏆 Ghostwrench AFE — Demo Summary\n\n"
            "**Amazon Nova models used:**\n"
            "- Nova 2 Lite — multimodal diagnosis & reasoning\n"
            "- Nova Act — agentic procurement & UI automation\n"
            "- Nova 2 Sonic — voice-guided repair instructions\n"
            "- Nova Multimodal Embeddings — unified RAG search\n"
            "- Claude 3.5 Sonnet — safety validation judge\n\n"
            "**Hackathon categories:** Agentic AI · Multimodal Understanding · Voice AI\n\n"
            "_#AmazonNova_"
        )
    ).send()


# ── Voice guidance ────────────────────────────────────────────────────────────

# Buffer for incoming audio chunks (keyed by session_id)
_audio_buffers: Dict[str, bytearray] = {}


@cl.on_audio_chunk
async def on_audio_chunk(chunk: cl.InputAudioChunk):
    """Accumulate audio chunks from the microphone widget."""
    session_id: str = cl.user_session.get("session_id")
    if session_id not in _audio_buffers:
        _audio_buffers[session_id] = bytearray()
    _audio_buffers[session_id].extend(chunk.data)


@cl.on_audio_end
async def on_audio_end():
    """Forward completed audio to GuidanceAgent and play back the response."""
    session_id: str = cl.user_session.get("session_id")
    orchestrator: OrchestrationLayer = cl.user_session.get("orchestrator")

    audio_bytes = bytes(_audio_buffers.pop(session_id, bytearray()))
    if not audio_bytes:
        await cl.Message(content="No audio received. Please try again.").send()
        return

    try:
        guidance_agent = orchestrator.guidance_agent
        voice_result = guidance_agent.process_voice_command(audio_bytes, session_id)

        # Display transcription
        transcription = voice_result.get("transcription", "")
        if transcription:
            await cl.Message(content=f"🎤 _{transcription}_").send()

        # Play audio response
        audio_response = voice_result.get("audio_response", b"")
        if audio_response and audio_response != b"[Synthesized audio data]":
            audio_el = cl.Audio(content=audio_response, name="response", mime="audio/wav")
            await cl.Message(content="🔊 Voice response:", elements=[audio_el]).send()

        # Display text response
        text_resp = voice_result.get("response", {}).get("text", "")
        if text_resp:
            await cl.Message(content=text_resp).send()

        # Handle escalation flag
        if voice_result.get("requires_human_escalation"):
            await cl.Message(
                content="🚨 **Human escalation required.** Voice guidance paused — please respond to the escalation prompt."
            ).send()

    except Exception:
        logger.exception("Error processing voice command")
        await cl.Message(content="Something went wrong processing your voice command.").send()
