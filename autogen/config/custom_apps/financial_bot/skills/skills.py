import csv
import json

import openai
import pandas as pd
from shared.utils.base_config import openai_client
from shared.utils.log_config import configure_logger

logger = configure_logger(__name__)


def interpret_user_preferences(input_text: str):
    """
    Interprets user's natural language input into structured budget preferences.
    Args:
        input_text (str): User's natural language input describing budget preferences.
    Returns:
        dict: Structured budget preferences.
    """
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant. Convert the user's natural language conversation text into structured budget preferences in JSON format.",
        },
        {"role": "user", "content": input_text},
    ]

    response = client.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=messages,
        response_format={"type": "json_object"},
    )
    try:
        # Assuming the response is a Python dictionary in string format
        preferences = eval(response["choices"][0]["message"]["content"])
        return preferences
    except Exception as e:
        logger(f"An error occurred: {e}")
        return {"error": "Could not interpret preferences"}


def create_budget_csv(preferences: dict, file_name: str = "budget.csv"):
    """
    Takes user's budgeting preferences and creates a CSV file.
    Args:
        preferences (dict): User's budgeting preferences.
        file_name (str): Name of the CSV file to be created.
    """
    try:
        with open(file_name, mode="w", newline="") as file:
            writer = csv.writer(file)
            # Assuming preferences is a dictionary with key-value pairs for budget items
            writer.writerow(["Item", "Price"])
            for key, value in preferences.items():
                writer.writerow([key, value])
        return f"Budget CSV '{file_name}' created successfully."
    except Exception as e:
        print(f"An error occurred while writing CSV: {e}")


def analyze_bank_statement(statement_file: str):
    """
    Analyzes bank statements from a CSV file.
    Args:
        statement_file (str): Path to the bank statement CSV file.
    Returns:
        str: Analysis insights.
    """
    # Implement analysis logic, e.g., categorizing expenses, identifying trends
    df = pd.read_csv(statement_file)
    # Perform analysis and generate insights
    insights = "Insights based on analysis"
    return insights


def generate_update_progress_report(
    budget_file: str, spending_file: str, report_file: str = "progress_report.csv"
):
    """
    Generates and updates progress reports.
    Args:
        budget_file (str): Path to the budget CSV file.
        spending_file (str): Path to the spending CSV file.
        report_file (str): Path to save the progress report.
    """
    budget_df = pd.read_csv(budget_file)
    spending_df = pd.read_csv(spending_file)
    # Logic to compare budget vs spending and generate report
    report_df = pd.DataFrame()  # Replace with actual report generation logic
    report_df.to_csv(report_file, index=False)
    return f"Progress report '{report_file}' generated/updated successfully."


def calculate_progress(budget_file: str, spending_file: str):
    """
    Calculates progress based on budget and actual spending.
    Args:
        budget_file (str): Path to the budget CSV file.
        spending_file (str): Path to the spending CSV file.
    Returns:
        str: Progress calculation results.
    """
    budget_df = pd.read_csv(budget_file)
    spending_df = pd.read_csv(spending_file)
    # Logic to calculate progress
    progress = "Calculated progress"
    return progress
