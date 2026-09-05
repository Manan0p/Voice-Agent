"""Asterisk Voice Pipeline Runner coordinating ARI channel events and Pipecat voice pipeline tasks."""

import asyncio
from typing import Any

from pipecat.pipeline.task import PipelineTask

from apps.agent.telephony.asterisk_ari import AsteriskARIClient
from apps.agent.telephony.asterisk_bridge import AsteriskMediaBridge
from apps.agent.telephony.state_machine import CallState, TelephonyCallSession
from apps.agent.voice.pipeline import VoicePipelineBuilder
from packages.schemas.asterisk import (
    ChannelHangupRequestEvent,
    StasisEndEvent,
    StasisStartEvent,
)
from packages.shared.logging import get_logger

logger = get_logger("apps.agent.telephony.asterisk_pipeline")


class AsteriskVoicePipelineRunner:
    """Coordinates Asterisk ARI call lifecycles with Pipecat voice pipelines."""

    def __init__(
        self,
        ari_client: AsteriskARIClient,
        pipeline_builder: VoicePipelineBuilder | None = None,
        auto_answer: bool = True,
    ) -> None:
        self.ari_client = ari_client
        self.pipeline_builder = pipeline_builder or VoicePipelineBuilder()
        self.auto_answer = auto_answer

        # Active session mappings: channel_id -> session data
        self.active_sessions: dict[str, TelephonyCallSession] = {}
        self.active_bridges: dict[str, AsteriskMediaBridge] = {}
        self.active_tasks: dict[str, tuple[PipelineTask, asyncio.Task[None]]] = {}

        # Register event handlers
        self.ari_client.on("StasisStart", self.on_stasis_start)
        self.ari_client.on("StasisEnd", self.on_stasis_end)
        self.ari_client.on("ChannelHangupRequest", self.on_hangup_request)

    async def on_stasis_start(self, event: StasisStartEvent) -> None:
        """Handle new incoming call entering Stasis application."""
        from apps.agent.telephony.trunk import SIPHeaderParser

        channel = event.channel
        channel_id = channel.id

        # Extract arguments passed from Asterisk Dialplan
        args = event.args or []
        caller_arg = channel.caller.number
        if len(args) > 0 and args[0]:
            candidate = SIPHeaderParser.normalize_phone_number(args[0])
            if candidate != "unknown":
                caller_arg = candidate

        diversion_arg = args[1] if len(args) > 1 and args[1] else None
        pai_arg = args[2] if len(args) > 2 and args[2] else None
        did_arg = args[3] if len(args) > 3 and args[3] else None

        resolved = SIPHeaderParser.resolve_call(
            caller_id_num=caller_arg,
            diversion_header=diversion_arg,
            pai_header=pai_arg,
            dialed_did=did_arg,
        )

        logger.info(
            "Asterisk StasisStart: Channel=%s, ResolvedCaller=%s, Forwarded=%s",
            channel_id,
            resolved.caller_number,
            resolved.is_forwarded,
        )

        # 1. Initialize Call Session with resolved caller identity
        session = TelephonyCallSession(
            call_sid=channel_id,
            phone_number=resolved.caller_number,
        )
        self.active_sessions[channel_id] = session

        # 2. Answer Channel if configured
        if self.auto_answer:
            answered = await self.ari_client.answer_channel(channel_id)
            if answered:
                session.set_connected(stream_sid=channel_id)

        # 3. Create Media Bridge and Pipeline
        bridge = AsteriskMediaBridge(channel_id=channel_id, audio_format="slin16")
        self.active_bridges[channel_id] = bridge

        # Build processors with bridge output
        processors = [
            bridge.input_processor,
            *self.pipeline_builder.build_processors(output_processor=bridge.output_processor),
        ]

        task = self.pipeline_builder.build_pipeline_task(processors=processors)
        loop_task = asyncio.create_task(self._run_pipeline_task(channel_id, task))
        self.active_tasks[channel_id] = (task, loop_task)

        logger.info("Voice pipeline initialized and attached for channel %s", channel_id)

    async def _run_pipeline_task(self, channel_id: str, task: PipelineTask) -> None:
        """Run the Pipecat pipeline task until completion or cancellation."""
        from pipecat.pipeline.runner import PipelineRunner

        runner = PipelineRunner()
        try:
            await runner.run(task)
        except asyncio.CancelledError:
            logger.info("Pipeline task for channel %s cancelled.", channel_id)
        except Exception as exc:
            logger.error(
                "Error running voice pipeline for channel %s: %s",
                channel_id,
                exc,
                exc_info=True,
            )

    async def on_stasis_end(self, event: StasisEndEvent) -> None:
        """Handle call leaving Stasis application."""
        channel_id = event.channel.id
        logger.info("Asterisk StasisEnd for channel %s", channel_id)
        await self._cleanup_channel(channel_id)

    async def on_hangup_request(self, event: ChannelHangupRequestEvent) -> None:
        """Handle hangup requested on channel."""
        channel_id = event.channel.id
        logger.info(
            "Asterisk ChannelHangupRequest for channel %s (cause=%s)",
            channel_id,
            event.cause,
        )
        await self._cleanup_channel(channel_id)

    async def _cleanup_channel(self, channel_id: str) -> None:
        """Cancel pipeline task and release bridge resources for channel."""
        session = self.active_sessions.pop(channel_id, None)
        if session:
            session.state = CallState.COMPLETED
            session.end_time = None

        bridge = self.active_bridges.pop(channel_id, None)
        if bridge:
            bridge.handle_barge_in()

        task_entry = self.active_tasks.pop(channel_id, None)
        if task_entry:
            task, loop_task = task_entry
            await task.cancel()
            if not loop_task.done():
                loop_task.cancel()
                try:
                    await loop_task
                except asyncio.CancelledError:
                    pass

        logger.info("Cleaned up session and pipeline for channel %s", channel_id)

    async def push_inbound_audio(self, channel_id: str, audio_bytes: bytes) -> bool:
        """Push incoming audio frame to channel pipeline."""
        bridge = self.active_bridges.get(channel_id)
        if not bridge:
            return False
        await bridge.receive_inbound_audio(audio_bytes)
        return True

    async def pop_outbound_audio(self, channel_id: str, timeout: float = 0.05) -> bytes | None:
        """Retrieve synthesized output frame for channel playback."""
        bridge = self.active_bridges.get(channel_id)
        if not bridge:
            return None
        return await bridge.get_outbound_audio_chunk(timeout=timeout)

    def get_session_status(self, channel_id: str) -> dict[str, Any] | None:
        """Get status of an active session."""
        session = self.active_sessions.get(channel_id)
        bridge = self.active_bridges.get(channel_id)
        if not session:
            return None
        return {
            "channel_id": channel_id,
            "state": session.state.value,
            "caller_phone": session.phone_number,
            "bridge": bridge.get_status() if bridge else None,
        }
