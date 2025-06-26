"""
PHIL Analytics and QA Library - Data Cleaning

This module provides data cleaning functionality based on the original working code,
simplified to just add the three basic columns: PAYER FOLDER, EFT NUM, PRACTICE ID.
"""

import pandas as pd
import re
import time
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict
from typing import Dict, List
from .exceptions import DataProcessingError
from .utils import format_runtime, print_processing_summary, get_mapping_loader, determine_payer_folder


class DataCleaner:
    """
    Handles data cleaning operations for payment data.

    This class is based on the original working scrub_combined_file.py code,
    simplified to focus on the core functionality that works.
    """

    def __init__(self, mapping_file: str = "Proliance Mapping.xlsx"):
        """Initialize the data cleaner."""
        print(f"🧹 Initializing Data Cleaner...")
        self.mapping_file = mapping_file
        self.mapping_loader = None
        self.processing_stats = {
            'bad_rows_removed': 0,
            'interest_rows_processed': 0,
            'pla_rows_updated': 0,
            'total_rows_input': 0,
            'total_rows_output': 0
        }
        print(f"✅ Data Cleaner initialized")

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Main method to perform data cleaning operations.

        This follows the original working logic from scrub_combined_file.py
        but simplified to just add the three basic columns.

        Args:
            df (pd.DataFrame): Input DataFrame with raw payment data

        Returns:
            pd.DataFrame: Cleaned DataFrame with basic columns added
        """
        print("🚀 Starting data cleaning process...")
        start_time = time.time()

        self.processing_stats['total_rows_input'] = len(df)

        # Step 1: Remove known bad rows (from original code)
        df = self._remove_bad_rows(df)

        # Step 2: Process interest and PLA rows (from original code)
        df = self._process_interest_and_pla_rows(df)

        # Step 3: Add the three basic columns
        df = self._add_basic_columns(df)

        self.processing_stats['total_rows_output'] = len(df)

        # Calculate runtime
        end_time = time.time()
        runtime = end_time - start_time

        print(f"✅ Data cleaning completed successfully!")
        print(f"⏱️ Cleaning runtime: {format_runtime(runtime)}")

        # Print summary
        print_processing_summary(self.processing_stats, "Data Cleaning")

        return df

    def _remove_bad_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove known bad rows - exact logic from original code."""
        print("🗑️ Removing known bad rows...")

        rows_before = len(df)

        # Original bad row logic - exactly as it was
        bad_rows = (
            ((df["Enc Nbr"] != "") & (df["Bill Amt"] == "0") & (df["Pd Amt"] == "0") & (df["Reason Cd"] == "")) |
            ((df["Enc Nbr"] == "") & (df["Description"] == "Encounter not found.") & (df["Bill Amt"] == "0") & (df["Pd Amt"] == "0")) |
            ((df["Description"] == "Encounter payer not found") & (df["Svc Date"] == "") & (df["Reason Cd"] == ""))
        )

        df = df[~bad_rows].copy()
        rows_removed = rows_before - len(df)
        self.processing_stats['bad_rows_removed'] = rows_removed

        print(f"   ✅ Removed {rows_removed:,} bad rows")
        print(f"   📊 Remaining rows: {len(df):,}")

        return df

    def _process_interest_and_pla_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process interest and PLA rows - exact logic from original code."""
        print("🔧 Processing and removing interest rows after updating PLA rows...")

        rows_to_drop = []

        for chk_nbr, group in df.groupby("Chk Nbr"):
            interest_rows = group[group["Description"].str.startswith("Interest payment", na=False)]
            pla_rows = group[
                group["Description"].str.startswith("Provider Level Adjustment", na=False) &
                group["Description"].str.contains("L6", na=False)
            ]

            if len(pla_rows) != 1 or len(interest_rows) == 0:
                continue

            # Get PLA amount
            pla_row = pla_rows.iloc[0]
            pla_match = re.search(r"Provider Level Adjustment.*\$(\-?\d+\.\d+)", pla_row["Description"])
            if not pla_match:
                continue
            pla_amt = float(pla_match.group(1))
            amt_str = pla_match.group(1)

            # Sum interest amounts
            interest_total = 0
            for _, irow in interest_rows.iterrows():
                match = re.search(r"Interest payment.*\$(\-?\d+\.\d+)", irow["Description"])
                if match:
                    interest_total += float(match.group(1))
                else:
                    interest_total = None
                    break

            if interest_total is not None and round(pla_amt, 2) == round(interest_total, 2):
                # Copy Pat Name and Clm Sts Cod from interest row to PLA row
                interest_row = interest_rows.iloc[0]
                pat_name = interest_row["Pat Name"]
                clm_sts = interest_row["Clm Sts Cod"]
                df.loc[pla_row.name, "Pat Name"] = pat_name
                df.loc[pla_row.name, "Clm Sts Cod"] = clm_sts

                # Filter all rows by Chk Nbr + Pat Name + Clm Sts Cod
                match_rows = df[
                    (df["Chk Nbr"] == chk_nbr) &
                    (df["Pat Name"] == pat_name) &
                    (df["Clm Sts Cod"] == clm_sts)
                ]

                # Get Enc Nbr and Pol Nbr
                enc_nbr, pol_nbr = "", ""
                for _, row in match_rows.iterrows():
                    if row["Enc Nbr"] != "" and row["Pol Nbr"] != "":
                        enc_nbr = row["Enc Nbr"]
                        pol_nbr = row["Pol Nbr"]
                        break

                # Update PLA + interest rows
                df.loc[pla_row.name, "Enc Nbr"] = enc_nbr
                df.loc[pla_row.name, "Pol Nbr"] = pol_nbr
                df.loc[interest_rows.index, "Enc Nbr"] = enc_nbr
                df.loc[interest_rows.index, "Pol Nbr"] = pol_nbr

                # Update Description on PLA row
                new_desc = f"L6^Enc: {enc_nbr}|Status: {clm_sts}|Pol Nbr: {pol_nbr}|Amt: {amt_str}"
                df.loc[pla_row.name, "Description"] = new_desc

                # Mark interest rows to delete
                rows_to_drop.extend(interest_rows.index.tolist())

                self.processing_stats['pla_rows_updated'] += 1

        # Drop interest rows
        if rows_to_drop:
            df = df.drop(index=rows_to_drop).reset_index(drop=True)
            self.processing_stats['interest_rows_processed'] = len(rows_to_drop)
            print(f"   ✅ Updated {self.processing_stats['pla_rows_updated']} PLA rows")
            print(f"   🗑️ Removed {len(rows_to_drop)} interest rows")
        else:
            print("   ℹ️ No interest/PLA pairs found to process")

        return df

    def _add_basic_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add the three basic columns: PAYER FOLDER, EFT NUM, PRACTICE ID."""
        print("📊 Adding PAYER FOLDER, EFT NUM, and PRACTICE ID columns...")

        # Load mappings if not already loaded
        if self.mapping_loader is None:
            self.mapping_loader = get_mapping_loader(self.mapping_file)

        practice_mapping, payer_df = self.mapping_loader.load_mappings()

        # Add the new columns
        df["PAYER FOLDER"] = ""
        df["EFT NUM"] = ""
        df["PRACTICE ID"] = ""

        print(f"   🔄 Processing {len(df):,} rows...")

        # Process each row
        for idx, row in df.iterrows():
            # Get the File column value (this contains the payment file identifier)
            file_identifier = str(row["File"]).strip()

            # Parse the payment file identifier, not the Excel filename
            file_parts = file_identifier.split("_")
            chk_nbr = str(row["Chk Nbr"]).strip()

            # Determine payer folder, EFT number, and practice ID
            payer_folder, eft_num, practice_id = determine_payer_folder(
                file_parts, practice_mapping, payer_df, chk_nbr
            )

            # Set the values
            df.at[idx, "PAYER FOLDER"] = payer_folder
            df.at[idx, "EFT NUM"] = eft_num
            df.at[idx, "PRACTICE ID"] = practice_id

            # Progress indicator for large datasets
            if (idx + 1) % 5000 == 0:
                print(f"      📈 Processed {idx + 1:,} rows...")

        # Get summary of payer folders found
        payer_folders = df["PAYER FOLDER"].value_counts()
        print(f"   ✅ Added basic columns successfully!")
        print(f"   📋 Payer folders found: {len(payer_folders)}")
        for folder, count in payer_folders.head(10).items():
            print(f"      • {folder}: {count:,} rows")

        return df

    def save_to_file(self, df: pd.DataFrame, output_file: str) -> None:
        """
        Save the scrubbed data to an Excel file with proper formatting.

        Uses the exact same formatting logic as the original working code.

        Args:
            df (pd.DataFrame): DataFrame to save
            output_file (str): Path for the output Excel file
        """
        print(f"💾 Saving scrubbed data to: {output_file}")

        try:
            # Create ExcelWriter with openpyxl engine for formatting control
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Sheet1', index=False)

                # Get the workbook and worksheet
                workbook = writer.book
                worksheet = writer.sheets['Sheet1']

                # Freeze the top row
                worksheet.freeze_panes = 'A2'

                # Bold the header row
                for cell in worksheet[1]:
                    cell.font = cell.font.copy(bold=True)

                # Format specific columns as text (original logic)
                from openpyxl.utils import get_column_letter

                for col_idx, col_name in enumerate(df.columns, 1):
                    col_letter = get_column_letter(col_idx)

                    # Set column format to text for all cells in this column
                    for row in range(1, len(df) + 2):  # +2 for header and 1-indexing
                        cell = worksheet[f"{col_letter}{row}"]
                        cell.number_format = '@'  # Text format

            print(f"✅ Scrubbed data saved successfully!")
            print(f"   📁 File location: {output_file}")
            print(f"   📊 Rows saved: {len(df):,}")
            print(f"   📋 Columns saved: {len(df.columns)}")

        except Exception as e:
            raise DataProcessingError(
                f"Failed to save Excel file: {e}",
                operation="excel_save",
                output_file=output_file
            )

    def get_cleaning_stats(self) -> Dict:
        """
        Get data cleaning statistics.

        Returns:
            Dict: Dictionary of cleaning statistics
        """
        return self.processing_stats.copy()