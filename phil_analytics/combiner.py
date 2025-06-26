"""
PHIL Analytics and QA Library - Excel File Combiner

This module replicates the exact logic from combine_xlsx_files.py but returns
a DataFrame instead of saving to a file.
"""

import os
import pandas as pd
from openpyxl import load_workbook
from typing import Optional
from .exceptions import FileNotFoundError, ValidationError, DataProcessingError


class ExcelCombiner:
    """
    Combines multiple Excel files from a specified folder using the exact same
    logic as the original combine_xlsx_files.py.

    This preserves all formatting and handles headers the same way as the original,
    but returns a DataFrame instead of saving to Excel.
    """

    def __init__(self, input_folder: str, max_files: int = None):
        """
        Initialize the ExcelCombiner.

        Args:
            input_folder (str): Path to the folder containing Excel files to combine
            max_files (int, optional): Maximum number of files to process (for testing)

        Raises:
            FileNotFoundError: If the input folder doesn't exist
        """
        print(f"🔧 Initializing Excel combiner for folder: {input_folder}")
        if max_files:
            print(f"   🧪 Test mode: Limited to {max_files} files")

        if not os.path.exists(input_folder):
            raise FileNotFoundError(
                input_folder,
                file_type="input folder",
                expected_location="Current working directory or specified path"
            )

        self.input_folder = input_folder
        self.max_files = max_files
        self.combined_data = None
        self.file_count = 0
        self.total_rows = 0

        print(f"✅ Excel combiner initialized successfully")

    def get_excel_files(self) -> list:
        """
        Get list of Excel files - exact logic from original combine_xlsx_files.py

        Returns:
            list: List of Excel file names (.xlsx files, excluding temporary files)
        """
        print(f"📁 Scanning folder for Excel files...")

        excel_files = []
        for file_name in os.listdir(self.input_folder):
            if file_name.endswith(".xlsx") and not file_name.startswith("~$"):
                excel_files.append(file_name)

        if not excel_files:
            raise ValidationError(
                f"No Excel files found in folder: {self.input_folder}",
                validation_type="file_discovery",
                expected="*.xlsx files",
                actual="no xlsx files found"
            )

        # Apply file limit for testing
        if self.max_files and len(excel_files) > self.max_files:
            excel_files = excel_files[:self.max_files]
            print(f"🧪 Test mode: Limited to first {self.max_files} files")

        print(f"📋 Found {len(excel_files)} Excel files to process")
        for i, file_name in enumerate(excel_files, 1):
            print(f"   {i}. {file_name}")

        return excel_files

    def combine_files(self) -> pd.DataFrame:
        """
        Combine Excel files using the exact same logic as combine_xlsx_files.py
        but return a DataFrame instead of saving to Excel.

        Returns:
            pd.DataFrame: Combined data with all original formatting preserved as text
        """
        print(f"🚀 Starting file combination process (replicating combine_xlsx_files.py)...")

        # Get list of Excel files
        excel_files = self.get_excel_files()

        # Initialize variables exactly like the original
        all_data = []
        first_file = True
        expected_headers = []

        print(f"🔄 Processing {len(excel_files)} files...")

        for file_name in excel_files:
            if file_name.endswith(".xlsx") and not file_name.startswith("~$"):
                file_path = os.path.join(self.input_folder, file_name)
                print(f"📄 Processing: {file_name}")

                try:
                    # Use openpyxl exactly like the original - with data_only=False
                    wb = load_workbook(file_path, data_only=False)

                    for sheet in wb.worksheets:
                        sheet_data = []

                        for i, row in enumerate(sheet.iter_rows(), start=1):
                            row_data = []

                            # Extract cell values exactly like original
                            for cell in row:
                                row_data.append(cell.value)

                            # Handle headers exactly like original
                            if first_file and i == 1:
                                expected_headers = row_data.copy()
                                sheet_data.append(row_data)
                                continue

                            # Skip header rows from subsequent files
                            if not first_file and i == 1:
                                headers = row_data.copy()
                                if headers != expected_headers:
                                    print(f"⚠️ Header mismatch in file: {file_name}")
                                continue

                            # Add the data row
                            sheet_data.append(row_data)

                        # Add this sheet's data to all_data
                        all_data.extend(sheet_data)

                    first_file = False
                    self.file_count += 1
                    print(f"   ✅ Successfully processed {file_name}")

                except Exception as e:
                    print(f"   ❌ Failed to process {file_name}: {e}")
                    continue

        if not all_data:
            raise DataProcessingError(
                "No files were successfully processed",
                operation="file_combination",
                files_attempted=len(excel_files)
            )

        # Convert to DataFrame exactly preserving the original logic
        print(f"🔗 Converting combined data to DataFrame...")

        try:
            # Create DataFrame with first row as headers, rest as data
            if len(all_data) > 0:
                headers = all_data[0]
                data_rows = all_data[1:] if len(all_data) > 1 else []

                # Create DataFrame ensuring all data is treated as strings (like Excel TEXT)
                self.combined_data = pd.DataFrame(data_rows, columns=headers)

                # Convert all columns to string to preserve Excel TEXT formatting
                for col in self.combined_data.columns:
                    self.combined_data[col] = self.combined_data[col].astype(str)

                # Replace 'None' strings with empty strings
                self.combined_data = self.combined_data.replace('None', '')
                self.combined_data = self.combined_data.fillna('')

                self.total_rows = len(self.combined_data)

                print(f"✅ File combination completed successfully!")
                print(f"   📊 Total files processed: {self.file_count}")
                print(f"   📈 Total rows combined: {self.total_rows:,}")
                print(f"   📋 Total columns: {len(self.combined_data.columns)}")

                # Show sample of the File column to verify it has the right data
                if 'File' in self.combined_data.columns:
                    sample_files = self.combined_data['File'].unique()[:3]
                    print(f"   🔍 Sample File column values: {sample_files.tolist()}")

                return self.combined_data
            else:
                raise DataProcessingError("No data found in combined files")

        except Exception as e:
            raise DataProcessingError(
                f"Failed to create DataFrame from combined data: {e}",
                operation="dataframe_creation"
            )

    def get_file_summary(self) -> dict:
        """
        Get summary statistics about the combined data.

        Returns:
            dict: Summary information including file count, row count, columns, etc.
        """
        if self.combined_data is None:
            return {"status": "No data combined yet"}

        # Get file distribution if File column exists
        file_counts = {}
        if 'File' in self.combined_data.columns:
            file_counts = self.combined_data['File'].value_counts().to_dict()

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
        Save the combined data to an Excel file (optional - for debugging).

        Args:
            output_file (str): Path for the output Excel file
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