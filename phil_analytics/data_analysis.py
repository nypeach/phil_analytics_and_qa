"""
PHIL Analytics and QA Library - Data Analysis Module

This module provides data structure building and analysis functions for payment data.
All functions are designed to handle Excel TEXT formatting as strings, even when
the data appears to be numeric.
"""

import pandas as pd
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict
from pathlib import Path
import re


class DataStructureBuilder:
    """
    Class to build structured data objects from Excel payment data using the
    row groupings identified by ExcelDataProcessor.

    Creates nested data structure with EFT -> Payment -> Encounter -> Service hierarchy.
    All data is preserved as strings to maintain Excel TEXT formatting.
    """

    def __init__(self, payer_folder: str):
        """
        Initialize the data structure builder.

        Args:
            payer_folder (str): Name of the payer folder being processed
        """
        self.payer_folder = payer_folder
        self.efts = {}

    def build_eft_object(self, eft_num: str, eft_rows: pd.DataFrame,
                        pmt_groups: Dict[str, pd.DataFrame]) -> Dict:
        """
        Build EFT object from the rows and payment groups identified by ExcelDataProcessor.

        Args:
            eft_num (str): EFT number
            eft_rows (pd.DataFrame): All rows for this EFT
            pmt_groups (Dict[str, pd.DataFrame]): Payment groups within this EFT

        Returns:
            Dict: EFT object with all attributes
        """
        # Get payer from PAYER FOLDER column if available, otherwise use passed payer_folder
        payer = self.payer_folder
        if 'PAYER FOLDER' in eft_rows.columns:
            payer_values = eft_rows['PAYER FOLDER'].astype(str).unique()
            payer_values = [p for p in payer_values if p and p.strip() != '']
            if payer_values:
                payer = payer_values[0]  # Use first non-empty payer folder value

        # Build EFT object
        eft = {
            "eft_num": str(eft_num),
            "payer": str(payer),
            "payments": list(pmt_groups.keys()),
            "is_split": len(pmt_groups) > 1
        }

        return eft

    def build_payment_object(self, payment_key: str, pmt_rows: pd.DataFrame,
                           pla_rows: pd.DataFrame, enc_groups: Dict[str, pd.DataFrame]) -> Dict:
        """
        Build payment object from the rows identified by ExcelDataProcessor.

        Args:
            payment_key (str): Payment key (practice_id_check_number)
            pmt_rows (pd.DataFrame): All rows for this payment
            pla_rows (pd.DataFrame): PLA rows for this payment
            enc_groups (Dict[str, pd.DataFrame]): Encounter groups within this payment

        Returns:
            Dict: Payment object with all attributes
        """
        # Extract practice_id and payment number from key
        parts = payment_key.split('_')
        practice_id = parts[0] if len(parts) > 0 else ""
        pmt_num = parts[1] if len(parts) > 1 else ""

        # Build PLAs
        plas = self.build_pla_objects(pla_rows)

        # Build payment object
        payment = {
            "practice_id": str(practice_id),
            "num": str(pmt_num),
            "status": "",  # Will be determined by analysis
            "plas": plas,
            "encounters": list(enc_groups.keys())
        }

        return payment

    def build_pla_objects(self, pla_rows: pd.DataFrame) -> Dict[str, List]:
        """
        Build PLA objects from PLA rows identified by ExcelDataProcessor.

        Since PLA rows are already filtered by the correct criteria, we just need to
        separate L6 vs other PLAs. L6 PLAs are the ones that match condition 2:
        - Clm Nbr = "Provider Lvl Adj" AND Enc Nbr != "" AND Description contains "L6"

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

    def build_encounter_object(self, encounter_key: str, enc_rows: pd.DataFrame,
                             service_rows: pd.DataFrame) -> Dict:
        """
        Build encounter object from the rows identified by ExcelDataProcessor.

        Args:
            encounter_key (str): Encounter key (enc_nbr_clm_sts)
            enc_rows (pd.DataFrame): All rows for this encounter
            service_rows (pd.DataFrame): Service rows for this encounter

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

        # Build services
        services = self.build_service_objects(service_rows)

        # Build encounter object
        encounter = {
            "num": str(enc_nbr),
            "status": str(clm_sts),
            "services": services
        }

        return encounter

    def build_service_objects(self, service_rows: pd.DataFrame) -> List[Dict]:
        """
        Build service objects from service rows identified by ExcelDataProcessor.

        Args:
            service_rows (pd.DataFrame): Service rows (rows with CPT4 codes)

        Returns:
            List[Dict]: List of service objects
        """
        services = []

        for _, row in service_rows.iterrows():
            service = self.build_service_object(row)
            services.append(service)

        return services

    def build_service_object(self, row: pd.Series) -> Dict:
        """
        Build individual service object from a single row.

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

    def generate_data_structure_markdown(self, efts: Dict[str, Dict], output_dir: str = ".") -> str:
        """
        Generate markdown file showing the data structure using HTML details/summary.
        Organizes EFTs by split status: Not Split first, then Split.

        Args:
            efts (Dict[str, Dict]): Complete EFT structure
            output_dir (str): Directory to save the markdown file

        Returns:
            str: Path to the saved markdown file
        """
        print(f"📝 Generating data structure markdown...")

        markdown_content = []
        markdown_content.append(f"# {self.payer_folder} Data Structure\n\n")
        markdown_content.append(f"This file shows the nested data structure captured from the payment data.\n\n")

        # Separate EFTs by split status
        not_split_efts = {}
        split_efts = {}

        for eft_num, eft in efts.items():
            if eft['is_split']:
                split_efts[eft_num] = eft
            else:
                not_split_efts[eft_num] = eft

        # Generate "EFTs - Not Split" section as toggle
        not_split_title = f"EFTs - Not Split ({len(not_split_efts)})"
        markdown_content.append(f"<details markdown=\"1\">\n<summary>{not_split_title}</summary>\n\n")

        for eft_num in sorted(not_split_efts.keys()):
            eft = not_split_efts[eft_num]
            self._generate_eft_section(eft, eft_num, markdown_content)

        markdown_content.append("</details>\n\n")

        # Generate "EFTs - Split" section as toggle
        split_title = f"EFTs - Split ({len(split_efts)})"
        markdown_content.append(f"<details markdown=\"1\">\n<summary>{split_title}</summary>\n\n")

        for eft_num in sorted(split_efts.keys()):
            eft = split_efts[eft_num]
            self._generate_eft_section(eft, eft_num, markdown_content)

        markdown_content.append("</details>\n\n")

        # Save markdown file
        output_path = Path(output_dir) / f"{self.payer_folder}_data_structure.md"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(''.join(markdown_content))

        print(f"   ✅ Data structure markdown saved to: {output_path}")
        return str(output_path)

    def _generate_eft_section(self, eft: Dict, eft_num: str, markdown_content: List[str]) -> None:
        """
        Generate the markdown section for a single EFT.

        Args:
            eft (Dict): EFT object
            eft_num (str): EFT number
            markdown_content (List[str]): List to append markdown content to
        """
        eft_title = f"EFT: {eft_num} (Payer: {eft['payer']}, Split: {eft['is_split']}, Payments: {len(eft['payments'])})"
        markdown_content.append(f"<details markdown=\"1\">\n<summary>{eft_title}</summary>\n\n")

        # Payment level
        for payment_key, payment in eft["payments"].items():
            payment_title = f"Payment: {payment_key} (Practice: {payment['practice_id']}, Num: {payment['num']})"
            markdown_content.append(f"<details markdown=\"1\">\n<summary>{payment_title}</summary>\n\n")

            # PLA section
            pla_l6_count = len(payment["plas"]["pla_l6"])
            pla_other_count = len(payment["plas"]["pla_other"])
            pla_title = f"PLAs (L6: {pla_l6_count}, Other: {pla_other_count})"
            markdown_content.append(f"<details markdown=\"1\">\n<summary>{pla_title}</summary>\n\n")

            if payment["plas"]["pla_l6"]:
                markdown_content.append("**L6 PLAs:**\n")
                for pla in payment["plas"]["pla_l6"]:
                    markdown_content.append(f"- {pla}\n")
                markdown_content.append("\n")

            if payment["plas"]["pla_other"]:
                markdown_content.append("**Other PLAs:**\n")
                for pla in payment["plas"]["pla_other"]:
                    markdown_content.append(f"- {pla}\n")
                markdown_content.append("\n")

            markdown_content.append("</details>\n\n")

            # Encounters section
            encounter_count = len(payment["encounters"])
            encounters_title = f"Encounters ({encounter_count})"
            markdown_content.append(f"<details markdown=\"1\">\n<summary>{encounters_title}</summary>\n\n")

            for encounter_key, encounter in payment["encounters"].items():
                service_count = len(encounter["services"])
                encounter_title = f"Encounter: {encounter['num']} (Status: {encounter['status']}, Services: {service_count})"
                markdown_content.append(f"<details markdown=\"1\">\n<summary>{encounter_title}</summary>\n\n")

                # Services section
                if encounter["services"]:
                    markdown_content.append("**Services:**\n")
                    for service in encounter["services"]:
                        service_info = f"CPT4: {service['cpt4']}, Bill: {service['bill_amt']}, Paid: {service['paid_amt']}"
                        if service['codes']:
                            service_info += f", Codes: {', '.join(service['codes'])}"
                        if service['remarks']:
                            service_info += f", Remarks: {', '.join(service['remarks'])}"
                        markdown_content.append(f"- {service_info}\n")
                    markdown_content.append("\n")

                markdown_content.append("</details>\n\n")

            markdown_content.append("</details>\n\n")
            markdown_content.append("</details>\n\n")

        markdown_content.append("</details>\n\n")


class EncounterReviewAnalyzer:
    """
    Class to analyze encounters and determine which ones need review vs. which ones don't.

    This class provides methods to quickly identify encounters that require manual review
    based on various business rules and data patterns.
    """

    def __init__(self):
        """Initialize the encounter review analyzer."""
        self.review_required_encounters = set()
        self.no_review_required_encounters = set()
        self.review_criteria = {}

    def analyze_encounter_for_review(self, enc_rows: pd.DataFrame, enc_key: str) -> Dict[str, any]:
        """
        Analyze a single encounter to determine if it needs review.

        Args:
            enc_rows (pd.DataFrame): Rows for a specific encounter
            enc_key (str): Encounter key (format: enc_nbr_clm_sts)

        Returns:
            Dict[str, any]: Analysis results including review status and reasons
        """
        # Stub - will implement logic to determine review requirements
        pass


# Utility functions for string-based operations
def safe_string_to_decimal(value: str, default: str = "0.00") -> str:
    """
    Safely convert string that looks like a number to a standardized decimal string.

    Args:
        value (str): String value that may represent a number
        default (str): Default value if conversion fails

    Returns:
        str: Standardized decimal string
    """
    # Stub - will handle string-to-decimal conversion while preserving string format
    pass


def compare_string_amounts(amount1: str, amount2: str) -> Dict[str, any]:
    """
    Compare two string amounts and return comparison results.

    Args:
        amount1 (str): First amount as string
        amount2 (str): Second amount as string

    Returns:
        Dict[str, any]: Comparison results including difference and relationship
    """
    # Stub - will compare amounts while treating them as strings
    pass