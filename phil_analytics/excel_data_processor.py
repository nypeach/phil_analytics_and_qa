import pandas as pd
import openpyxl
from pathlib import Path
from typing import Dict, List, Optional, Union
from collections import defaultdict
import re

class ExcelDataProcessor:
    """
    Class to process Excel spreadsheet data while maintaining text formatting.
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

        except Exception as e:
            print(f"Error loading data: {e}")
            raise

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

    def get_reason_codes(self, service_rows: pd.DataFrame) -> List[str]:
        """
        Get reason codes from service rows.

        Args:
            service_rows (pd.DataFrame): Service rows

        Returns:
            List[str]: List of reason codes
        """
        if 'Reason Cd' not in service_rows.columns:
            return []

        reason_codes = service_rows['Reason Cd'].astype(str).str.strip()
        return [code for code in reason_codes.unique() if code and code != '']

    def get_remark_codes(self, service_rows: pd.DataFrame) -> List[str]:
        """
        Get remark codes from service rows.

        Args:
            service_rows (pd.DataFrame): Service rows

        Returns:
            List[str]: List of remark codes
        """
        if 'Remark Codes' not in service_rows.columns:
            return []

        remark_codes = service_rows['Remark Codes'].astype(str).str.strip()
        return [code for code in remark_codes.unique() if code and code != '']

    def generate_test_logic_markdown(self) -> str:
        """
        Generate nested markdown file with GitHub-style toggles for test logic.
        Uses same structure as data structure markdown but only shows encounters that need review.

        Returns:
            str: Markdown content
        """
        # Import here to avoid circular imports
        from .data_analysis import EncounterReviewAnalyzer, DataStructureBuilder

        markdown_content = []
        markdown_content.append(f"# {self.payer_name} EFTs Analysis\n\n")

        # Initialize encounter analyzer and data structure builder
        encounter_analyzer = EncounterReviewAnalyzer()
        data_builder = DataStructureBuilder(self.payer_name)

        # Build complete structure first
        efts = {}
        eft_nums = self.df['EFT NUM'].astype(str).unique()
        eft_nums = [eft for eft in eft_nums if eft and eft.strip() != '']

        # Build complete EFT structure with encounter analysis
        for eft_num in eft_nums:
            eft_rows = self.get_eft_num_rows(eft_num)
            pmt_groups = self.get_pmt_num_rows(eft_rows)

            # Build EFT object
            eft_obj = data_builder.build_eft_object(eft_num, eft_rows, pmt_groups)

            # Build payment objects with encounter analysis
            enhanced_payments = {}
            for pmt_key, pmt_rows in pmt_groups.items():
                pla_rows = self.get_pla_rows(pmt_rows)
                enc_groups = self.get_encounter_rows(pmt_rows)

                # Build payment object
                payment_obj = data_builder.build_payment_object(pmt_key, pmt_rows, pla_rows, enc_groups)

                # Build complete encounter objects with services
                enhanced_encounters = {}
                for enc_key, enc_rows in enc_groups.items():
                    service_rows = self.get_service_rows(enc_rows)
                    encounter_obj = data_builder.build_encounter_object(enc_key, enc_rows, service_rows)
                    enhanced_encounters[enc_key] = encounter_obj

                payment_obj["encounters"] = enhanced_encounters

                # Perform encounter analysis
                encs_to_check = encounter_analyzer.encounter_quick_check(payment_obj, eft_obj["payer"])
                payment_obj["encs_to_check"] = encs_to_check

                enhanced_payments[pmt_key] = payment_obj

            eft_obj["payments"] = enhanced_payments
            efts[eft_num] = eft_obj

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
            self._generate_eft_analysis_section(eft, eft_num, markdown_content)

        markdown_content.append("</details>\n\n")

        # Generate "EFTs - Split" section as toggle
        split_title = f"EFTs - Split ({len(split_efts)})"
        markdown_content.append(f"<details markdown=\"1\">\n<summary>{split_title}</summary>\n\n")

        for eft_num in sorted(split_efts.keys()):
            eft = split_efts[eft_num]
            self._generate_eft_analysis_section(eft, eft_num, markdown_content)

        markdown_content.append("</details>\n\n")

        return ''.join(markdown_content)

    def _generate_eft_analysis_section(self, eft: Dict, eft_num: str, markdown_content: List[str]) -> None:
        """
        Generate the markdown section for a single EFT analysis (similar to data structure but filtered).

        Args:
            eft (Dict): EFT object with analysis results
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

            # Encounters section - only show encounters that need review
            encs_to_check = payment.get("encs_to_check", {})
            encounters_title = f"Encounters ({len(encs_to_check)})"
            markdown_content.append(f"<details markdown=\"1\">\n<summary>{encounters_title}</summary>\n\n")

            if encs_to_check:
                for enc_key, enc_check_data in encs_to_check.items():
                    # Get full encounter data for service count
                    full_encounter = payment["encounters"].get(enc_key, {})
                    service_count = len(full_encounter.get("services", []))

                    encounter_title = f"Encounter: {enc_check_data['num']} (Status: {enc_check_data['clm_status']}, Services: {service_count})"
                    markdown_content.append(f"<details markdown=\"1\">\n<summary>{encounter_title}</summary>\n\n")

                    # Add encounter analysis summary
                    markdown_content.append("**Review Required:**\n")
                    for enc_type, cpt4_list in enc_check_data['types'].items():
                        cpt4_str = ", ".join(cpt4_list) if cpt4_list else "No CPT4"
                        markdown_content.append(f"- {enc_type}: {cpt4_str}\n")
                    markdown_content.append("\n")

                    markdown_content.append("</details>\n\n")
            else:
                markdown_content.append("No encounters require review.\n\n")

            markdown_content.append("</details>\n\n")
            markdown_content.append("</details>\n\n")

        markdown_content.append("</details>\n\n")

    def generate_data_structure_markdown(self, output_dir: str = ".") -> str:
        """
        Generate data structure markdown using the DataStructureBuilder.

        Args:
            output_dir (str): Directory to save the markdown file

        Returns:
            str: Path to the saved markdown file
        """
        # Import here to avoid circular imports
        from .data_analysis import DataStructureBuilder

        print(f"🏗️ Building data structure for {self.payer_name}...")

        # Create data structure builder
        builder = DataStructureBuilder(self.payer_name)

        # Build complete structure using the Excel processor's row identification
        efts = {}

        # Get all unique EFT NUMs
        eft_nums = self.df['EFT NUM'].astype(str).unique()
        eft_nums = [eft for eft in eft_nums if eft and eft.strip() != '']

        for eft_num in eft_nums:
            # Get EFT rows and payment groups using our methods
            eft_rows = self.get_eft_num_rows(eft_num)
            pmt_groups = self.get_pmt_num_rows(eft_rows)

            # Build EFT object
            eft_obj = builder.build_eft_object(eft_num, eft_rows, pmt_groups)

            # Build payment objects with their encounters and services
            enhanced_payments = {}
            for pmt_key, pmt_rows in pmt_groups.items():
                # Get PLA rows and encounter groups for this payment
                pla_rows = self.get_pla_rows(pmt_rows)
                enc_groups = self.get_encounter_rows(pmt_rows)

                # Build payment object
                payment_obj = builder.build_payment_object(pmt_key, pmt_rows, pla_rows, enc_groups)

                # Build encounter objects with their services
                enhanced_encounters = {}
                for enc_key, enc_rows in enc_groups.items():
                    service_rows = self.get_service_rows(enc_rows)
                    encounter_obj = builder.build_encounter_object(enc_key, enc_rows, service_rows)
                    enhanced_encounters[enc_key] = encounter_obj

                payment_obj["encounters"] = enhanced_encounters
                enhanced_payments[pmt_key] = payment_obj

            eft_obj["payments"] = enhanced_payments
            efts[eft_num] = eft_obj

        # Generate and save markdown
        markdown_path = builder.generate_data_structure_markdown(efts, output_dir)

        return markdown_path

    def save_test_logic_markdown(self, output_dir: str = ".") -> str:
        """
        Save the test logic markdown to a file.

        Args:
            output_dir (str): Directory to save the markdown file

        Returns:
            str: Path to the saved file
        """
        markdown_content = self.generate_test_logic_markdown()
        output_path = Path(output_dir) / f"{self.payer_name}_efts.md"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        print(f"Test logic markdown saved to: {output_path}")
        return str(output_path)

    def save_data_structure_markdown(self, output_dir: str = ".") -> str:
        """
        Save the data structure markdown to a file.

        Args:
            output_dir (str): Directory to save the markdown file

        Returns:
            str: Path to the saved file
        """
        return self.generate_data_structure_markdown(output_dir)

    def save_both_markdown_files(self, output_dir: str = ".") -> Dict[str, str]:
        """
        Save both the test logic and data structure markdown files.

        Args:
            output_dir (str): Directory to save the markdown files

        Returns:
            Dict[str, str]: Paths to both saved files
        """
        print(f"📝 Generating both markdown files for {self.payer_name}...")

        # Save test logic markdown
        test_logic_path = self.save_test_logic_markdown(output_dir)

        # Save data structure markdown
        data_structure_path = self.generate_data_structure_markdown(output_dir)

        return {
            "test_logic": test_logic_path,
            "data_structure": data_structure_path
        }

    def get_all_eft_nums(self) -> List[str]:
        """Get all unique EFT numbers from the dataset."""
        eft_nums = self.df['EFT NUM'].astype(str).unique()
        return [eft for eft in eft_nums if eft and eft.strip() != '']

    def get_summary_stats(self) -> Dict:
        """
        Get summary statistics for the dataset.

        Returns:
            Dict: Summary statistics
        """
        stats = {
            'total_rows': len(self.df),
            'total_eft_nums': len(self.get_all_eft_nums()),
            'columns': list(self.df.columns),
            'payer_name': self.payer_name
        }

        return stats