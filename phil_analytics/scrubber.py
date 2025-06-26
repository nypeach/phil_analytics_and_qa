"""
PHIL Analytics and QA Library - Data Cleaning

This module provides data cleaning functionality including bad row removal,
interest/PLA payment processing, and basic column additions.
"""

import pandas as pd
import re
import time
from typing import Dict, List
from .exceptions import DataProcessingError
from .utils import format_runtime, print_processing_summary, get_mapping_loader, determine_payer_folder


class DataCleaner:
    """
    Handles data cleaning operations for payment data.

    This class focuses specifically on:
    - Removing known bad rows based on patterns
    - Processing interest payments and Provider Level Adjustments (PLA)
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

    def remove_bad_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove known bad rows based on specific patterns.

        Args:
            df (pd.DataFrame): Input DataFrame

        Returns:
            pd.DataFrame: DataFrame with bad rows removed
        """
        print("🗑️ Removing known bad rows...")

        rows_before = len(df)
        self.processing_stats['total_rows_input'] = rows_before

        # Define bad row patterns
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

    def process_interest_and_pla_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process interest payments and Provider Level Adjustments (PLA).

        This method:
        1. Finds matching interest payments and L6 PLA rows
        2. Updates PLA rows with interest payment data
        3. Removes processed interest rows

        Args:
            df (pd.DataFrame): Input DataFrame

        Returns:
            pd.DataFrame: DataFrame with processed interest and PLA rows
        """
        print("🔧 Processing interest payments and PLA rows...")

        rows_to_drop = []
        pla_updates = 0
        interest_processed = 0

        print("   🔍 Analyzing check numbers for interest/PLA patterns...")

        # Group by check number to find interest/PLA pairs
        for chk_nbr, group in df.groupby("Chk Nbr"):
            result = self._process_check_group(group, chk_nbr, df)
            if result:
                interest_indices, updated_pla = result
                rows_to_drop.extend(interest_indices)
                pla_updates += 1
                interest_processed += len(interest_indices)

        # Drop processed interest rows
        if rows_to_drop:
            df = df.drop(index=rows_to_drop).reset_index(drop=True)
            print(f"   ✅ Updated {pla_updates} PLA rows")
            print(f"   🗑️ Removed {interest_processed} interest rows")
        else:
            print("   ℹ️ No interest/PLA pairs found to process")

        self.processing_stats['interest_rows_processed'] = interest_processed
        self.processing_stats['pla_rows_updated'] = pla_updates
        self.processing_stats['total_rows_output'] = len(df)

        return df

    def _process_check_group(self, group: pd.DataFrame, chk_nbr: str, main_df: pd.DataFrame) -> tuple:
        """
        Process a group of rows for a single check number to find interest/PLA pairs.

        Args:
            group (pd.DataFrame): Rows for a single check number
            chk_nbr (str): Check number being processed
            main_df (pd.DataFrame): Main DataFrame for updates

        Returns:
            tuple: (interest_row_indices, pla_row_updated) or None if no match
        """
        # Find interest and PLA rows
        interest_rows = group[group["Description"].str.startswith("Interest payment", na=False)]
        pla_rows = group[
            group["Description"].str.startswith("Provider Level Adjustment", na=False) &
            group["Description"].str.contains("L6", na=False)
        ]

        # Must have exactly 1 PLA row and at least 1 interest row
        if len(pla_rows) != 1 or len(interest_rows) == 0:
            return None

        pla_row = pla_rows.iloc[0]

        # Extract PLA amount
        pla_match = re.search(r"Provider Level Adjustment.*\$(\-?\d+\.\d+)", pla_row["Description"])
        if not pla_match:
            return None

        pla_amt = float(pla_match.group(1))
        amt_str = pla_match.group(1)

        # Calculate total interest amount
        interest_total = self._calculate_interest_total(interest_rows)
        if interest_total is None:
            return None

        # Check if amounts match
        if round(pla_amt, 2) != round(interest_total, 2):
            return None

        print(f"   🔄 Processing PLA/Interest pair for check {chk_nbr} (${pla_amt})")

        # Update PLA row with interest data
        self._update_pla_row(main_df, pla_row, interest_rows.iloc[0], chk_nbr, amt_str)

        return interest_rows.index.tolist(), True

    def _calculate_interest_total(self, interest_rows: pd.DataFrame) -> float:
        """
        Calculate total interest amount from interest rows.

        Args:
            interest_rows (pd.DataFrame): Interest payment rows

        Returns:
            float: Total interest amount or None if extraction fails
        """
        interest_total = 0
        for _, irow in interest_rows.iterrows():
            match = re.search(r"Interest payment.*\$(\-?\d+\.\d+)", irow["Description"])
            if match:
                interest_total += float(match.group(1))
            else:
                return None  # Failed to extract amount

        return interest_total

    def _update_pla_row(self, df: pd.DataFrame, pla_row: pd.Series, interest_row: pd.Series,
                       chk_nbr: str, amt_str: str) -> None:
        """
        Update PLA row with data from interest row and related records.

        Args:
            df (pd.DataFrame): Main DataFrame
            pla_row (pd.Series): PLA row to update
            interest_row (pd.Series): Interest row with patient data
            chk_nbr (str): Check number
            amt_str (str): Amount string for description
        """
        # Copy patient data from interest row
        pat_name = interest_row["Pat Name"]
        clm_sts = interest_row["Clm Sts Cod"]
        df.loc[pla_row.name, "Pat Name"] = pat_name
        df.loc[pla_row.name, "Clm Sts Cod"] = clm_sts

        # Find related records to get encounter and policy numbers
        match_rows = df[
            (df["Chk Nbr"] == chk_nbr) &
            (df["Pat Name"] == pat_name) &
            (df["Clm Sts Cod"] == clm_sts)
        ]

        # Get encounter and policy numbers from related records
        enc_nbr, pol_nbr = self._extract_encounter_policy(match_rows)

        # Update PLA row with encounter and policy data
        df.loc[pla_row.name, "Enc Nbr"] = enc_nbr
        df.loc[pla_row.name, "Pol Nbr"] = pol_nbr

        # Update description with structured format
        new_desc = f"L6^Enc: {enc_nbr}|Status: {clm_sts}|Pol Nbr: {pol_nbr}|Amt: {amt_str}"
        df.loc[pla_row.name, "Description"] = new_desc

    def _extract_encounter_policy(self, match_rows: pd.DataFrame) -> tuple:
        """
        Extract encounter and policy numbers from matching rows.

        Args:
            match_rows (pd.DataFrame): Rows matching patient and claim status

        Returns:
            tuple: (encounter_number, policy_number)
        """
        enc_nbr, pol_nbr = "", ""

        for _, row in match_rows.iterrows():
            if row["Enc Nbr"] != "" and row["Pol Nbr"] != "":
                enc_nbr = row["Enc Nbr"]
                pol_nbr = row["Pol Nbr"]
                break

    def _prepare_numeric_columns_safely(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Safely convert only specific amount columns to numeric while preserving text formatting.

        This method only converts columns that are explicitly meant to be numeric
        (like Bill Amt, Adj Amt) while leaving all other columns as strings to preserve
        Excel TEXT formatting.

        Args:
            df (pd.DataFrame): Input DataFrame

        Returns:
            pd.DataFrame: DataFrame with selective numeric conversion
        """
        print("   🔢 Converting only amount columns to numeric (preserving text formatting)...")

        # Only these specific columns should be converted to numeric for calculations
        numeric_columns = ["Bill Amt", "Adj Amt", "Pd Amt"]

        for col in numeric_columns:
            if col in df.columns:
                # Store original values for debugging
                original_sample = df[col].head(3).tolist()

                # Convert to numeric, coercing errors to 0
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

                print(f"      • {col}: {original_sample} -> numeric")

        print(f"   ✅ All other columns preserved as text to maintain Excel formatting")
        return df

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Main method to perform all data cleaning operations.

        Args:
            df (pd.DataFrame): Input DataFrame with raw payment data (all columns as strings)

        Returns:
            pd.DataFrame: Cleaned DataFrame with basic columns added
        """
        print("🚀 Starting data cleaning process...")
        print("📝 Preserving Excel TEXT formatting throughout cleaning process...")
        start_time = time.time()

        # Remove bad rows
        df = self.remove_bad_rows(df)

        # Process interest and PLA rows
        df = self.process_interest_and_pla_rows(df)

        # Safely convert only amount columns for calculations
        df = self._prepare_numeric_columns_safely(df)

        # Add basic columns
        df = self.add_basic_columns(df)

        # Calculate runtime
        end_time = time.time()
        runtime = end_time - start_time

        print(f"✅ Data cleaning completed successfully!")
        print(f"📝 Excel TEXT formatting preserved for all non-amount columns")
        print(f"⏱️ Cleaning runtime: {format_runtime(runtime)}")

        # Print summary
        print_processing_summary(self.processing_stats, "Data Cleaning")

        return df

    def save_to_file(self, df: pd.DataFrame, output_file: str) -> None:
        """
        Save the scrubbed data to an Excel file with proper formatting.

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

                # Format all columns as text to preserve formatting
                for col_idx, col_name in enumerate(df.columns, 1):
                    col_letter = chr(64 + col_idx) if col_idx <= 26 else chr(64 + col_idx // 26) + chr(64 + col_idx % 26)
                    for row in range(1, len(df) + 2):
                        cell = worksheet[f"{col_letter}{row}"]
                        cell.number_format = '@'  # Text format

            print(f"✅ Scrubbed data saved successfully!")
            print(f"   📁 File location: {output_file}")
            print(f"   📊 Rows saved: {len(df):,}")

        except Exception as e:
            raise DataProcessingError(
                f"Failed to save Excel file: {e}",
                operation="excel_save",
                output_file=output_file
            )

    def get_cleaning_stats(self) -> Dict:
        """
        Main method to perform all data cleaning operations.

        Args:
            df (pd.DataFrame): Input DataFrame with raw payment data

        Returns:
            pd.DataFrame: Cleaned DataFrame
        """
        print("🚀 Starting data cleaning process...")
        start_time = time.time()

        # Remove bad rows
        df = self.remove_bad_rows(df)

        # Process interest and PLA rows
        df = self.process_interest_and_pla_rows(df)

        # Calculate runtime
        end_time = time.time()
        runtime = end_time - start_time

        print(f"✅ Data cleaning completed successfully!")
        print(f"⏱️ Cleaning runtime: {format_runtime(runtime)}")

        # Print summary
        print_processing_summary(self.processing_stats, "Data Cleaning")

        return df

    def add_basic_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add PAYER FOLDER, EFT NUM, and PRACTICE ID columns.

        Args:
            df (pd.DataFrame): Input DataFrame

        Returns:
            pd.DataFrame: DataFrame with basic columns added
        """
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
            # Parse file parts
            file_parts = str(row["File"]).split("_")
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
        """
        Get data cleaning statistics.

        Returns:
            Dict: Dictionary of cleaning statistics
        """
        return self.processing_stats.copy()