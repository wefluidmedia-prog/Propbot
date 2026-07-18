import asyncio
import logging
import os
import boto3
from dotenv import load_dotenv

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.worker import PipelineWorker, PipelineParams
from pipecat.processors.aggregators.llm_context import LLMContext, LLMContextMessage
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair

from pipecat.services.aws.stt import AWSTranscribeSTTService
from pipecat.services.aws.llm import AWSBedrockLLMService
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.transports.network.fastapi_websocket import (
    FastAPIWebsocketTransport,
    FastAPIWebsocketParams,
)

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting Pipecat Hybrid Worker (AWS + ElevenLabs)...")
    
    # Ensure AWS SDK has credentials (from env or default profile)
    session = boto3.Session(region_name=os.getenv("AWS_REGION", "us-east-1"))
    
    # 1. Setup STT (AWS Transcribe)
    stt = AWSTranscribeSTTService(
        session=session,
        settings=AWSTranscribeSTTService.Settings(language="hi-IN")
    )

    # 2. Setup LLM (AWS Bedrock - Claude Haiku 4.5)
    llm = AWSBedrockLLMService(
        session=session,
        settings=AWSBedrockLLMService.Settings(model="us.anthropic.claude-haiku-4-5-20251001-v1:0")
    )

    # 3. Setup TTS (ElevenLabs with Emotion Tuning)
    tts = ElevenLabsTTSService(
        api_key=os.getenv("ELEVENLABS_API_KEY", ""),
        settings=ElevenLabsTTSService.Settings(
            voice=os.getenv("ELEVENLABS_VOICE_ID", "pFZP5JQG7iQjIQuC4Bku"),
            model="eleven_multilingual_v2",
            stability=float(os.getenv("ELEVENLABS_STABILITY", "0.5")),
            similarity_boost=float(os.getenv("ELEVENLABS_SIMILARITY", "0.75")),
            style=float(os.getenv("ELEVENLABS_STYLE", "0.0")),
            use_speaker_boost=True
        )
    )

    # 4. Transport (WebSocket for testing)
    transport = FastAPIWebsocketTransport(
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
        )
    )

    messages = [
        {"role": "system", "content": "You are Priya, a highly persuasive real estate negotiation assistant. Speak strictly in Hindi. Use conversational fillers like 'hmm' and 'achha' to sound human. Keep responses short and punchy."}
    ]

    context = LLMContext(messages=messages)
    context_aggregator = LLMContextAggregatorPair(context=context)

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )

    task = PipelineWorker(pipeline, params=PipelineParams(allow_interruptions=True))

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("New web client connected! Starting context loop.")
        await task.queue_frames([context_aggregator.user().get_context_frame()])

    runner = PipelineRunner()
    await runner.run(task)

if __name__ == "__main__":
    asyncio.run(main())
