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
        self.encounter_tags = [
            "22_no_123", "22_with_123", "appeal_has_adj", "chg_equal_adj",
            "secondary_n408_pr96", "secondary_co94_oa94", "secondary_mc_tricare_dshs",
            "tertiary", "enc_payer_not_found", "multiple_to_one", "other_not_posted",
            "svc_no_match_clm"
        ]
        self.review_required_encounters = set()
        self.no_review_required_encounters = set()
        self.review_criteria = {}

    def encounter_quick_check(self, payment: Dict, encounter: Dict, payer: str) -> Dict[str, any]:
        """
        Perform quick check analysis on a single encounter within a payment.

        Args:
            payment (Dict): Payment object with all encounters
            encounter (Dict): Specific encounter to analyze
            payer (str): Payer name from EFT

        Returns:
            Dict[str, any]: Analysis results for this specific encounter
        """
        encounter_num = encounter["num"]
        print(f"🔍 Analyzing encounter {encounter_num} for review requirements")

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
                tertiary_cpt4s, recoupment_cpt4s
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
                        secondary_cpt4s: set, tertiary_cpt4s: set, recoupment_cpt4s: set) -> str:
        """
        Analyze a single service to determine encounter type tag.

        Args:
            service (Dict): Service object
            payer (str): Payer name
            primary_cpt4s (set): Set of primary service CPT4 codes
            secondary_cpt4s (set): Set of secondary service CPT4 codes
            tertiary_cpt4s (set): Set of tertiary service CPT4 codes
            recoupment_cpt4s (set): Set of recoupment service CPT4 codes

        Returns:
            str: Encounter type tag or None if no tag applies
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

        if posted_sts == "Not Posted":
            return "other_not_posted"

        # HANDLE REPROCESSED
        if clm_sts == "22":
            all_other_cpt4s = primary_cpt4s | secondary_cpt4s | tertiary_cpt4s
            if cpt4 in all_other_cpt4s:
                return "22_with_123"
            else:
                return "22_no_123"

        # HANDLE SECONDARY
        if clm_sts != "22":
            # Skip if there's a matching CPT4 in recoupment services
            if cpt4 in recoupment_cpt4s:
                return None

            # Check for appeal with adjustment
            if txn_status == "Appeal" and self._has_adjustment(service):
                return "appeal_has_adj"

            # Check for charge equal to adjustment (but not appeal)
            if self._amounts_equal(bill_amt, self._get_adj_amt(service)) and txn_status != "Appeal":
                return "chg_equal_adj"

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

    def generate_encounter_summary_markdown(self, encs_to_check: Dict[str, Dict]) -> str:
        """
        Generate markdown summary for encounters to check.

        Args:
            encs_to_check (Dict[str, Dict]): Encounters that need review

        Returns:
            str: Markdown content for encounter summary
        """
        if not encs_to_check:
            return ""

        markdown_content = []

        for enc_key, enc_data in encs_to_check.items():
            markdown_content.append(f"{enc_data['num']}_{enc_data['clm_status']}:\n")

            for enc_type, cpt4_list in enc_data['types'].items():
                cpt4_str = ", ".join(cpt4_list) if cpt4_list else "No CPT4"
                markdown_content.append(f"- {enc_type}: {cpt4_str}\n")

            markdown_content.append("\n")

        return "".join(markdown_content)

    def analyze_encounter_for_review(self, enc_rows: pd.DataFrame, enc_key: str) -> Dict[str, any]:
        """
        Analyze a single encounter to determine if it needs review.

        Args:
            enc_rows (pd.DataFrame): Rows for a specific encounter
            enc_key (str): Encounter key (format: enc_nbr_clm_sts)

        Returns:
            Dict[str, any]: Analysis results including review status and reasons
        """
        # This method will be used for more detailed analysis later
        # For now, use the encounter_quick_check method
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