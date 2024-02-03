import asyncio
from concurrent.futures import ThreadPoolExecutor

from interpreter import interpreter

# from interpreter.core.core import OpenInterpreter

interpreter = OpenInterpreter()

executor = ThreadPoolExecutor()


async def get_interpreter_result(query):
    loop = asyncio.get_running_loop()

    # Function to be called within the ThreadPoolExecutor
    def run_chat():
        interpreter.auto_run = True
        return interpreter.chat(query)

    try:
        # Run the synchronous interpreter.chat in an executor
        final_response = await loop.run_in_executor(executor, run_chat)
        return final_response
    except Exception as e:
        # Handle exceptions that may occur during chat execution
        print(f"An error occurred: {e}")
        return None
