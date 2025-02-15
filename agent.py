import asyncio
import os
import sys

from dotenv import load_dotenv
from loguru import logger
from pypdf import PdfReader

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.elevenlabs import ElevenLabsTTSService
from pipecat.services.groq import GroqLLMService
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecat.services.gladia import GladiaSTTService
from pipecat.transcriptions.language import Language


# Load environment variables from a .env file
load_dotenv(override=True)

# Configure logger to output debug information to stderr
logger.remove(0)
logger.add(sys.stderr, level="DEBUG")


def load_text(file_path):
    with open(file_path, "r") as file:
        text = file.read()
    return text


def load_pdf(file_path):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text


# Main asynchronous function to initialize and run the voice assistant pipeline
async def main(room_url: str, token: str, language: str, article_content: str):
    """
    Main function to initialize and run the voice assistant pipeline.
    This function performs the following steps:
    1. Reads the content of a document from "doc.txt".
    2. Truncates the document content using a specified model.
    3. Configures the session and transport for communication.
    4. Sets up the speech-to-text (STT) and text-to-speech (TTS) services.
    5. Initializes the language model (LLM) service with a predefined context.
    6. Creates a pipeline to process audio input, transcribe it, generate responses, and synthesize speech output.
    7. Defines event handlers for participant join and leave events.
    8. Runs the pipeline using a PipelineRunner.
    The pipeline includes:
    - Audio input from the transport.
    - Speech-to-text conversion.
    - Context aggregation for user input.
    - Language model processing.
    - Text-to-speech conversion.
    - Audio output through the transport.
    - Context aggregation for assistant responses.
    Event Handlers:
    - `on_first_participant_joined`: Captures transcription for the participant and sends a welcome message.
    - `on_participant_left`: Cancels the pipeline task when a participant leaves.
    Returns:
        None
    """
    # Load the config file
    if language == "Arabic":
        language_code = Language.AR
    elif language == "English":
        language_code = Language.EN
    else:
        raise ValueError(
            "Invalid language specified. Please use 'Arabic' or 'English'."
        )

    # Configure the session and transport for communication

    # Initialize the transport with DailyParams
    transport = DailyTransport(
        room_url,
        token,
        "agent",
        DailyParams(
            audio_out_enabled=True,
            transcription_enabled=False,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            vad_audio_passthrough=True,
            session_timeout=60
        ),
    )

    # Configure the speech-to-text (STT) service
    stt = GladiaSTTService(
        api_key=os.getenv("GLADIA_API_KEY"),
        confidence=0.7,
        params=GladiaSTTService.InputParams(
            language=language_code, audio_enhancer=True, sample_rate=16000
        ),
    )

    # Configure the text-to-speech (TTS) service
    tts = ElevenLabsTTSService(
        api_key=os.getenv("ELEVEN_LABS_API_KEY"),
        voice_id="21m00Tcm4TlvDq8ikWAM",
        sample_rate=16000,
        params=ElevenLabsTTSService.InputParams(language=language_code),
    )

    # Initialize the language model (LLM) service
    llm = GroqLLMService(
        api_key=os.getenv("GROQ_API_KEY"),
        model="llama-3.3-70b-versatile"
    )

    # Define the initial context for the LLM
    messages = [
        {
            "role": "system",
            "content": f"""You are an AI assistant answering the user questions about the given document only.
You will be given a document defined with context tags and your task is to answer the user questions based on the given document only.
<Context>
{article_content}
</Context>
Use {language} language in this conversation.""",
        },
    ]

    # Create a context aggregator for the LLM
    context = OpenAILLMContext(messages)
    context_aggregator = llm.create_context_aggregator(context)

    # Define the pipeline for processing audio input, transcribing it, generating responses, and synthesizing speech output
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

    # Create a pipeline task with specified parameters
    task = PipelineTask(
        pipeline,
        PipelineParams(
            audio_out_sample_rate=44100,
            allow_interruptions=True,
            enable_metrics=True,
        ),
    )

    # Define event handler for when the first participant joins
    @transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant):
        await transport.capture_participant_transcription(participant["id"])
        participant_name = participant.get("info", {}).get("userName", "")
        messages.append(
            {
                "role": "user",
                "content": f"A user named {participant_name} just joined the conversation with you. Welcome him and offer your assistance.",
            }
        )
        await task.queue_frames([context_aggregator.user().get_context_frame()])

    # Define event handler for when a participant leaves
    @transport.event_handler("on_participant_left")
    async def on_participant_left(transport, participant, reason):
        await task.cancel()

    # Initialize and run the pipeline using a PipelineRunner
    runner = PipelineRunner()
    await runner.run(task)


def _voice_bot_process(room_url: str, token: str, language: str, file_contents):
    asyncio.run(main(room_url, token, language, file_contents))