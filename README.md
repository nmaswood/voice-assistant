# AI Voice Chatbot Assistant

This repository contains an AI Voice Chatbot Assistant that enables users to interact with text or PDF documents through conversational engagement. The assistant supports both Arabic and English languages and is built using the Pipecat framework, integrating services like Gladia for speech-to-text, Eleven Labs for text-to-speech, and Llama-3.3-70B-Versatile as the Large Language Model (LLM).

## Features

- **Document Interaction**: Upload text or PDF files and engage in a conversational manner to extract information or gain insights.
- **Multilingual Support**: Communicate with the assistant in either Arabic or English.
- **Real-Time Communication**: Utilizes Pipecat's Daily transport for seamless real-time media interactions.
- **Advanced AI Integration**: Employs Llama-3.3-70B-Versatile for understanding and generating human-like text responses.
- **Speech Processing**: Incorporates Gladia for converting speech to text and Eleven Labs for generating natural-sounding speech from text.

## Getting Started

Follow these steps to set up and run the project locally.

### Prerequisites

- Python 3.11 or higher
- [Poetry](https://python-poetry.org/) for dependency management
- [Modal](https://modal.com/) for serving and deploying the application

### Installation

1. **Clone the Repository**:

   ```bash
   git clone git@github.com:MohammedShokr/voice-assistant.git
   cd voice-assistant
1. **Install Dependencies**:
    ```bash
   poetry install
   
3. **Set Up Environment Variables**:

Create a .env file in the root directory with the following variables:

```
DAILY_API_KEY=your_daily_api_key
GLADIA_API_KEY=your_gladia_api_key
ELEVEN_LABS_API_KEY=your_eleven_labs_api_key
GROQ_API_KEY=your_groq_api_key
```
Replace your_*_api_key with your actual API keys.


### Running the Application
- **Serve Locally**:
```bash
modal serve app.py
```
This command starts the application on your local machine.

- **Deploy to Cloud**:
```
modal deploy app.py
```
This command deploys the application to the cloud using Modal.

- **Client Usage**:
To interact with the assistant, send a POST request with the desired language and document file.

```
curl -X POST "<end-point>" \
     -F "language=English" \
     -F "file=@/path/to/your/document.pdf"
```
Replace <end-point> with the actual endpoint URL and `/path/to/your/document.pdf` with the path to your document file.
