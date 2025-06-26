"""
PHIL Analytics and QA Library - Excel File Combiner

This module provides the ExcelCombiner class for combining multiple Excel files
from a specified folder into a single pandas DataFrame while preserving
text formatting and ensuring consistent headers.
"""

import os
import pandas as pd
from typing import Optional
from .exceptions import FileNotFoundError, ValidationError, DataProcessingError


class ExcelCombiner:
    """
    Combines multiple Excel files from a specified folder into a single pandas DataFrame.

    This class handles Excel file combination while preserving formatting and ensuring
    consistent headers across all files. Text formatting is preserved by treating all
    columns as strings during the initial load.

    Attributes:
        input_folder (str): Path to the folder containing Excel files
        combined_data (pd.DataFrame): Combined data from all Excel files
        file_count (int): Number of files successfully processed
        total_rows (int): Total number of rows in combined data
    """

    def __init__(self, input_folder: str):
        """
        Initialize the ExcelCombiner.

        Args:
            input_folder (str): Path to the folder containing Excel files to combine

        Raises:
            FileNotFoundError: If the input folder doesn't exist
        """
        print(f"🔧 Initializing Excel combiner for folder: {input_folder}")

        if not os.path.exists(input_folder):
            raise FileNotFoundError(
                input_folder,
                file_type="input folder",
                expected_location="Current working directory or specified path"
            )

        self.input_folder = input_folder
        self.combined_data = None
        self.file_count = 0
        self.total_rows = 0

        print(f"✅ Excel combiner initialized successfully")

    def get_excel_files(self) -> list:
        """
        Get list of Excel files in the input folder.

        Returns:
            list: List of Excel file names (.xlsx files, excluding temporary files)

        Raises:
            ValidationError: If no Excel files are found
        """
        print(f"📁 Scanning folder for Excel files...")

        try:
            all_files = os.listdir(self.input_folder)
            excel_files = [f for f in all_files
                          if f.endswith(".xlsx") and not f.startswith("~$")]

            if not excel_files:
                raise ValidationError(
                    f"No Excel files found in folder: {self.input_folder}",
                    validation_type="file_discovery",
                    expected="*.xlsx files",
                    actual="no xlsx files found"
                )

            print(f"📋 Found {len(excel_files)} Excel files to process")
            for i, file_name in enumerate(excel_files, 1):
                print(f"   {i}. {file_name}")

            return excel_files

        except OSError as e:
            raise DataProcessingError(
                f"Error reading folder contents: {e}",
                operation="folder_scan",
                folder_path=self.input_folder
            )

    def validate_headers(self, new_headers: list, expected_headers: Optional[list] = None) -> bool:
        """
        Validate that headers match across files.

        Args:
            new_headers (list): Headers from current file
            expected_headers (list, optional): Expected headers from first file

        Returns:
            bool: True if headers match or no expected headers provided
        """
        if expected_headers is None:
            return True

        if list(new_headers) != list(expected_headers):
            print(f"⚠️ Header mismatch detected")
            print(f"   Expected: {expected_headers}")
            print(f"   Found: {new_headers}")
            return False

        return True

    def read_excel_file(self, file_path: str, file_name: str) -> pd.DataFrame:
        """
        Read a single Excel file with proper text formatting preservation.

        This method ensures that Excel TEXT fields are preserved as strings,
        preventing pandas from converting text that looks like numbers.

        Args:
            file_path (str): Full path to the Excel file
            file_name (str): Name of the file (for source tracking)

        Returns:
            pd.DataFrame: DataFrame with all columns as strings and File column added

        Raises:
            DataProcessingError: If file cannot be read
        """
        print(f"📖 Reading file: {file_name}")

        try:
            # Read with ALL columns as strings to preserve Excel TEXT formatting
            # This prevents pandas from auto-converting text that looks like numbers
            df = pd.read_excel(
                file_path,
                dtype=str,                    # Treat ALL columns as strings
                keep_default_na=False,        # Don't convert to NaN
                na_filter=False              # Don't filter NA values
            ).fillna("")

            # Add File column to track source
            df['File'] = file_name

            print(f"   ✅ Successfully read {len(df)} rows from {file_name}")
            print(f"   📝 All columns preserved as text to maintain Excel formatting")
            return df

        except Exception as e:
            raise DataProcessingError(
                f"Failed to read Excel file: {e}",
                operation="excel_read",
                file_name=file_name,
                file_path=file_path
            )

    def combine_files(self) -> pd.DataFrame:
        """
        Combine all Excel files in the input folder into a single DataFrame.

        Returns:
            pd.DataFrame: Combined data from all Excel files with all columns as strings

        Raises:
            FileNotFoundError: If no Excel files found
            ValidationError: If header mismatches occur
            DataProcessingError: If file processing fails
        """
        print(f"🚀 Starting file combination process...")

        # Get list of Excel files
        excel_files = self.get_excel_files()

        combined_data = []
        expected_headers = None
        files_with_header_issues = []

        print(f"🔄 Processing {len(excel_files)} files...")

        for i, file_name in enumerate(excel_files, 1):
            file_path = os.path.join(self.input_folder, file_name)

            print(f"📄 Processing file {i}/{len(excel_files)}: {file_name}")

            try:
                # Read the Excel file
                df = self.read_excel_file(file_path, file_name)

                # Validate headers
                current_headers = [col for col in df.columns if col != 'File']  # Exclude our added File column

                if expected_headers is None:
                    expected_headers = current_headers
                    print(f"   📋 Using headers from first file as template")
                elif not self.validate_headers(current_headers, expected_headers):
                    files_with_header_issues.append(file_name)
                    print(f"   ⚠️ Header mismatch in {file_name} - including anyway")

                combined_data.append(df)
                self.file_count += 1

            except Exception as e:
                print(f"   ❌ Failed to process {file_name}: {e}")
                # Continue processing other files rather than failing completely
                continue

        if not combined_data:
            raise DataProcessingError(
                "No files were successfully processed",
                operation="file_combination",
                files_attempted=len(excel_files)
            )

        # Combine all DataFrames
        print(f"🔗 Combining data from {len(combined_data)} successfully processed files...")

        try:
            self.combined_data = pd.concat(combined_data, ignore_index=True, sort=False)
            self.total_rows = len(self.combined_data)

            print(f"✅ File combination completed successfully!")
            print(f"   📊 Total files processed: {self.file_count}")
            print(f"   📈 Total rows combined: {self.total_rows:,}")
            print(f"   📋 Total columns: {len(self.combined_data.columns)}")

            if files_with_header_issues:
                print(f"   ⚠️ Files with header mismatches: {len(files_with_header_issues)}")
                for file_name in files_with_header_issues:
                    print(f"      - {file_name}")

            return self.combined_data

        except Exception as e:
            raise DataProcessingError(
                f"Failed to combine DataFrames: {e}",
                operation="dataframe_concatenation",
                files_count=len(combined_data)
            )

    def get_file_summary(self) -> dict:
        """
        Get summary statistics about the combined data.

        Returns:
            dict: Summary information including file count, row count, columns, etc.
        """
        if self.combined_data is None:
            return {"status": "No data combined yet"}

        # Get file distribution
        file_counts = self.combined_data['File'].value_counts().to_dict() if 'File' in self.combined_data.columns else {}

        summary = {
            "total_files": self.file_count,
            "total_rows": self.total_rows,
            "total_columns": len(self.combined_data.columns),
            "file_distribution": file_counts,
            "columns": list(self.combined_data.columns),
            "memory_usage_mb": round(self.combined_data.memory_usage(deep=True).sum() / 1024 / 1024, 2)
        }

        return summary

    def save_to_file(self, output_file: str) -> None:
        """
        Save the combined data to an Excel file.

        Args:
            output_file (str): Path for the output Excel file

        Raises:
            DataProcessingError: If no data to save or save operation fails
        """
        if self.combined_data is None:
            raise DataProcessingError(
                "No data to save. Run combine_files() first.",
                operation="file_save"
            )

        print(f"💾 Saving combined data to: {output_file}")

        try:
            self.combined_data.to_excel(output_file, index=False)
            print(f"✅ Combined data saved successfully!")
            print(f"   📁 File location: {output_file}")
            print(f"   📊 Rows saved: {len(self.combined_data):,}")

        except Exception as e:
            raise DataProcessingError(
                f"Failed to save Excel file: {e}",
                operation="excel_save",
                output_file=output_file
            )

    def preview_data(self, rows: int = 5) -> pd.DataFrame:
        """
        Preview the first few rows of combined data.

        Args:
            rows (int): Number of rows to preview (default: 5)

        Returns:
            pd.DataFrame: Preview of the data
        """
        if self.combined_data is None:
            print("❌ No data available for preview. Run combine_files() first.")
            return pd.DataFrame()

        print(f"👀 Preview of first {rows} rows:")
        preview = self.combined_data.head(rows)
        print(preview.to_string())
        return preview