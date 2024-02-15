import numpy as np
import pandas as pd

from verification.pdf.openai_chat import get_chat_response


class TransactionSummary:
    def __init__(
        self, transactions, header_columns=["Date", "Description", "Credit", "Debit"]
    ):
        self.transactions = transactions
        self.df = pd.DataFrame(self.transactions, columns=header_columns)
        print(self.df)
        self._prepare_data()

    def _prepare_data(self):
        # Ensure 'Date' is in datetime format
        self.df["Date"] = pd.to_datetime(
            self.df["Date"], errors="coerce", dayfirst=True
        ).ffill()

        # Convert 'Credit' and 'Debit' to numeric, handling any non-numeric issues
        self.df["Credit"] = pd.to_numeric(
            self.df["Credit"].str.replace(",", ""), errors="coerce"
        ).fillna(0)
        self.df["Debit"] = pd.to_numeric(
            self.df["Debit"].str.replace(",", ""), errors="coerce"
        ).fillna(0)

    def check_gambling_activities(self):
        # Convert the 'Description' column to a list
        descriptions_list = self.df["Description"].tolist()

        # Create a dictionary with index as key and description as value
        description_dict = {
            index: description for index, description in enumerate(descriptions_list)
        }

        # Convert the dictionary to a string
        description_str = str(description_dict)

        example_structure = {
            "gambling": True,
            "area_found": [
                {"index": 23, "description": "Gambling ticket"},
                {"index": 30, "description": "Gambling ticket"},
                # more description and index here
            ],
        }
        instruction = "Get the index and description text of all transactions that shows gambling activites from the list of the transactions. If none exist, return False and an empty list"
        response = get_chat_response(instruction, description_str, example_structure)

        return response

    def filter_last_six_months(self):
        six_months_ago = pd.Timestamp.now() - pd.DateOffset(months=6)
        return self.df[self.df["Date"] >= six_months_ago]

    def generate_monthly_summary(self):
        filtered_df = self.filter_last_six_months()
        monthly_summary = (
            filtered_df.groupby(
                [
                    filtered_df["Date"].dt.year.rename("Year"),
                    filtered_df["Date"].dt.month.rename("Month"),
                ]
            )
            .agg(Income=("Credit", "sum"), Expenses=("Debit", "sum"))
            .reset_index()
        )

        # Calculate Savings and Savings Ratio
        monthly_summary["Savings"] = (
            monthly_summary["Income"] - monthly_summary["Expenses"]
        )
        monthly_summary["Savings_Ratio"] = np.where(
            monthly_summary["Income"] > 0,
            (monthly_summary["Savings"] / monthly_summary["Income"]) * 100,
            0,  # Or another appropriate value indicating no calculation possible
        )

        # Convert month numbers to words
        monthly_summary["Month"] = monthly_summary["Month"].apply(
            lambda x: pd.to_datetime(x, format="%m").strftime("%B")
        )

        total_income = monthly_summary["Income"].sum()
        total_expenses = monthly_summary["Expenses"].sum()
        total_savings = monthly_summary["Savings"].sum()

        if np.isnan(total_income) or np.isnan(total_savings):
            print("NaN encountered in totals. Adjusting...")
            total_income = np.nan_to_num(total_income, nan=0.0)  # Convert NaN to 0.0
            total_savings = np.nan_to_num(total_savings, nan=0.0)  # Convert NaN to 0.0

        # Use np.where to safely perform division, avoiding division by zero
        total_savings_ratio = np.where(
            total_income > 0, (total_savings / total_income) * 100, 0
        )

        # Calculate totals and append to the bottom of the DataFrame
        totals_row = {
            "Year": "Total",
            "Month": "All",
            "Income": total_income,
            "Expenses": total_expenses,
            "Savings": total_savings,
            "Savings_Ratio": total_savings_ratio,
        }

        totals_df = pd.DataFrame([totals_row])
        return pd.concat([monthly_summary, totals_df], ignore_index=True)
