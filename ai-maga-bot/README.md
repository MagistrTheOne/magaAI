# AI-Maga Telegram Assistant 🤖

AI-powered Telegram assistant with auto voice/text responses using Yandex Foundation Models and SpeechKit.

## Features

- 🤖 **AI Conversations**: Powered by Yandex GPT
- 🎤 **Voice Responses**: Automatic voice synthesis with Yandex SpeechKit
- 🔄 **Auto Mode**: Smart response mode detection
- 🛡️ **Secure Webhooks**: Protected Telegram webhooks
- 🚀 **Railway Ready**: Docker deployment for Railway

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Yandex Cloud account with Foundation Models and SpeechKit enabled

### 2. Environment Setup

```bash
# Clone repository
git clone <your-repo>
cd ai-maga-bot

# Copy environment template
cp .env.example .env

# Edit .env with your values
nano .env
```

Required environment variables:

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_WEBHOOK_SECRET=your_random_secret

# Yandex Cloud
YANDEX_API_KEY=your_yandex_api_key
YANDEX_FOLDER_ID=your_folder_id
YANDEX_LLM_MODEL=gpt://your-catalog/model-name

# Deployment
BASE_PUBLIC_URL=https://your-domain.railway.app
```

### 3. Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python -m app.main

# Or with uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### 4. Set Webhook (Local Testing)

For local testing, use ngrok or similar:

```bash
# Install ngrok
npm install -g ngrok

# Start ngrok on port 8080
ngrok http 8080

# Set BASE_PUBLIC_URL to your ngrok URL
# Then set webhook
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook?url=$BASE_PUBLIC_URL/webhook/telegram/$TELEGRAM_WEBHOOK_SECRET"
```

## Deployment to Railway

### 1. Create Railway Project

1. Go to [Railway.app](https://railway.app)
2. Create new project
3. Connect your GitHub repository

### 2. Configure Environment Variables

In Railway dashboard → Variables:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_WEBHOOK_SECRET=your_secret
BASE_PUBLIC_URL=https://your-project.railway.app
YANDEX_API_KEY=your_yandex_key
YANDEX_FOLDER_ID=your_folder_id
YANDEX_LLM_MODEL=gpt://catalog/model
YANDEX_TTS_VOICE=alyss
YANDEX_TTS_FORMAT=oggopus
YANDEX_STT_ENABLE=false
PORT=8080
LOG_LEVEL=INFO
```

### 3. Deploy

Railway will automatically build and deploy using the Dockerfile.

### 4. Verify Deployment

Check logs in Railway dashboard:
```
Webhook was set: OK
Starting server on 0.0.0.0:8080
```

Test health endpoint:
```bash
curl https://your-project.railway.app/healthz
# Should return: {"status":"ok"}
```

## Usage

### Bot Commands

- `/start` - Welcome message and current mode
- `/help` - Show help and available commands
- `/mode auto|text|voice` - Change response mode

### Response Modes

- **auto** (default): Text → text, voice → voice, 🔊 in text → voice
- **text**: Always respond with text
- **voice**: Always respond with voice

### Examples

```
User: Hello, how are you?
Bot: I'm doing well, thank you! How can I help you today?

User: Tell me a joke 🔊
Bot: [Voice response with a joke]

User (voice): What's the weather like?
Bot: [Voice response about weather]
```

## Yandex Cloud Setup

### 1. Create Yandex Cloud Account

1. Go to [Yandex Cloud](https://cloud.yandex.com)
2. Create account and billing

### 2. Enable Services

1. **Foundation Models**: Enable YandexGPT in your folder
2. **SpeechKit**: Enable TTS (and STT if needed)

### 3. Get Credentials

1. Create API key in Yandex Cloud console
2. Get your folder ID
3. Find your model URI (e.g., `gpt://catalog-id/model-name`)

## Architecture

```
Telegram → Webhook → FastAPI → aiogram → Yandex LLM/TTS → Response
```

### Key Components

- **FastAPI**: Web server with webhook endpoints
- **aiogram**: Telegram bot framework
- **Yandex LLM**: Text generation via Foundation Models API
- **Yandex TTS**: Voice synthesis via SpeechKit API
- **Mode Manager**: Auto/text/voice response logic

## Development

### Running Tests

```bash
pytest tests/
```

### Project Structure

```
ai-maga-bot/
├── app/
│   ├── main.py           # FastAPI app & webhook
│   ├── router.py         # aiogram handlers
│   ├── settings.py       # Configuration
│   ├── schemas.py        # Pydantic models
│   └── services/
│       ├── yandex_llm.py # LLM service
│       ├── yandex_tts.py # TTS service
│       ├── mode.py       # Mode management
│       └── tg_utils.py   # Telegram helpers
├── tests/
│   ├── test_health.py
│   └── test_yandex_client.py
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Troubleshooting

### Common Issues

**"Webhook not set"**
- Check `BASE_PUBLIC_URL` is correct
- Verify webhook secret matches
- Check Railway logs for errors

**"Yandex API errors"**
- Verify API key and folder ID
- Check model URI format
- Ensure services are enabled in Yandex Cloud

**"Audio not playing"**
- Verify TTS format is `oggopus`
- Check voice parameter is valid
- Test with different voices

### Logs

Check Railway logs for detailed error messages:

```bash
# In Railway dashboard → Deployments → View logs
```

## Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new features
4. Submit pull request

## License

MIT License - see LICENSE file for details.