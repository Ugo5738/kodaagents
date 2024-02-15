import json
import logging
import time

from langchain.schema import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from openai import OpenAI

client = OpenAI(api_key="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")


def get_refined_instruction(instruction, example_structure, message_type=None):
    if message_type == "for_vision":
        structured_instruction = f"""{instruction}\n\nEnsure you structure the JSON data using this format with 'columns' being the key name and the values being a list of column names:\n\nEXAMPLE:\n\n{example_structure}"""
    if message_type == "not_vision":
        structured_instruction = f"""{instruction}\n\nHere is how I would like the information to be structured in JSON format:\n\nEXAMPLE:\n\n{example_structure}"""
    return structured_instruction


def get_chat_response(
    instruction, message, example_structure=None, message_type="not_vision"
):
    start_time = time.time()

    chat = ChatOpenAI(
        temperature=0.7,
        model_name="gpt-4-1106-preview",
        openai_api_key="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",
    )

    messages = [SystemMessage(content=instruction), HumanMessage(content=message)]

    if example_structure:
        structured_instruction = get_refined_instruction(
            instruction, example_structure, message_type=message_type
        )

        messages = [
            {"role": "system", "content": structured_instruction},
            {"role": "user", "content": message},
        ]

        structured_response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=messages,
            response_format={"type": "json_object"},
        )

        response = json.loads(structured_response.choices[0].message.content)

        total = time.time() - start_time
        logging.info(f"Chat Response Time: {total}")

        return response

    response = chat(messages).content
    total = time.time() - start_time
    logging.info(f"Chat Response Time: {total}")
    return response


def swap_columns(header_columns):
    default_columns = ["Date", "Debit", "Credit", "Description"]

    desired_format = {"columns": ["Date", "Description", "Credit", "Debit"]}

    instruction = f"""These two lists represent column names of different transaction tables. Map List 1 to List 2 by identifying columns that correspond \
        to each other based on their content or purpose. Then, rearrange the columns in List 1 to match the order and naming convention of List 2.
    """

    message = f"""
    LIST 1: 
    {default_columns}
    
    list 2:
    {header_columns}
    """

    chat_response = get_chat_response(
        instruction,
        message,
        example_structure=desired_format,
        message_type="for_vision",
    )

    arranged_columns = chat_response["columns"]

    return arranged_columns


def get_vision_response(image_data_url, sample_columns):
    response = client.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""Return JSON document of the column names in the transactions table using the sample format as a guide. Ensure you return only JSON not other text.\n\n
                        
                        SAMPLE FORMAT: 
                        {sample_columns}""",
                    },
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ],
            }
        ],
        max_tokens=300,
    )

    # Extract JSON data from the response and remove Markdown formatting
    json_string = response.choices[0].message.content
    json_string = json_string.replace("```json\n", "").replace("\n```", "")
    # print("This is json string: ", json_string)
    data = json.loads(json_string)

    column_headers = data.get("columns", [])

    return column_headers


def get_vision_data(image_data_url, sample_columns):
    response = client.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""Return JSON document of the transactions table using the sample format as a guide. Ensure you return only JSON not other text.\n\n
                        
                        SAMPLE FORMAT: 
                        {sample_columns}.\nPlease follow the Date format of day-month-year""",
                    },
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ],
            }
        ],
        max_tokens=300,
    )

    # Extract JSON data from the response and remove Markdown formatting
    json_string = response.choices[0].message.content
    json_string = json_string.replace("```json\n", "").replace("\n```", "")
    print("This is the json string I am checking: ")
    print(json_string)
    data = json.loads(json_string)
    return data


def refine_data(vision_transaction_data, sample_columns):
    instruction = f"""Given the transaction details, select the data of columns in the required columns from \
        the entire set of transactions. Give you response in the required format. Ensure you remove Opening \
        Balance and Closing Balance records in your response.
    """

    message = f"""
    TRANSACTION DETAILS:
    {vision_transaction_data}
    
    REQUIRED COLUMNS OR EQUIVALENT:
    ["Date", "Description", "Credit", "Debit"]
    """

    refined_data = get_chat_response(
        instruction,
        message,
        example_structure=sample_columns,
        message_type="not_vision",
    )
    print("This is the refined data: ")
    print(refined_data)

    return refined_data


def categorize_pdf(image_data_url, sample_columns):

    response = client.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""Return JSON document showing what category this document belongs to using the sample mapping as a guide. Ensure you return only \\
                        JSON not other text.

                        MAPPING EXPLANATION:
                        1 => Characterized by a transaction table with well defined and distinct and full grid lines separating each transaction entry, cells and column. 
                        2 => Characterized by the transaction table having very sparse grid lines if at all. Institutions that use this type of statement are WEMA BANK
                        3 => Characterized by the fact that it doesn't fit into any of the above categorization and not a lot of transactions are in the transaction table. A lot of text that is not particular about the transaction are written in the document.

                        MAPPING GUIDE:
                        {{
                            "Zenith Bank": 1,
                            "Guaranty Trust Bank (GT Bank)": 1,
                            "Wema Bank": 2,
                            "Royal Bank of Canada": 3,
                        }}

                        SAMPLE RESPONSE FORMAT: 
                        {sample_columns}
                    """,
                    },
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ],
            }
        ],
        max_tokens=300,
    )

    # Extract JSON data from the response and remove Markdown formatting
    json_string = response.choices[0].message.content
    json_string = json_string.replace("```json\n", "").replace("\n```", "")
    # print("This is json string: ", json_string)
    data = json.loads(json_string)
    print(data)
    type = data.get("type", [])

    return type
