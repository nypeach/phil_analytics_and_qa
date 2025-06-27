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
        Get PLA rows where Description begins with "Provider Level Adjustment".

        Args:
            pmt_rows (pd.DataFrame): Rows filtered by PMT NUM

        Returns:
            pd.DataFrame: Filtered dataframe with PLA rows
        """
        if 'Description' not in pmt_rows.columns:
            return pd.DataFrame()

        pla_mask = pmt_rows['Description'].astype(str).str.startswith('Provider Level Adjustment', na=False)
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

        Returns:
            str: Markdown content
        """
        markdown_content = []
        markdown_content.append(f"# {self.payer_name} EFTs Analysis\n\n")

        # Get all unique EFT NUMs
        eft_nums = self.df['EFT NUM'].astype(str).unique()
        eft_nums = [eft for eft in eft_nums if eft and eft.strip() != '']

        for eft_num in sorted(eft_nums):
            markdown_content.append(f"<details markdown=\"1\">\n<summary>{eft_num}</summary>\n\n")

            # Get EFT rows
            eft_rows = self.get_eft_num_rows(eft_num)
            pmt_groups = self.get_pmt_num_rows(eft_rows)

            for pmt_num, pmt_rows in pmt_groups.items():
                # Extract practice_id from pmt_num (format is practice_id_check_number)
                parts = pmt_num.split('_')
                practice_id = parts[0] if len(parts) > 0 else pmt_num

                markdown_content.append(f"<details markdown=\"1\">\n<summary>{practice_id}_{pmt_num}</summary>\n\n")

                # PLA Analysis
                pla_rows = self.get_pla_rows(pmt_rows)
                pla_count = len(pla_rows)

                if pla_count > 0:
                    pla_l6_count = len(pla_rows[pla_rows['Description'].astype(str).str.contains('L6', na=False)])
                    pla_other_count = pla_count - pla_l6_count
                else:
                    pla_l6_count = 0
                    pla_other_count = 0

                markdown_content.append(f"<details markdown=\"1\">\n<summary>PLAs:</summary>\n\n")
                markdown_content.append(f"- Total: {pla_count}\n")
                markdown_content.append(f"- L6: {pla_l6_count}\n")
                markdown_content.append(f"- Other: {pla_other_count}\n\n")
                markdown_content.append("</details>\n\n")

                # Encounter Analysis
                encounter_groups = self.get_encounter_rows(pmt_rows)
                markdown_content.append(f"<details markdown=\"1\">\n<summary>Encounters:</summary>\n\n")

                if encounter_groups:
                    for enc_key, enc_rows in encounter_groups.items():
                        # Extract Enc Nbr and Clm Sts from the key
                        if '_' in enc_key:
                            enc_nbr, clm_sts = enc_key.split('_', 1)
                            markdown_content.append(f"<details><summary>ENC NBR: {enc_nbr} CLM STS: {clm_sts}</summary></details>\n")
                        else:
                            markdown_content.append(f"<details><summary>ENC NBR: {enc_key}</summary></details>\n")

                markdown_content.append("\n</details>\n\n")
                markdown_content.append("</details>\n\n")

            markdown_content.append("</details>\n\n")

        return ''.join(markdown_content)

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