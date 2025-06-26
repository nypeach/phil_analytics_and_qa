"""
PHIL Analytics and QA Library - Utility Functions

This module provides shared utility functions used across the library,
including mapping file operations and common data processing utilities.
"""

import pandas as pd
import os
from typing import Dict, Tuple
from .exceptions import FileNotFoundError, MappingError


class MappingLoader:
    """
    Handles loading and managing mapping data from the Proliance mapping file.

    This class centralizes mapping operations that are used throughout the pipeline.
    """

    def __init__(self, mapping_file: str = "Proliance Mapping.xlsx"):
        """
        Initialize the mapping loader.

        Args:
            mapping_file (str): Path to the Proliance mapping file
        """
        self.mapping_file = mapping_file
        self.practice_mapping = {}
        self.payer_df = pd.DataFrame()
        self._mappings_loaded = False

    def load_mappings(self) -> Tuple[Dict[str, str], pd.DataFrame]:
        """
        Load practice and payer mappings from the mapping file.

        Returns:
            Tuple[Dict[str, str], pd.DataFrame]: Practice mapping dict and payer DataFrame

        Raises:
            FileNotFoundError: If mapping file doesn't exist
            MappingError: If mapping sheets cannot be read
        """
        print(f"🗺️ Loading mapping data from: {self.mapping_file}")

        if not os.path.exists(self.mapping_file):
            raise FileNotFoundError(
                self.mapping_file,
                file_type="mapping file",
                expected_location="Current working directory"
            )

        # Load practice mappings
        self._load_practice_mappings()

        # Load payer mappings
        self._load_payer_mappings()

        self._mappings_loaded = True
        print(f"✅ All mapping data loaded successfully")

        return self.practice_mapping, self.payer_df

    def _load_practice_mappings(self) -> None:
        """Load practice mappings from Waystar Practices sheet."""
        print(f"   📋 Reading Waystar Practices sheet...")

        try:
            practice_df = pd.read_excel(
                self.mapping_file,
                sheet_name="Waystar Practices",
                dtype=str,                    # Keep all as strings
                keep_default_na=False,        # Don't convert to NaN
                na_filter=False              # Don't filter NA values
            ).fillna("")

            self.practice_mapping = {}
            for _, row in practice_df.iterrows():
                ws_id = str(row.iloc[0]).strip()  # Column A (WS_ID)
                app_id = str(row.iloc[3]).strip()  # Column D (APP_ID)
                if ws_id and app_id and ws_id != "WS_ID":  # Skip header row
                    self.practice_mapping[ws_id] = app_id

            print(f"   ✅ Loaded {len(self.practice_mapping)} practice mappings")
            print(f"   📝 All mapping data preserved as text")

        except Exception as e:
            raise MappingError(
                f"Could not read Waystar Practices sheet: {e}",
                mapping_type="practice",
                sheet_name="Waystar Practices"
            )

    def _load_payer_mappings(self) -> None:
        """Load payer mappings from Waystar Payers sheet."""
        print(f"   📋 Reading Waystar Payers sheet...")

        try:
            self.payer_df = pd.read_excel(
                self.mapping_file,
                sheet_name="Waystar Payers",
                dtype=str,                    # Keep all as strings
                keep_default_na=False,        # Don't convert to NaN
                na_filter=False              # Don't filter NA values
            ).fillna("")

            print(f"   ✅ Loaded {len(self.payer_df)} payer mappings")
            print(f"   📝 All payer data preserved as text")

        except Exception as e:
            raise MappingError(
                f"Could not read Waystar Payers sheet: {e}",
                mapping_type="payer",
                sheet_name="Waystar Payers"
            )

    def get_practice_mapping(self) -> Dict[str, str]:
        """
        Get practice mapping dictionary.

        Returns:
            Dict[str, str]: WS_ID to APP_ID mapping
        """
        if not self._mappings_loaded:
            self.load_mappings()
        return self.practice_mapping

    def get_payer_mapping(self) -> pd.DataFrame:
        """
        Get payer mapping DataFrame.

        Returns:
            pd.DataFrame: Payer mapping data
        """
        if not self._mappings_loaded:
            self.load_mappings()
        return self.payer_df

    def lookup_practice_id(self, ws_id: str) -> str:
        """
        Look up APP_ID for a given WS_ID.

        Args:
            ws_id (str): Waystar ID to look up

        Returns:
            str: Corresponding APP_ID or empty string if not found
        """
        if not self._mappings_loaded:
            self.load_mappings()
        return self.practice_mapping.get(str(ws_id).strip(), "")

    def lookup_payer_folder(self, waystar_id: str, exclude_zelis: bool = True) -> str:
        """
        Look up payer folder for a given Waystar ID.

        Args:
            waystar_id (str): Waystar ID to look up
            exclude_zelis (bool): Whether to exclude Zelis from lookup

        Returns:
            str: Payer folder name or empty string if not found
        """
        if not self._mappings_loaded:
            self.load_mappings()

        # Filter payer mappings
        matches = self.payer_df[self.payer_df.iloc[:, 1].str.strip() == str(waystar_id).strip()]

        if exclude_zelis:
            matches = matches[matches.iloc[:, 2].str.strip() != "Zelis"]

        if len(matches) > 0:
            return matches.iloc[0, 2].strip()

        return ""


def determine_payer_folder(file_parts: list, practice_mapping: Dict[str, str],
                          payer_df: pd.DataFrame, chk_nbr: str) -> Tuple[str, str, str]:
    """
    Determine payer folder, EFT number, and practice ID from file parts and check number.

    Args:
        file_parts (list): Parts of the filename split by underscore
        practice_mapping (Dict[str, str]): WS_ID to APP_ID mapping
        payer_df (pd.DataFrame): Payer mapping DataFrame
        chk_nbr (str): Check number

    Returns:
        Tuple[str, str, str]: (payer_folder, eft_num, practice_id)
    """
    if len(file_parts) >= 2:
        ws_id = str(file_parts[0])
        waystar_id = str(file_parts[1])
    else:
        ws_id = ""
        waystar_id = ""

    # Get APP_ID from practice mapping
    app_id = practice_mapping.get(ws_id, "")

    # Determine TRN (transaction number)
    if app_id and chk_nbr.startswith(app_id):
        trn = chk_nbr[len(app_id):]
    else:
        trn = chk_nbr

    # Check for Zelis pattern (9 digits starting with 6 or 7)
    if (len(trn) == 9 and trn.isdigit() and (trn.startswith("6") or trn.startswith("7"))):
        payer_folder = "Zelis"
    else:
        # Look up waystar_id in mapping file where PAYER FOLDER != "Zelis"
        non_zelis_matches = payer_df[
            (payer_df.iloc[:, 1].str.strip() == waystar_id) &
            (payer_df.iloc[:, 2].str.strip() != "Zelis")
        ]
        if len(non_zelis_matches) > 0:
            payer_folder = non_zelis_matches.iloc[0, 2].strip()
        else:
            payer_folder = ""

    return payer_folder, trn, ws_id


def format_runtime(seconds: float) -> str:
    """
    Format runtime in a human-readable way.

    Args:
        seconds (float): Runtime in seconds

    Returns:
        str: Formatted runtime string
    """
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    else:
        minutes = seconds / 60
        return f"{minutes:.1f} minutes ({seconds:.1f} seconds)"


def validate_dataframe_columns(df: pd.DataFrame, required_columns: list, operation: str = "") -> None:
    """
    Validate that a DataFrame has all required columns.

    Args:
        df (pd.DataFrame): DataFrame to validate
        required_columns (list): List of required column names
        operation (str): Description of the operation for error messages

    Raises:
        ValidationError: If required columns are missing
    """
    from .exceptions import ValidationError

    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        raise ValidationError(
            f"Missing required columns for {operation}: {missing_columns}",
            validation_type="column_validation",
            expected=required_columns,
            actual=list(df.columns)
        )


def safe_numeric_conversion(value, default=0):
    """
    Safely convert a value to numeric, returning default if conversion fails.

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Numeric value or default
    """
    try:
        return pd.to_numeric(value, errors='raise')
    except (ValueError, TypeError):
        return default


def get_unique_encounters_by_status(df: pd.DataFrame) -> Tuple[set, set]:
    """
    Get unique encounter numbers categorized by claim status (22 vs others).

    Args:
        df (pd.DataFrame): DataFrame with encounter and claim status data

    Returns:
        Tuple[set, set]: (encounters with status 22, encounters with other statuses)
    """
    unique_22_enc_nbrs = set()
    unique_123_enc_nbrs = set()

    for _, row in df.iterrows():
        enc_val = str(row["Enc Nbr"]).strip()
        clm_val = str(row["Clm Sts Cod"]).strip()

        if enc_val and enc_val != "":
            if clm_val.startswith("22"):
                unique_22_enc_nbrs.add(enc_val)
            else:
                unique_123_enc_nbrs.add(enc_val)

    return unique_22_enc_nbrs, unique_123_enc_nbrs


def print_processing_summary(stats: dict, operation: str = "Processing") -> None:
    """
    Print a formatted summary of processing statistics.

    Args:
        stats (dict): Dictionary of processing statistics
        operation (str): Name of the operation being summarized
    """
    print(f"📊 {operation} Summary:")
    for key, value in stats.items():
        formatted_key = key.replace('_', ' ').title()
        if isinstance(value, (int, float)) and value >= 1000:
            print(f"   • {formatted_key}: {value:,}")
        else:
            print(f"   • {formatted_key}: {value}")


# Global mapping loader instance for shared use
_global_mapping_loader = None

def get_mapping_loader(mapping_file: str = "Proliance Mapping.xlsx") -> MappingLoader:
    """
    Get a shared mapping loader instance.

    Args:
        mapping_file (str): Path to mapping file

    Returns:
        MappingLoader: Shared mapping loader instance
    """
    global _global_mapping_loader

    if _global_mapping_loader is None or _global_mapping_loader.mapping_file != mapping_file:
        _global_mapping_loader = MappingLoader(mapping_file)

    return _global_mapping_loader