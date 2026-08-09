"""
MediVoice — real-time voice intake agent.

Pipeline:
    Microphone audio --> Deepgram (STT) --> OpenAI GPT-4o-mini (LLM + tools)
        --> Cartesia (TTS) --> Speaker audio

Run with:
    python main.py dev
"""

from __future__ import annotations

import logging

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RoomInputOptions,
    WorkerOptions,
    cli,
)
from livekit.plugins import cartesia, deepgram, openai, silero

from prompts import INTAKE_AGENT_INSTRUCTIONS
from tools import SessionStore, build_tools

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("medivoice.agent")


# --------------------------------------------------------------------------
# Streaming / chunking configuration
# --------------------------------------------------------------------------
# These control how audio and text are "chunked" as they flow through the
# pipeline. Framework defaults are reasonable, but for a clinical intake
# call — where patients may pause to think, or need to interrupt with an
# urgent symptom — it's worth tuning explicitly rather than trusting
# defaults blindly.
#
#   LLM -> TTS chunking:
#     Tokens from the LLM are streamed and split into sentence-sized chunks
#     (via a sentence tokenizer, blingfire by default) before being sent to
#     Cartesia. Cartesia starts synthesizing and streaming audio back as
#     soon as the first sentence chunk arrives, rather than waiting for the
#     full reply. `preemptive_generation` goes a step further: it starts
#     the LLM call speculatively before the patient's turn is even fully
#     confirmed over, which shaves noticeable latency off back-and-forth
#     exchanges.
#
#   Mic audio -> STT chunking / turn-taking:
#     `min_endpointing_delay` / `max_endpointing_delay` control how long
#     the agent waits in silence before deciding the patient has finished
#     speaking. Too short, and it cuts patients off mid-thought; too long,
#     and the conversation feels sluggish. Intake calls involve patients
#     recalling medication names and dates, so we bias slightly longer
#     than chat-bot defaults.
#
#   Interruptions (barge-in):
#     `min_interruption_duration` / `min_interruption_words` set the bar
#     for what counts as a genuine interruption vs. a stray "mm-hmm" or
#     background noise. We keep the word threshold low so a patient who
#     urgently says "wait, it hurts more now" can cut Maya off immediately.
#
CHUNKING_CONFIG = dict(
    # --- LLM -> TTS streaming ---
    preemptive_generation=True,     # start generating before patient's turn is confirmed done

    # --- Turn-taking / endpointing (how audio silence is chunked into turns) ---
    min_endpointing_delay=0.4,      # min silence (s) before treating turn as complete
    max_endpointing_delay=6.0,      # cap wait time for a hesitant/slow patient

    # --- Interruption sensitivity (barge-in) ---
    allow_interruptions=True,
    min_interruption_duration=0.4,  # min speech duration (s) to count as a real interruption
    min_interruption_words=1,       # even a short urgent phrase can interrupt

    # --- False-interruption recovery ---
    # If the agent is interrupted but no real transcript follows (e.g. a
    # cough or noise), resume speaking from where it left off instead of
    # silently dropping the rest of the sentence.
    resume_false_interruption=True,
    false_interruption_timeout=1.0,
)


class IntakeAgent(Agent):
    """The clinical intake conversational agent."""

    def __init__(self, store: SessionStore) -> None:
        super().__init__(
            instructions=INTAKE_AGENT_INSTRUCTIONS,
            tools=build_tools(store),
        )


async def entrypoint(ctx: JobContext) -> None:
    """Called by the LiveKit worker for each new room/call."""

    await ctx.connect()
    logger.info("Connected to room: %s", ctx.room.name)

    store = SessionStore()

    session = AgentSession(
        # Speech-to-text
        stt=deepgram.STT(model="nova-2-medical", language="en"),

        # LLM — clinical reasoning + tool calling
        llm=openai.LLM(model="gpt-4o-mini", temperature=0.4),

        # Text-to-speech
        tts=cartesia.TTS(
            model="sonic-2",
            voice="79a125e8-cd45-4c13-8a67-188112f4dd22",  # calm, friendly voice
        ),

        # Voice activity detection — determines when the patient starts/stops talking
        vad=silero.VAD.load(),

        # Explicit streaming/turn-taking/interruption tuning — see
        # CHUNKING_CONFIG above for rationale on each value.
        **CHUNKING_CONFIG,
    )

    await session.start(
        agent=IntakeAgent(store),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            # Cancels the agent's own voice from the mic input (echo/barge-in)
            noise_cancellation=None,
        ),
    )

    # Greet the patient as soon as the call connects
    await session.generate_reply(
        instructions=(
            "Greet the patient warmly, introduce yourself as Maya from the "
            "clinic's intake line, and ask for their name, date of birth, "
            "and phone number to get started."
        )
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
