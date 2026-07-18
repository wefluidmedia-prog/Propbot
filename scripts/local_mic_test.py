import asyncio
import logging
import os
import pyaudio
from dotenv import load_dotenv

from pipecat.pipeline.pipeline import Pipeline
from pipecat.workers.runner import WorkerRunner
from pipecat.pipeline.worker import PipelineWorker, PipelineParams
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.sarvam.tts import SarvamTTSService
from pipecat.transports.local.audio import LocalAudioTransport, LocalAudioTransportParams

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample rates by Sarvam model — v2 outputs 22050, v3 outputs 24000.
# PipelineParams defaults to 24000; mismatch causes garbled/fast audio on v2.
SARVAM_SAMPLE_RATES = {
    "bulbul:v2": 22050,
    "bulbul:v3-beta": 24000,
    "bulbul:v3": 24000,
}


def list_audio_devices():
    p = pyaudio.PyAudio()
    logger.info("=" * 60)
    logger.info("AVAILABLE AUDIO DEVICES:")
    logger.info("=" * 60)
    default_input = p.get_default_input_device_info()
    default_output = p.get_default_output_device_info()
    logger.info(f"  DEFAULT INPUT:  [{default_input['index']}] {default_input['name']}")
    logger.info(f"  DEFAULT OUTPUT: [{default_output['index']}] {default_output['name']}")
    logger.info("-" * 60)
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        direction = ""
        if info["maxInputChannels"] > 0:
            direction += " [IN]"
        if info["maxOutputChannels"] > 0:
            direction += " [OUT]"
        logger.info(f"  [{i}]{direction} {info['name']}  (rate={int(info['defaultSampleRate'])})")
    logger.info("=" * 60)
    p.terminate()


def build_llm(provider: str, model: str):
    if provider == "openai":
        from pipecat.services.openai.llm import OpenAILLMService
        return OpenAILLMService(
            api_key=os.getenv("OPENAI_API_KEY"),
            settings=OpenAILLMService.Settings(model=model),
        )
    elif provider == "bedrock":
        from pipecat.services.aws.llm import AWSBedrockLLMService
        return AWSBedrockLLMService(
            aws_region=os.getenv("AWS_REGION", "ap-south-1"),
            aws_access_key=os.getenv("AWS_ACCESS_KEY_ID") or None,
            aws_secret_key=os.getenv("AWS_SECRET_ACCESS_KEY") or None,
            aws_session_token=os.getenv("AWS_SESSION_TOKEN") or None,
            settings=AWSBedrockLLMService.Settings(model=model),
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


async def main():
    logger.info("Starting Pipecat Local Mic Test...")

    list_audio_devices()

    # --- STT (Deepgram) ---
    # nova-3 does not support Hindi; nova-2 required for non-English.
    # smart_format is English-only — disabled for Hindi to prevent 400.
    dg_keywords_str = os.getenv("DEEPGRAM_KEYWORDS", "")
    dg_keywords = [k.strip() for k in dg_keywords_str.split(",") if k.strip()] or None
    dg_endpointing = int(os.getenv("DEEPGRAM_ENDPOINTING", "300"))
    dg_lang = os.getenv("DEEPGRAM_LANGUAGE", "hi")
    dg_smart_format = (
        os.getenv("DEEPGRAM_SMART_FORMAT", "false").lower() == "true"
        if dg_lang != "en"
        else os.getenv("DEEPGRAM_SMART_FORMAT", "true").lower() == "true"
    )

    stt = DeepgramSTTService(
        api_key=os.getenv("DEEPGRAM_API_KEY", ""),
        sample_rate=16000,
        settings=DeepgramSTTService.Settings(
            language=dg_lang,
            model=os.getenv("DEEPGRAM_MODEL", "nova-2"),
            smart_format=dg_smart_format,
            punctuate=os.getenv("DEEPGRAM_PUNCTUATE", "true").lower() == "true",
            keywords=dg_keywords,
            endpointing=dg_endpointing,
        ),
    )

    # --- LLM ---
    llm_provider = os.getenv("LLM_PROVIDER", "openai")
    llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    llm = build_llm(llm_provider, llm_model)
    logger.info(f"LLM: {llm_provider} / {llm_model}")

    # --- TTS (Sarvam) ---
    def safe_float(key, default):
        try:
            return float(os.getenv(key, str(default)))
        except ValueError:
            return default

    sarvam_model = os.getenv("SARVAM_MODEL", "bulbul:v3")
    sarvam_voice = os.getenv("SARVAM_VOICE", "priya")
    tts_sample_rate = SARVAM_SAMPLE_RATES.get(sarvam_model, 24000)

    tts = SarvamTTSService(
        api_key=os.getenv("SARVAM_API_KEY", ""),
        sample_rate=tts_sample_rate,
        settings=SarvamTTSService.Settings(
            model=sarvam_model,
            voice=sarvam_voice,
            language="hi-IN",
            pace=safe_float("SARVAM_PACE", 1.0),
            temperature=safe_float("SARVAM_TEMPERATURE", 0.6),
            pitch=safe_float("SARVAM_PITCH", 0.0),
            loudness=safe_float("SARVAM_LOUDNESS", 1.0),
        ),
    )
    logger.info(f"TTS: Sarvam {sarvam_model} / {sarvam_voice} @ {tts_sample_rate}Hz")

    # --- Transport ---
    input_device = os.getenv("AUDIO_INPUT_DEVICE")
    output_device = os.getenv("AUDIO_OUTPUT_DEVICE")

    transport_params = LocalAudioTransportParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        input_device_index=int(input_device) if input_device else None,
        output_device_index=int(output_device) if output_device else None,
    )

    p = pyaudio.PyAudio()
    if transport_params.input_device_index is not None:
        try:
            info = p.get_device_info_by_index(transport_params.input_device_index)
            transport_params.audio_in_sample_rate = int(info["defaultSampleRate"])
        except Exception:
            pass
    if transport_params.output_device_index is not None:
        try:
            info = p.get_device_info_by_index(transport_params.output_device_index)
            transport_params.audio_out_sample_rate = int(info["defaultSampleRate"])
        except Exception:
            pass
    p.terminate()

    if input_device:
        logger.info(f"Audio INPUT device: {input_device}")
    if output_device:
        logger.info(f"Audio OUTPUT device: {output_device}")

    transport = LocalAudioTransport(params=transport_params)

    # Pre-seeding the greeting as the first assistant message means the LLM sees
    # it as already said — so it answers the user's actual question instead of repeating it.
    messages = [
        {
            "role": "system",
            "content": (
                "You are Priya, a real estate assistant for PropBot. "
                "ALWAYS respond 100% in Hindi using Devanagari script ONLY. "
                "NEVER write any word in Latin/Roman/English script — not even brand names, numbers, or technical terms. "
                "Write brand names in Devanagari phonetically (e.g., प्रोपबॉट, रेरा, ईएमआई, बीएचके). "
                "Keep responses under 2 sentences."
            ),
        },
        {
            "role": "assistant",
            "content": "नमस्ते! मैं प्रोपबॉट से प्रिया बोल रही हूँ। कहिये?",
        },
    ]

    context = LLMContext(messages=messages)
    context_aggregator = LLMContextAggregatorPair(context=context)

    pipeline = Pipeline([
        transport.input(),
        stt,
        context_aggregator.user(),
        llm,
        tts,
        transport.output(),
        context_aggregator.assistant(),
    ])

    task = PipelineWorker(pipeline, params=PipelineParams(audio_out_sample_rate=tts_sample_rate))

    @task.event_handler("on_pipeline_started")
    async def on_pipeline_started(worker, frame):
        logger.info("Pipeline started! Sending initial greeting...")
        await context_aggregator.user().push_context_frame()

    runner = WorkerRunner()
    await runner.add_workers(task)

    logger.info(f"Connecting to Deepgram, {llm_provider.upper()}, and Sarvam...")
    await runner.run()


if __name__ == "__main__":
    asyncio.run(main())
