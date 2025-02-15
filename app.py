import os

import aiohttp
import modal
from agent import _voice_bot_process
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from fastapi import Form, UploadFile, File
from loguru import logger
from pipecat.transports.services.helpers.daily_rest import (
    DailyRESTHelper,
    DailyRoomParams,
)
from PyPDF2 import PdfReader
from io import BytesIO


MAX_SESSION_TIME = 15 * 60  # 15 minutes

# Create a new modal app
app = modal.App("pipecat-modal")

# Define the image
image = modal.Image.debian_slim(python_version="3.12").pip_install_from_requirements(
    "requirements.txt"
)


@app.function(
    image=image,
    cpu=1.0,
    secrets=[modal.Secret.from_dotenv()],
    keep_warm=1,
    enable_memory_snapshot=True,
    max_inputs=1,  # Do not reuse instances across requests
    retries=0,
)
def launch_bot_process(room_url: str, token: str, language: str, file_contents):
    _voice_bot_process(room_url, token, language, file_contents)


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes"""
    # Open the PDF from bytes
    pdf_stream = BytesIO(pdf_bytes)
    reader = PdfReader(pdf_stream)
    text = ""
    # Iterate through each page
    for page in reader.pages:
        text += page.extract_text()
    return text


@app.function(
    image=image,
    secrets=[modal.Secret.from_dotenv()],
)
# Define the start function
@modal.web_endpoint(method="POST")
async def start(
    language: str = Form(..., regex="^(Arabic|English)$"), file: UploadFile = File(...)
):
    # Validate file type
    if file.content_type != "application/pdf" and file.content_type != "text/plain":
        raise HTTPException(
            status_code=400, detail="Only PDF or Text files are allowed"
        )

    logger.info("Request received")
    logger.info(f"Received language: {language}")
    file_contents = await file.read()
    # Extract text from file
    if file.content_type == "application/pdf":
        text = extract_text_from_pdf_bytes(file_contents)
    else:
        text = file_contents.decode("utf-8")

    # Start Daily session
    async with aiohttp.ClientSession() as session:
        daily_rest_helper = DailyRESTHelper(
            daily_api_key=os.getenv("DAILY_API_KEY", ""),
            daily_api_url=os.getenv("DAILY_API_URL", "https://api.daily.co/v1"),
            aiohttp_session=session,
        )

        # Create new Daily room
        room = await daily_rest_helper.create_room(DailyRoomParams())
        if not room.url:
            raise HTTPException(
                status_code=500,
                detail="Unable to create room",
            )
        logger.info(f"Created room: {room.url}")

        # Create bot token for room
        token = await daily_rest_helper.get_token(room.url, MAX_SESSION_TIME)
        if not token:
            raise HTTPException(
                status_code=500, detail=f"Failed to get token for room: {room.url}"
            )

        logger.info(f"Bot token created: {token}")

        # Spawn a new bot process
        launch_bot_process.spawn(
            room_url=room.url, token=token, language=language, file_contents=text
        )

        # Return room URL to the user to join
        return JSONResponse(content={"room_url": room.url, token: token})
