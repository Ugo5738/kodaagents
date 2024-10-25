from anthropic import AsyncAnthropic
from django.conf import settings
from groq import AsyncGroq
from openai import AsyncOpenAI

anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
