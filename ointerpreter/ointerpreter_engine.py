import asyncio
from concurrent.futures import ThreadPoolExecutor

from interpreter import interpreter

executor = ThreadPoolExecutor()


async def get_interpreter_result(query):
    loop = asyncio.get_running_loop()
    final_response = await loop.run_in_executor(executor, interpreter.chat, query)
    return final_response
