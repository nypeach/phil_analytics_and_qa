"""
PHIL Analytics and QA Library - Excel Data Processor

This module processes Excel spreadsheet data while maintaining text formatting.
Creates data objects with EFT -> Payment -> Encounter -> Service hierarchy.
"""

import pandas as pd
import openpyxl
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple
from collections import defaultdict
import re


class ExcelDataObjectCreator:
    """
    Creates data objects from Excel spreadsheet data while maintaining text formatting.
    Handles grouping of rows by EFT NUM, PMT NUM, PLAs, Encounters, and Services.
    """

    def __init__(self, file_path: str, process_limit: Optional[int] = None):
        """
        Initialize the processor with the Excel file path and optional processing limit.

        Args:
            file_path (str): Path to the Excel file
            process_limit (int, optional): Maximum number of rows to process
        """
        self.file_path = Path(file_path)
        self.process_limit = process_limit
        self.df = None
        self.payer_name = None
        self.data_object = {}
        self.missing_encounter_efts = []
        self._load_data()

    def _load_data(self):
        """
        Load Excel data while preserving text formatting.
        Uses openpyxl engine to maintain Excel TEXT formatting as strings.
        """
        try:
            # Use openpyxl engine to preserve text formatting
            # Set dtype=str for all columns to ensure text is treated as strings
            self.df = pd.read_excel(
                self.file_path,
                engine='openpyxl',
                dtype=str,  # This ensures all columns are treated as strings
                na_filter=False  # Prevents pandas from converting empty cells to NaN
            )

            # Apply process limit if specified
            if self.process_limit:
                self.df = self.df.head(self.process_limit)

            # Extract payer name from filename (remove _Scrubbed.xlsx)
            self.payer_name = self.file_path.stem.replace('_Scrubbed', '')

            # Clean column names (strip whitespace)
            self.df.columns = self.df.columns.str.strip()

            # Fill NaN values with empty strings to maintain string dtype
            self.df = self.df.fillna('')

            print(f"Loaded {len(self.df)} rows from {self.file_path}")
            print(f"Columns: {list(self.df.columns)}")

            # Check for missing encounter EFTs and remove them
            self._identify_and_remove_missing_encounter_efts()

        except Exception as e:
            print(f"Error loading data: {e}")
            raise

    def _identify_and_remove_missing_encounter_efts(self):
        """
        Identify EFTs with 'Encounter not found.' description and remove all rows for those EFTs.
        """
        print("🔍 Checking for EFTs with missing encounters...")

        # Find all EFT NUMs that have "Encounter not found." in Description
        if 'Description' in self.df.columns:
            encounter_not_found_mask = self.df['Description'].astype(str).str.strip() == "Encounter not found."
            missing_encounter_rows = self.df[encounter_not_found_mask]

            if not missing_encounter_rows.empty:
                # Get unique EFT NUMs that have missing encounters
                self.missing_encounter_efts = missing_encounter_rows['EFT NUM'].astype(str).unique().tolist()
                self.missing_encounter_efts = [eft for eft in self.missing_encounter_efts if eft and eft.strip() != '']

                if self.missing_encounter_efts:
                    print(f"   ⚠️ Found {len(self.missing_encounter_efts)} EFTs with missing encounters:")
                    for eft in self.missing_encounter_efts:
                        print(f"      • EFT: {eft}")

                    # Remove ALL rows for these EFT NUMs from the dataframe
                    original_row_count = len(self.df)
                    self.df = self.df[~self.df['EFT NUM'].astype(str).isin(self.missing_encounter_efts)].copy()
                    removed_row_count = original_row_count - len(self.df)

                    print(f"   🗑️ Removed {removed_row_count:,} rows from {len(self.missing_encounter_efts)} EFTs with missing encounters")
                    print(f"   📊 Remaining rows: {len(self.df):,}")
                else:
                    print("   ✅ No EFTs with missing encounters found")
            else:
                print("   ✅ No rows with 'Encounter not found.' description found")
        else:
            print("   ⚠️ No 'Description' column found - skipping missing encounter check")

    def create_data_object(self) -> Dict:
        """
        Create the complete data object with EFT -> Payment -> Encounter -> Service hierarchy.

        Returns:
            Dict: Complete data object with all EFTs, payments, encounters, and services
        """
        print(f"🏗️ Creating data object for {self.payer_name}...")

        # Get all unique EFT NUMs (after missing encounter EFTs have been removed)
        eft_nums = self.df['EFT NUM'].astype(str).unique()
        eft_nums = [eft for eft in eft_nums if eft and eft.strip() != '']

        self.data_object = {}

        for eft_num in eft_nums:
            print(f"   📊 Processing EFT: {eft_num}")

            # Get all rows for this EFT
            eft_rows = self.get_eft_num_rows(eft_num)

            # Create EFT object
            eft_obj = self._create_eft_object(eft_num, eft_rows)

            # Get payment groups for this EFT
            pmt_groups = self.get_pmt_num_rows(eft_rows)

            # Create payment objects
            payments = {}
            for pmt_key, pmt_rows in pmt_groups.items():
                payment_obj = self._create_payment_object(pmt_key, pmt_rows)
                payments[pmt_key] = payment_obj

            eft_obj["payments"] = payments
            self.data_object[eft_num] = eft_obj

        print(f"✅ Data object created with {len(self.data_object)} EFTs")
        return self.data_object

    def get_eft_num_rows(self, eft_num: str) -> pd.DataFrame:
        """
        Get all rows that have the same EFT NUM.

        Args:
            eft_num (str): The EFT number to filter by

        Returns:
            pd.DataFrame: Filtered dataframe with matching EFT NUM
        """
        return self.df[self.df['EFT NUM'].astype(str) == str(eft_num)].copy()

    def get_pmt_num_rows(self, eft_rows: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        Get groups of rows for each PMT NUM (PRACTICE_ID + Chk Nbr combination).

        Args:
            eft_rows (pd.DataFrame): Rows filtered by EFT NUM

        Returns:
            Dict[str, pd.DataFrame]: Dictionary with pmt_num as key and filtered rows as value
        """
        pmt_groups = {}

        # Create PMT NUM by combining PRACTICE_ID and Chk Nbr
        eft_rows['pmt_num'] = eft_rows['PRACTICE ID'].astype(str) + '_' + eft_rows['Chk Nbr'].astype(str)

        # Group by unique PMT NUM combinations
        for pmt_num in eft_rows['pmt_num'].unique():
            if pmt_num and pmt_num != '_':  # Skip empty combinations
                pmt_groups[pmt_num] = eft_rows[eft_rows['pmt_num'] == pmt_num].copy()

        return pmt_groups

    def get_pla_rows(self, pmt_rows: pd.DataFrame) -> pd.DataFrame:
        """
        Get PLA rows based on the correct criteria:
        - (Enc Nbr = "" AND Description contains "Provider Level Adjustment") OR
        - (Clm Nbr = "Provider Lvl Adj" AND Enc Nbr != "" AND Description contains "L6")

        Args:
            pmt_rows (pd.DataFrame): Rows filtered by PMT NUM

        Returns:
            pd.DataFrame: Filtered dataframe with PLA rows
        """
        if 'Description' not in pmt_rows.columns:
            return pd.DataFrame()

        # Condition 1: Enc Nbr = "" AND Description contains "Provider Level Adjustment"
        condition1 = (
            (pmt_rows['Enc Nbr'].astype(str).str.strip() == '') &
            (pmt_rows['Description'].astype(str).str.contains('Provider Level Adjustment', na=False))
        )

        # Condition 2: Clm Nbr = "Provider Lvl Adj" AND Enc Nbr != "" AND Description contains "L6"
        condition2 = (
            (pmt_rows.get('Clm Nbr', pd.Series(dtype=str)).astype(str).str.strip() == 'Provider Lvl Adj') &
            (pmt_rows['Enc Nbr'].astype(str).str.strip() != '') &
            (pmt_rows['Description'].astype(str).str.contains('L6', na=False))
        )

        # Combine conditions with OR
        pla_mask = condition1 | condition2
        return pmt_rows[pla_mask].copy()

    def get_encounter_rows(self, pmt_rows: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        Get encounter rows grouped by Enc Nbr where Enc Nbr is not blank and Clm Sts is the same.

        Args:
            pmt_rows (pd.DataFrame): Rows filtered by PMT NUM

        Returns:
            Dict[str, pd.DataFrame]: Dictionary with enc_num as key and filtered rows as value
        """
        encounter_groups = {}

        if 'Enc Nbr' not in pmt_rows.columns:
            return encounter_groups

        # Filter rows where Enc Nbr is not blank
        enc_rows = pmt_rows[pmt_rows['Enc Nbr'].astype(str).str.strip() != ''].copy()

        # Group by Enc Nbr and Clm Sts Cod combination
        if not enc_rows.empty and 'Clm Sts Cod' in enc_rows.columns:
            enc_rows['enc_key'] = enc_rows['Enc Nbr'].astype(str) + '_' + enc_rows['Clm Sts Cod'].astype(str)

            for enc_key in enc_rows['enc_key'].unique():
                if enc_key and enc_key != '_':
                    encounter_groups[enc_key] = enc_rows[enc_rows['enc_key'] == enc_key].copy()

        return encounter_groups

    def get_service_rows(self, enc_rows: pd.DataFrame) -> pd.DataFrame:
        """
        Get service rows where CPT4 is not blank.

        Args:
            enc_rows (pd.DataFrame): Rows filtered by encounter

        Returns:
            pd.DataFrame: Filtered dataframe with service rows
        """
        if 'CPT4' not in enc_rows.columns:
            return pd.DataFrame()

        service_mask = enc_rows['CPT4'].astype(str).str.strip() != ''
        return enc_rows[service_mask].copy()

    def _create_eft_object(self, eft_num: str, eft_rows: pd.DataFrame) -> Dict:
        """
        Create EFT object from the rows.

        Args:
            eft_num (str): EFT number
            eft_rows (pd.DataFrame): All rows for this EFT

        Returns:
            Dict: EFT object with all attributes
        """
        # Get payer from PAYER FOLDER column if available, otherwise use payer_name
        payer = self.payer_name
        if 'PAYER FOLDER' in eft_rows.columns:
            payer_values = eft_rows['PAYER FOLDER'].astype(str).unique()
            payer_values = [p for p in payer_values if p and p.strip() != '']
            if payer_values:
                payer = payer_values[0]  # Use first non-empty payer folder value

        # Build EFT object
        eft = {
            "eft_num": str(eft_num),
            "payer": str(payer),
            "is_split": False,  # Will be set by PaymentTagger
            "status": "",  # Will be set by PaymentTagger
            "payments": {}  # Will be populated with payment objects
        }

        return eft

    def _create_payment_object(self, payment_key: str, pmt_rows: pd.DataFrame) -> Dict:
        """
        Create payment object from the rows by parsing the File column.

        Args:
            payment_key (str): Payment key (practice_id_check_number) - used for grouping but actual values come from File column
            pmt_rows (pd.DataFrame): All rows for this payment

        Returns:
            Dict: Payment object with all attributes
        """
        # Parse the File column to get the authoritative payment information
        practice_id, pmt_num, payment_amount = self._parse_file_column(pmt_rows)

        # Get PLA rows for this payment
        pla_rows = self.get_pla_rows(pmt_rows)
        plas = self._create_pla_objects(pla_rows)

        # Calculate PLA amounts
        pla_amounts = self._calculate_pla_amounts(pla_rows)

        # Get encounter groups for this payment
        enc_groups = self.get_encounter_rows(pmt_rows)
        encounters = {}

        for enc_key, enc_rows in enc_groups.items():
            encounter_obj = self._create_encounter_object(enc_key, enc_rows)
            encounters[enc_key] = encounter_obj

        # Build payment object
        payment = {
            "practice_id": str(practice_id),
            "num": str(pmt_num),
            "amt": payment_amount,
            "status": "",  # Will be set by PaymentTagger
            "plas": plas,
            "pla_l6_amts": pla_amounts["pla_l6_amts"],  # Sum of L6 PLA amounts
            "pla_other_amts": pla_amounts["pla_other_amts"],  # Sum of Other PLA amounts
            "encounters": encounters,
            "encs_to_check": {}  # Will be populated by EncounterTagger
        }

        return payment

    def _parse_file_column(self, pmt_rows: pd.DataFrame) -> tuple[str, str, float]:
        """
        Parse the File column to extract practice_id, payment_number, and payment_amount.

        File format: {WS_ID}_{WAYSTAR ID}_{AMT}_{CHK NBR}_{TYPE}_{FILE_DATE}
        Example: 207008_SB542_35.03_1525153B100018112000_ACH_20250603

        Args:
            pmt_rows (pd.DataFrame): All rows for this payment

        Returns:
            tuple[str, str, float]: (practice_id, payment_number, payment_amount)
        """
        if 'File' not in pmt_rows.columns:
            print(f"   ⚠️ Warning: No 'File' column found in payment rows")
            return "", "", 0.0

        # Get the first non-empty file name (should be the same for all rows in this payment)
        file_names = pmt_rows['File'].astype(str).str.strip()
        file_names = file_names[file_names != '']  # Remove empty values

        if len(file_names) == 0:
            print(f"   ⚠️ Warning: No file names found in payment rows")
            return "", "", 0.0

        file_name = file_names.iloc[0]

        try:
            # Split by underscore: {WS_ID}_{WAYSTAR ID}_{AMT}_{CHK NBR}_{TYPE}_{FILE_DATE}
            parts = file_name.split('_')

            if len(parts) < 6:
                print(f"   ⚠️ Warning: File name format unexpected - expected 6 parts, got {len(parts)}: {file_name}")
                return "", "", 0.0

            # Extract the components
            ws_id = parts[0].strip()              # WS_ID (practice identifier)
            waystar_id = parts[1].strip()         # WAYSTAR ID
            amount_str = parts[2].strip()         # AMT (payment amount)
            chk_nbr = parts[3].strip()            # CHK NBR (payment/check number)
            payment_type = parts[4].strip()       # TYPE (ACH, etc.)
            file_date = parts[5].strip()          # FILE_DATE

            # Convert amount to float
            payment_amount = float(amount_str)

            # Use WS_ID as practice_id and CHK_NBR as payment number
            practice_id = ws_id
            pmt_num = chk_nbr

            print(f"   📄 Parsed file: {file_name}")
            print(f"      • Practice ID: {practice_id}")
            print(f"      • Payment Num: {pmt_num}")
            print(f"      • Amount: ${payment_amount:,.2f}")

            return practice_id, pmt_num, payment_amount

        except (ValueError, TypeError, IndexError) as e:
            print(f"   ❌ Error parsing file name '{file_name}': {e}")
            return "", "", 0.0

    def _calculate_pla_amounts(self, pla_rows: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate PLA amounts from PLA rows using the actual amounts (no reverse logic).

        Args:
            pla_rows (pd.DataFrame): PLA rows

        Returns:
            Dict[str, float]: Dictionary with pla_l6_amts and pla_other_amts
        """
        pla_l6_amts = 0.0
        pla_other_amts = 0.0

        if 'Description' not in pla_rows.columns:
            return {"pla_l6_amts": pla_l6_amts, "pla_other_amts": pla_other_amts}

        for _, row in pla_rows.iterrows():
            description = str(row['Description']).strip()
            clm_nbr = str(row.get('Clm Nbr', '')).strip()
            enc_nbr = str(row.get('Enc Nbr', '')).strip()

            # Extract amount from description
            pla_amount = self._extract_pla_amount(description)

            if pla_amount is not None:
                # Use actual PLA amount (no reverse logic)
                actual_amount = pla_amount

                # Determine if this is L6 or other PLA
                # L6 PLAs are identified by condition 2 from the PLA criteria:
                # Clm Nbr = "Provider Lvl Adj" AND Enc Nbr != "" AND Description contains "L6"
                is_l6 = (
                    clm_nbr == "Provider Lvl Adj" and
                    enc_nbr != "" and
                    'L6' in description
                )

                if is_l6:
                    pla_l6_amts += actual_amount
                else:
                    pla_other_amts += actual_amount

        return {"pla_l6_amts": pla_l6_amts, "pla_other_amts": pla_other_amts}

    def _extract_pla_amount(self, description: str) -> Optional[float]:
        """
        Extract PLA amount from description text.

        Args:
            description (str): PLA description text

        Returns:
            Optional[float]: Extracted amount or None if not found
        """
        # Look for dollar amounts in the description
        # Common patterns: $123.45, $-123.45, -$123.45, etc.

        # First try to find patterns with $ sign
        dollar_patterns = [
            r'\$(-?\d+\.?\d*)',  # $123.45 or $-123.45
            r'(-?\$\d+\.?\d*)',  # -$123.45
            r'Amt:\s*\$?(-?\d+\.?\d*)',  # Amt: $123.45 or Amt: 123.45
            r'Amount:\s*\$?(-?\d+\.?\d*)',  # Amount: $123.45 or Amount: 123.45
        ]

        for pattern in dollar_patterns:
            matches = re.findall(pattern, description)
            if matches:
                try:
                    # Get the first match and clean it
                    amount_str = matches[0].replace('$', '').strip()
                    return float(amount_str)
                except (ValueError, TypeError):
                    continue

        # If no dollar patterns found, look for any number that might be an amount
        # Look for patterns like "Provider Level Adjustment found: 123.45"
        number_patterns = [
            r'found:\s*(-?\d+\.?\d*)',  # found: 123.45
            r'applied:\s*(-?\d+\.?\d*)',  # applied: 123.45
            r':\s*(-?\d+\.?\d*)$',  # ends with : 123.45
        ]

        for pattern in number_patterns:
            matches = re.findall(pattern, description)
            if matches:
                try:
                    return float(matches[0])
                except (ValueError, TypeError):
                    continue

        # Last resort: look for any decimal number in the description
        decimal_matches = re.findall(r'(-?\d+\.\d{2})', description)
        if decimal_matches:
            try:
                return float(decimal_matches[0])
            except (ValueError, TypeError):
                pass

        return None

    def _create_pla_objects(self, pla_rows: pd.DataFrame) -> Dict[str, List]:
        """
        Create PLA objects from PLA rows.

        Args:
            pla_rows (pd.DataFrame): PLA rows

        Returns:
            Dict[str, List]: PLA objects with L6 and other categories
        """
        pla_l6 = []
        pla_other = []

        if 'Description' in pla_rows.columns:
            for _, row in pla_rows.iterrows():
                description = str(row['Description']).strip()
                clm_nbr = str(row.get('Clm Nbr', '')).strip()
                enc_nbr = str(row.get('Enc Nbr', '')).strip()

                # Clean description - remove "Provider Level Adjustment found: " prefix
                clean_description = self._clean_pla_description(description)

                # L6 PLAs are identified by condition 2 from the PLA criteria:
                # Clm Nbr = "Provider Lvl Adj" AND Enc Nbr != "" AND Description contains "L6"
                is_l6 = (
                    clm_nbr == "Provider Lvl Adj" and
                    enc_nbr != "" and
                    'L6' in description
                )

                if is_l6:
                    pla_l6.append(clean_description)
                else:
                    pla_other.append(clean_description)

        return {
            "pla_l6": pla_l6,
            "pla_other": pla_other
        }

    def _clean_pla_description(self, description: str) -> str:
        """
        Clean PLA description by removing the "Provider Level Adjustment found: " prefix.

        Args:
            description (str): Original PLA description

        Returns:
            str: Cleaned description with prefix removed
        """
        # Remove "Provider Level Adjustment found: " prefix if present
        if "Provider Level Adjustment found: " in description:
            return description.replace("Provider Level Adjustment found: ", "").strip()

        # Also handle other potential prefixes
        if "Provider Level Adjustment " in description:
            # Find the part after "Provider Level Adjustment" and any following text until we hit the actual data
            parts = description.split("Provider Level Adjustment")
            if len(parts) > 1:
                # Look for the actual amount/data part (usually starts with $ or other data)
                remaining = parts[1].strip()
                # Remove common prefixes like "found: ", "applied: ", etc.
                for prefix in ["found: ", "applied: ", ": ", " - "]:
                    if remaining.startswith(prefix):
                        remaining = remaining[len(prefix):].strip()
                        break
                return remaining

        # If no known prefix, return original description
        return description

    def _create_encounter_object(self, encounter_key: str, enc_rows: pd.DataFrame) -> Dict:
        """
        Create encounter object from the rows.

        Args:
            encounter_key (str): Encounter key (enc_nbr_clm_sts)
            enc_rows (pd.DataFrame): All rows for this encounter

        Returns:
            Dict: Encounter object with all attributes
        """
        # Parse encounter key
        if '_' in encounter_key:
            enc_nbr, clm_sts = encounter_key.split('_', 1)
        else:
            enc_nbr = encounter_key
            clm_sts = ""

        # Clean claim status - remove parenthetical text
        if '(' in clm_sts:
            clm_sts = clm_sts.split('(')[0].strip()

        # Get service rows for this encounter
        service_rows = self.get_service_rows(enc_rows)
        services = self._create_service_objects(service_rows)

        # Build encounter object
        encounter = {
            "num": str(enc_nbr),
            "status": str(clm_sts),
            "services": services,
            "tags": []  # Will be populated by EncounterTagger
        }

        return encounter

    def _create_service_objects(self, service_rows: pd.DataFrame) -> List[Dict]:
        """
        Create service objects from service rows.

        Args:
            service_rows (pd.DataFrame): Service rows (rows with CPT4 codes)

        Returns:
            List[Dict]: List of service objects
        """
        services = []

        for _, row in service_rows.iterrows():
            service = self._create_service_object(row)
            services.append(service)

        return services

    def _create_service_object(self, row: pd.Series) -> Dict:
        """
        Create individual service object from a single row.

        Args:
            row (pd.Series): Single row of service data

        Returns:
            Dict: Service object with all attributes
        """
        # Extract reason codes
        reason_codes = []
        if 'Reason Cd' in row.index:
            reason_cd = str(row['Reason Cd']).strip()
            if reason_cd:
                reason_codes = [reason_cd]

        # Extract remark codes
        remark_codes = []
        if 'Remark Codes' in row.index:
            remark_cd = str(row['Remark Codes']).strip()
            if remark_cd:
                remark_codes = [remark_cd]

        # Clean claim status - remove parenthetical text
        clm_sts = str(row.get('Clm Sts Cod', '')).strip()
        if '(' in clm_sts:
            clm_sts = clm_sts.split('(')[0].strip()

        # Build service object - all values as strings to preserve Excel TEXT formatting
        service = {
            "clm_sts": clm_sts,
            "posting_sts": str(row.get('Posting Sts', '')).strip(),
            "cpt4": str(row.get('CPT4', '')).strip(),
            "txn_status": str(row.get('Txn Status', '')).strip(),
            "description": str(row.get('Description', '')).strip(),
            "bill_amt": str(row.get('Bill Amt', '')).strip(),
            "paid_amt": str(row.get('Pd Amt', '')).strip(),
            "ded_amt": str(row.get('Ded Amt', '')).strip(),
            "codes": reason_codes,
            "remarks": remark_codes
        }

        return service

    def get_data_object(self) -> Dict:
        """
        Get the created data object.

        Returns:
            Dict: Complete data object
        """
        return self.data_object

    def get_missing_encounter_efts(self) -> List[str]:
        """
        Get the list of EFT NUMs that have missing encounters.

        Returns:
            List[str]: List of EFT NUMs with missing encounters
        """
        return self.missing_encounter_efts.copy()

    def get_summary_stats(self) -> Dict:
        """
        Get summary statistics for the dataset.

        Returns:
            Dict: Summary statistics
        """
        stats = {
            'total_rows': len(self.df),
            'total_eft_nums': len(self.data_object),
            'missing_encounter_efts': len(self.missing_encounter_efts),
            'columns': list(self.df.columns),
            'payer_name': self.payer_name
        }

        return stats


class AnalyticsProcessor:
    """
    Processes the final data object to generate specific analytics insights.
    Analyzes Mixed Post payments and encounters for targeted review requirements.
    """

    def __init__(self):
        """Initialize the analytics processor."""
        self.analytics_results = {}

    def analyze_mixed_post_payments(self, data_object: Dict) -> Dict:
        """
        Analyze Mixed Post payments to find specific scenarios for review.

        Args:
            data_object (Dict): Complete data object with tagged payments and encounters

        Returns:
            Dict: Analytics results with specific Mixed Post scenarios
        """
        print(f"📊 Analyzing Mixed Post payments for specific scenarios...")

        # Initialize results structure
        results = {
            "mixed_post_no_plas": [],
            "mixed_post_l6_only": [],
            "charge_mismatch_cpt4_encounters": [],
            "max_encounters_analysis": {
                "not_split_single_payment": None,
                "split_single_eft": None
            }
        }

        # Process all EFTs and payments
        for eft_num, eft in data_object.items():
            # Only analyze not-split EFTs (single payment per EFT)
            if not eft.get("is_split", False):
                for payment_key, payment in eft["payments"].items():
                    # Only analyze Mixed Post payments
                    if payment.get("status") == "Mixed Post":
                        # Check PLA conditions
                        has_l6_plas = len(payment["plas"]["pla_l6"]) > 0
                        has_other_plas = len(payment["plas"]["pla_other"]) > 0
                        has_no_plas = not has_l6_plas and not has_other_plas
                        has_only_l6_plas = has_l6_plas and not has_other_plas

                        encs_to_check_count = len(payment.get("encs_to_check", {}))

                        # Create payment info for analysis
                        payment_info = {
                            "eft_num": eft_num,
                            "practice_id": payment["practice_id"],
                            "payment_num": payment["num"],
                            "payment_amount": payment["amt"],
                            "encs_to_check_count": encs_to_check_count,
                            "total_encounters": len(payment.get("encounters", {})),
                            "pla_l6_count": len(payment["plas"]["pla_l6"]),
                            "pla_other_count": len(payment["plas"]["pla_other"]),
                            "payment_status": payment.get("status"),
                            "encounters_to_check": payment.get("encs_to_check", {})
                        }

                        # Scenario 1: Mixed Post with no PLAs
                        if has_no_plas:
                            results["mixed_post_no_plas"].append(payment_info)

                        # Scenario 2: Mixed Post with only L6 PLAs
                        if has_only_l6_plas:
                            results["mixed_post_l6_only"].append(payment_info)

                        # Check for "Charge mismatch on CPT4" encounters in this payment
                        self._analyze_charge_mismatch_encounters(payment, payment_info, results)

        # Sort results and find extremes
        self._process_analytics_results(results)

        # Analyze max encounters across all EFTs and payments
        self._analyze_max_encounters(data_object, results)

        self.analytics_results = results
        print(f"✅ Mixed Post analytics completed")
        return results

    def _analyze_charge_mismatch_encounters(self, payment: Dict, payment_info: Dict, results: Dict) -> None:
        """
        Analyze encounters in a payment for "Charge mismatch on CPT4" scenarios.

        Args:
            payment (Dict): Payment object
            payment_info (Dict): Payment information for tracking
            results (Dict): Results dictionary to update
        """
        encs_to_check = payment.get("encs_to_check", {})

        for enc_key, enc_check_data in encs_to_check.items():
            encounter_types = enc_check_data.get("types", {})

            # Check if this encounter has "chg_mismatch_cpt4" type
            if "chg_mismatch_cpt4" in encounter_types:
                encounter_info = {
                    "eft_num": payment_info["eft_num"],
                    "practice_id": payment_info["practice_id"],
                    "payment_num": payment_info["payment_num"],
                    "payment_amount": payment_info["payment_amount"],
                    "encounter_num": enc_check_data["num"],
                    "encounter_status": enc_check_data["clm_status"],
                    "encounter_key": enc_key,
                    "encs_to_check_count": payment_info["encs_to_check_count"],
                    "cpt4_codes": encounter_types.get("chg_mismatch_cpt4", [])
                }

                results["charge_mismatch_cpt4_encounters"].append(encounter_info)

    def _analyze_max_encounters(self, data_object: Dict, results: Dict) -> None:
        """
        Find the payment/EFT with the maximum encounters to check across different categories.

        Args:
            data_object (Dict): Complete data object
            results (Dict): Results dictionary to update
        """
        max_not_split_payment = None
        max_split_eft = None

        # Process all EFTs
        for eft_num, eft in data_object.items():
            if eft.get("is_split", False):
                # Split EFT - calculate total encounters to check across all payments
                total_encs_to_check = 0
                for payment in eft["payments"].values():
                    total_encs_to_check += len(payment.get("encs_to_check", {}))

                if total_encs_to_check > 0:
                    eft_info = {
                        "eft_num": eft_num,
                        "total_encs_to_check": total_encs_to_check,
                        "payment_count": len(eft["payments"]),
                        "payments": []
                    }

                    # Add ALL payment details (not just those with encounters to check)
                    for payment in eft["payments"].values():
                        payment_encs = len(payment.get("encs_to_check", {}))
                        eft_info["payments"].append({
                            "practice_id": payment["practice_id"],
                            "payment_num": payment["num"],
                            "encs_to_check": payment_encs,
                            "status": payment.get("status", "Unknown"),
                            "pla_l6_count": len(payment["plas"]["pla_l6"]),
                            "pla_other_count": len(payment["plas"]["pla_other"])
                        })

                    if max_split_eft is None or total_encs_to_check > max_split_eft["total_encs_to_check"]:
                        max_split_eft = eft_info
            else:
                # Not split EFT - single payment
                for payment in eft["payments"].values():
                    encs_to_check_count = len(payment.get("encs_to_check", {}))
                    if encs_to_check_count > 0:
                        payment_info = {
                            "eft_num": eft_num,
                            "practice_id": payment["practice_id"],
                            "payment_num": payment["num"],
                            "encs_to_check_count": encs_to_check_count,
                            "total_encounters": len(payment.get("encounters", {})),
                            "payment_status": payment.get("status", "Unknown"),
                            "pla_l6_count": len(payment["plas"]["pla_l6"]),
                            "pla_other_count": len(payment["plas"]["pla_other"])
                        }

                        if max_not_split_payment is None or encs_to_check_count > max_not_split_payment["encs_to_check_count"]:
                            max_not_split_payment = payment_info

        # Store results
        results["max_encounters_analysis"]["not_split_single_payment"] = max_not_split_payment
        results["max_encounters_analysis"]["split_single_eft"] = max_split_eft

    def _process_analytics_results(self, results: Dict) -> None:
        """
        Process and sort analytics results to find the largest and smallest scenarios.

        Args:
            results (Dict): Results dictionary to process
        """
        # Sort Mixed Post with no PLAs by encounters to check count (descending)
        results["mixed_post_no_plas"].sort(key=lambda x: x["encs_to_check_count"], reverse=True)

        # Sort Mixed Post with only L6 PLAs by encounters to check count (descending)
        results["mixed_post_l6_only"].sort(key=lambda x: x["encs_to_check_count"], reverse=True)

        # Sort charge mismatch encounters by encounters to check count (ascending for smallest)
        results["charge_mismatch_cpt4_encounters"].sort(key=lambda x: x["encs_to_check_count"])

        # Add summary statistics
        results["summary"] = {
            "mixed_post_no_plas_count": len(results["mixed_post_no_plas"]),
            "mixed_post_l6_only_count": len(results["mixed_post_l6_only"]),
            "charge_mismatch_cpt4_count": len(results["charge_mismatch_cpt4_encounters"]),
            "largest_no_plas_encs": results["mixed_post_no_plas"][0]["encs_to_check_count"] if results["mixed_post_no_plas"] else 0,
            "largest_l6_only_encs": results["mixed_post_l6_only"][0]["encs_to_check_count"] if results["mixed_post_l6_only"] else 0,
            "smallest_charge_mismatch_encs": results["charge_mismatch_cpt4_encounters"][0]["encs_to_check_count"] if results["charge_mismatch_cpt4_encounters"] else 0
        }

    def get_analytics_results(self) -> Dict:
        """
        Get the analytics results.

        Returns:
            Dict: Complete analytics results
        """
        return self.analytics_results

    def print_analytics_summary(self) -> None:
        """Print a summary of the analytics results."""
        if not self.analytics_results:
            print("❌ No analytics results available. Run analyze_mixed_post_payments() first.")
            return

        results = self.analytics_results
        summary = results.get("summary", {})

        print(f"\n📊 Mixed Post Analytics Summary:")
        print(f"   • Mixed Post with No PLAs: {summary.get('mixed_post_no_plas_count', 0)} payments")
        if summary.get('largest_no_plas_encs', 0) > 0:
            print(f"     └─ Largest encounters to check: {summary.get('largest_no_plas_encs', 0)}")

        print(f"   • Mixed Post with L6 PLAs Only: {summary.get('mixed_post_l6_only_count', 0)} payments")
        if summary.get('largest_l6_only_encs', 0) > 0:
            print(f"     └─ Largest encounters to check: {summary.get('largest_l6_only_encs', 0)}")

        print(f"   • Charge Mismatch CPT4 Encounters: {summary.get('charge_mismatch_cpt4_count', 0)} encounters")
        if summary.get('smallest_charge_mismatch_encs', 0) > 0:
            print(f"     └─ Smallest encounters to check: {summary.get('smallest_charge_mismatch_encs', 0)}")

        # Show max encounters analysis
        max_analysis = results.get("max_encounters_analysis", {})
        if max_analysis.get("not_split_single_payment"):
            max_not_split = max_analysis["not_split_single_payment"]
            print(f"\n🔍 Max Encounters (Not Split - Single Payment):")
            print(f"   • EFT: {max_not_split['eft_num']}")
            print(f"   • Payment: {max_not_split['practice_id']}_{max_not_split['payment_num']}")
            print(f"   • Encounters to Check: {max_not_split['encs_to_check_count']}")
            print(f"   • Status: {max_not_split['payment_status']}")

        if max_analysis.get("split_single_eft"):
            max_split = max_analysis["split_single_eft"]
            print(f"\n🔍 Max Encounters (Split - Single EFT):")
            print(f"   • EFT: {max_split['eft_num']}")
            print(f"   • Total Encounters to Check: {max_split['total_encs_to_check']}")
            print(f"   • Payments: {max_split['payment_count']}")

        # Show top results from original categories
        if results["mixed_post_no_plas"]:
            top_no_plas = results["mixed_post_no_plas"][0]
            print(f"\n🔍 Largest Mixed Post (No PLAs):")
            print(f"   • EFT: {top_no_plas['eft_num']}")
            print(f"   • Payment: {top_no_plas['practice_id']}_{top_no_plas['payment_num']}")
            print(f"   • Encounters to Check: {top_no_plas['encs_to_check_count']}")

        if results["mixed_post_l6_only"]:
            top_l6_only = results["mixed_post_l6_only"][0]
            print(f"\n🔍 Largest Mixed Post (L6 PLAs Only):")
            print(f"   • EFT: {top_l6_only['eft_num']}")
            print(f"   • Payment: {top_l6_only['practice_id']}_{top_l6_only['payment_num']}")
            print(f"   • Encounters to Check: {top_l6_only['encs_to_check_count']}")

        if results["charge_mismatch_cpt4_encounters"]:
            smallest_charge = results["charge_mismatch_cpt4_encounters"][0]
            print(f"\n🔍 Smallest Charge Mismatch CPT4:")
            print(f"   • EFT: {smallest_charge['eft_num']}")
            print(f"   • Payment: {smallest_charge['practice_id']}_{smallest_charge['payment_num']}")
            print(f"   • Encounter: {smallest_charge['encounter_num']} (Status: {smallest_charge['encounter_status']})")
            print(f"   • Encounters to Check in Payment: {smallest_charge['encs_to_check_count']}")


class EncounterTagger:
    """
    Tags encounters in the data object based on review criteria.
    Updates the data object with encounter tags and encs_to_check.
    """

    def __init__(self):
        """Initialize the encounter tagger."""
        self.encounter_tags = [
            "22_no_123", "22_with_123", "appeal_has_adj", "chg_equal_adj",
            "secondary_n408_pr96", "secondary_co94_oa94", "secondary_mc_tricare_dshs",
            "tertiary", "enc_payer_not_found", "multiple_to_one", "other_not_posted",
            "svc_no_match_clm", "chg_mismatch_cpt4"
        ]

    def tag_encounters(self, data_object: Dict) -> Dict:
        """
        Tag all encounters in the data object.

        Args:
            data_object (Dict): Complete data object with EFTs, payments, encounters

        Returns:
            Dict: Updated data object with encounter tags and encs_to_check
        """
        print(f"🏷️ Tagging encounters for review...")

        for eft_num, eft in data_object.items():
            print(f"   📊 Processing EFT: {eft_num}")

            for payment_key, payment in eft["payments"].items():
                encs_to_check = {}

                for encounter_key, encounter in payment["encounters"].items():
                    # Perform encounter analysis
                    review_data = self.encounter_quick_check(payment, encounter, eft["payer"])

                    if review_data:
                        # Add tags to encounter
                        encounter["tags"] = list(review_data["types"].keys())

                        # Add to encs_to_check
                        encs_to_check[encounter_key] = review_data

                # Sort encounters to check by encounter number and then by status
                sorted_encs_to_check = {}
                if encs_to_check:
                    # Create sorting tuples: (encounter_num, status, original_key)
                    sort_items = []
                    for enc_key, enc_data in encs_to_check.items():
                        enc_num = enc_data.get("num", "")
                        enc_status = enc_data.get("clm_status", "")
                        sort_items.append((enc_num, enc_status, enc_key, enc_data))

                    # Sort by encounter number first, then by status
                    sort_items.sort(key=lambda x: (x[0], x[1]))

                    # Rebuild the sorted dictionary
                    for _, _, enc_key, enc_data in sort_items:
                        sorted_encs_to_check[enc_key] = enc_data

                # Update payment with sorted encs_to_check
                payment["encs_to_check"] = sorted_encs_to_check

        print(f"✅ Encounter tagging completed")
        return data_object

    def encounter_quick_check(self, payment: Dict, encounter: Dict, payer: str) -> Optional[Dict]:
        """
        Perform quick check analysis on a single encounter within a payment.

        Args:
            payment (Dict): Payment object with all encounters
            encounter (Dict): Specific encounter to analyze
            payer (str): Payer name from EFT

        Returns:
            Optional[Dict]: Analysis results for this specific encounter or None if no review needed
        """
        encounter_num = encounter["num"]

        # Define service pairs for charge mismatch checking
        service_pairs = {("99202", "99212"), ("99203", "99213"), ("99204", "99214"), ("99205", "99215"), ("99206", "99216")}

        # Create all_encounters for payment encounters where encounter number matches
        all_encounters = {}
        for enc_key, enc_data in payment["encounters"].items():
            if enc_data["num"] == encounter_num:
                all_encounters[enc_key] = enc_data

        # Filter encounters by claim status for the matching encounter number
        recoupment_encounters = {k: v for k, v in all_encounters.items() if v["status"] == "22"}
        non_recoupment_encounters = {k: v for k, v in all_encounters.items() if v["status"] != "22"}

        primary_encounters = {k: v for k, v in non_recoupment_encounters.items()
                            if v["status"] in ["1", "19"]}
        secondary_encounters = {k: v for k, v in non_recoupment_encounters.items()
                              if v["status"] in ["2", "20"]}
        tertiary_encounters = {k: v for k, v in non_recoupment_encounters.items()
                             if v["status"].startswith("3") or v["status"] == "21"}

        # Get services from each encounter type for the matching encounter number
        recoupment_services = []
        for enc in recoupment_encounters.values():
            recoupment_services.extend(enc["services"])

        primary_services = []
        for enc in primary_encounters.values():
            primary_services.extend(enc["services"])

        secondary_services = []
        for enc in secondary_encounters.values():
            secondary_services.extend(enc["services"])

        tertiary_services = []
        for enc in tertiary_encounters.values():
            tertiary_services.extend(enc["services"])

        # Get CPT4 lists for comparison
        primary_cpt4s = {svc["cpt4"] for svc in primary_services if svc["cpt4"]}
        secondary_cpt4s = {svc["cpt4"] for svc in secondary_services if svc["cpt4"]}
        tertiary_cpt4s = {svc["cpt4"] for svc in tertiary_services if svc["cpt4"]}
        recoupment_cpt4s = {svc["cpt4"] for svc in recoupment_services if svc["cpt4"]}

        # Analyze services in the specific encounter
        encounter_tags_found = {}

        for service in encounter["services"]:
            enc_type = self._analyze_service(
                service, payer, primary_cpt4s, secondary_cpt4s,
                tertiary_cpt4s, recoupment_cpt4s, service_pairs
            )

            if enc_type:
                if enc_type not in encounter_tags_found:
                    encounter_tags_found[enc_type] = []
                encounter_tags_found[enc_type].append(service["cpt4"])

        # Return analysis for this specific encounter
        if encounter_tags_found:
            # Merge services by type (remove duplicates)
            for enc_type in encounter_tags_found:
                encounter_tags_found[enc_type] = list(set(encounter_tags_found[enc_type]))

            return {
                "num": encounter["num"],
                "clm_status": encounter["status"],
                "types": encounter_tags_found
            }
        else:
            return None

    def _analyze_service(self, service: Dict, payer: str, primary_cpt4s: set,
                        secondary_cpt4s: set, tertiary_cpt4s: set, recoupment_cpt4s: set,
                        service_pairs: set) -> Optional[str]:
        """
        Analyze a single service to determine encounter type tag.

        Args:
            service (Dict): Service object
            payer (str): Payer name
            primary_cpt4s (set): Set of primary service CPT4 codes
            secondary_cpt4s (set): Set of secondary service CPT4 codes
            tertiary_cpt4s (set): Set of tertiary service CPT4 codes
            recoupment_cpt4s (set): Set of recoupment service CPT4 codes
            service_pairs (set): Set of service pairs for charge mismatch checking

        Returns:
            Optional[str]: Encounter type tag or None if no tag applies
        """
        description = service.get("description", "").strip()
        posted_sts = service.get("posting_sts", "").strip()
        clm_sts = service.get("clm_sts", "").strip()
        cpt4 = service.get("cpt4", "").strip()
        txn_status = service.get("txn_status", "").strip()
        bill_amt = service.get("bill_amt", "").strip()
        paid_amt = service.get("paid_amt", "").strip()
        codes = service.get("codes", [])
        remarks = service.get("remarks", [])

        # HANDLE NOT POSTED
        if description == "Encounter payer not found.":
            return "enc_payer_not_found"

        if description == "Charge mismatch on amount.":
            return "multiple_to_one"

        if description == "Multiple payments found for the same line item.":
            return "multiple_to_one"

        if description == "Service line payments do not sum to claim level payment.":
            return "svc_no_match_clm"

        if description == "Charge mismatch on CPT4.":
            return "chg_mismatch_cpt4"

        if posted_sts == "Not Posted":
            return "other_not_posted"

        # Get service pairs and opposite CPT4 for use in both recoupment and non-recoupment logic
        opposite_cpt4 = None
        for pair in service_pairs:
            if cpt4 in pair:
                opposite_cpt4 = pair[1] if pair[0] == cpt4 else pair[0]
                break

        # HANDLE RECOUPMENT
        if clm_sts == "22":
            # If opposite CPT4 is in primary, secondary, or tertiary services, return None
            if opposite_cpt4:
                all_other_cpt4s = primary_cpt4s | secondary_cpt4s | tertiary_cpt4s
                if opposite_cpt4 in all_other_cpt4s:
                    return None

            # Otherwise follow the standard 22 checks
            all_other_cpt4s = primary_cpt4s | secondary_cpt4s | tertiary_cpt4s
            if cpt4 in all_other_cpt4s:
                return "22_with_123"
            else:
                return "22_no_123"

        # HANDLE NON-RECOUPMENT
        # Check for CPT4 or opposite CPT4 in recoupment services
        if clm_sts != "22":
            # Skip if current CPT4 or opposite CPT4 is in recoupment services
            if cpt4 in recoupment_cpt4s or (opposite_cpt4 and opposite_cpt4 in recoupment_cpt4s):
                return None

            # Check for appeal with adjustment
            if txn_status == "Appeal" and self._has_adjustment(service):
                return "appeal_has_adj"

            # Check for charge equal to adjustment (but not appeal)
            if self._amounts_equal(bill_amt, self._get_adj_amt(service)) and txn_status != "Appeal":
                return "chg_equal_adj"

        # HANDLE SECONDARY
        # Secondary claim status specific checks
        if clm_sts in ["2", "20"]:
            # Check for N408 + PR96 + (CO45 or OA23)
            if self._has_codes(codes + remarks, ["N408", "PR96"]) and \
               self._has_codes(codes + remarks, ["CO45", "OA23"], any_match=True):
                return "secondary_n408_pr96"

            # Check for (CO94 or OA94) + (CO45 or OA23) + PR96
            if self._has_codes(codes + remarks, ["CO94", "OA94"], any_match=True) and \
               self._has_codes(codes + remarks, ["CO45", "OA23"], any_match=True) and \
               self._has_codes(codes + remarks, ["PR96"]):
                return "secondary_co94_oa94"

            # Check for Medicare/Tricare/DSHS
            if payer in ["Medicare", "Tricare", "DSHS"]:
                return "secondary_mc_tricare_dshs"

        # HANDLE TERTIARY
        if clm_sts.startswith("3") or clm_sts == "21":
            return "tertiary"

        return None

    def _has_adjustment(self, service: Dict) -> bool:
        """Check if service has non-zero adjustment amount."""
        adj_amt = self._get_adj_amt(service)
        try:
            return float(adj_amt) != 0.0
        except (ValueError, TypeError):
            return False

    def _get_adj_amt(self, service: Dict) -> str:
        """Get adjustment amount from service (placeholder - you may need to specify the field)."""
        # You'll need to specify which field contains the adjustment amount
        return service.get("adj_amt", "0")

    def _amounts_equal(self, amount1: str, amount2: str) -> bool:
        """Compare two string amounts for equality."""
        try:
            return float(amount1) == float(amount2)
        except (ValueError, TypeError):
            return False

    def _has_codes(self, code_list: List[str], required_codes: List[str], any_match: bool = False) -> bool:
        """
        Check if required codes are present in the code list.

        Args:
            code_list (List[str]): List of codes to search in
            required_codes (List[str]): List of required codes
            any_match (bool): If True, any code match is sufficient; if False, all codes required

        Returns:
            bool: True if criteria is met
        """
        if any_match:
            return any(code in code_list for code in required_codes)
        else:
            return all(code in code_list for code in required_codes)


class PaymentTagger:
    """
    Tags payments and EFTs in the data object based on payment criteria.
    Updates the data object with payment statuses and EFT split status.
    """

    def __init__(self):
        """Initialize the payment tagger."""
        # Define encounter type categories for payment status determination
        self.not_posted_list = [
            "enc_payer_not_found",
            "multiple_to_one",
            "other_not_posted",
            "svc_no_match_clm",
            "chg_mismatch_cpt4"
        ]

        self.check_ng_and_data = [
            "secondary_co94_oa94",
            "secondary_mc_tricare_dshs",
            "tertiary"
        ]

        self.reversals = [
            "22_no_123",
            "22_with_123"
        ]

        # Define Quick Post specific encounter types
        self.quick_post_types = [
            "appeal_has_adj",
            "chg_equal_adj",
            "secondary_n408_pr96"
        ]

    def tag_payments(self, data_object: Dict) -> Dict:
        """
        Tag all payments and EFTs in the data object.

        Args:
            data_object (Dict): Complete data object with tagged encounters

        Returns:
            Dict: Updated data object with payment statuses and EFT split status
        """
        print(f"🏷️ Tagging payments and EFTs...")

        for eft_num, eft in data_object.items():
            print(f"   📊 Processing EFT: {eft_num}")

            # Tag EFT as split or not split based on number of payments
            eft["is_split"] = len(eft["payments"]) > 1

            # Tag each payment with status
            for payment_key, payment in eft["payments"].items():
                payment["status"] = self._determine_payment_status(payment)

        print(f"✅ Payment and EFT tagging completed")
        return data_object

    def _determine_payment_status(self, payment: Dict) -> str:
        """
        Determine payment status based on PLAs and encounters to check.

        Payment Statuses (in order of priority):
        1. "Immediate Post": no plas, no encs_to_check
        2. "PLA Only": has plas, no encs_to_check
        3. "Mixed Post": has at least one enc_to_check in not_posted_list
        4. "Quick Post": no plas, has ONLY quick_post_types encounters
        5. "Full Post": no plas, has encounters in check_ng_and_data or reversals (but not not_posted_list)
        6. "Unknown": any payment not fitting above categories

        Args:
            payment (Dict): Payment object

        Returns:
            str: Payment status
        """
        # Check if payment has PLAs
        has_plas = (len(payment["plas"]["pla_l6"]) > 0 or
                   len(payment["plas"]["pla_other"]) > 0)

        # Get all encounter types that need to be checked
        encs_to_check = payment.get("encs_to_check", {})

        # 1. Immediate Post: no plas, no encounters to check
        if not has_plas and not encs_to_check:
            return "Immediate Post"

        # 2. PLA Only: has plas, no encounters to check
        if has_plas and not encs_to_check:
            return "PLA Only"

        # If there are encounters to check, get all encounter types
        if encs_to_check:
            all_encounter_types = set()
            for enc_data in encs_to_check.values():
                all_encounter_types.update(enc_data.get("types", {}).keys())

            # 3. Mixed Post: has at least one enc_to_check in not_posted_list
            if any(enc_type in self.not_posted_list for enc_type in all_encounter_types):
                return "Mixed Post"

            # For remaining checks, payment should not have PLAs
            if not has_plas:
                # 4. Quick Post: no plas, has ONLY quick_post_types encounters
                if all_encounter_types and all_encounter_types.issubset(set(self.quick_post_types)):
                    return "Quick Post"

                # 5. Full Post: no plas, has encounters in check_ng_and_data or reversals
                has_check_ng_or_reversals = (
                    any(enc_type in self.check_ng_and_data for enc_type in all_encounter_types) or
                    any(enc_type in self.reversals for enc_type in all_encounter_types)
                )
                if has_check_ng_or_reversals:
                    return "Full Post"

        # 6. Fallback for any payment not fitting the above categories
        return "Unknown"
