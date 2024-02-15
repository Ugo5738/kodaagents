from openai import OpenAI
from decouple import config

openai_client = OpenAI(api_key=config("OPENAI_API_KEY"))
