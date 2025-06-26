"""
PHIL Analytics and QA Library - Pipeline Orchestrator

This module provides the main pipeline class for coordinating the full
data processing workflow.
"""

import os
import time
from typing import Optional, Dict, Any
from .combiner import ExcelCombiner
from .scrubber import DataCleaner
from .exceptions import PhilAnalyticsError
from .utils import format_runtime


class PhilPipeline:
    """
    Main pipeline orchestrator for PHIL Analytics processing.

    This class coordinates the full workflow from combining Excel files
    through data cleaning and validation.
    """

    def __init__(self, payer_folder: str, input_folder: Optional[str] = None,
                 output_folder: Optional[str] = None, mapping_file: Optional[str] = None,
                 max_files: Optional[int] = None):
        """
        Initialize the PHIL Analytics pipeline.

        Args:
            payer_folder (str): Name of the payer folder to process
            input_folder (str, optional): Override default input folder path
            output_folder (str, optional): Override default output folder path
            mapping_file (str, optional): Override default mapping file path
            max_files (int, optional): Maximum number of files to process (for testing)
        """
        print(f"🚀 Initializing PHIL Analytics Pipeline for: {payer_folder}")
        if max_files:
            print(f"🧪 Test mode: Limited to {max_files} files")

        self.payer_folder = payer_folder
        self.max_files = max_files

        # Set up paths
        if input_folder is None:
            self.input_folder = os.path.join("data", "input", payer_folder)
        else:
            self.input_folder = input_folder

        if output_folder is None:
            self.output_folder = os.path.join("data", "output", f"{payer_folder}_output")
        else:
            self.output_folder = output_folder

        if mapping_file is None:
            self.mapping_file = os.path.join("data", "mappings", "Proliance Mapping.xlsx")
        else:
            self.mapping_file = mapping_file

        # Initialize components
        self.combiner = None
        self.cleaner = None

        # Results storage
        self.combined_data = None
        self.scrubbed_data = None

        print(f"✅ Pipeline initialized successfully")
        print(f"   📁 Input folder: {self.input_folder}")
        print(f"   📁 Output folder: {self.output_folder}")
        print(f"   🗺️ Mapping file: {self.mapping_file}")

    def run_combine_and_scrub(self) -> Dict[str, Any]:
        """
        Run the combine and scrub phases of the pipeline.

        Returns:
            Dict[str, Any]: Results containing scrubbed data and statistics
        """
        print(f"\n🚀 Starting PHIL Analytics Pipeline for {self.payer_folder}")
        total_start_time = time.time()

        try:
            # Step 1: Combine files
            self._run_combine_step()

            # Step 2: Scrub data
            self._run_scrub_step()

            # Step 3: Save output
            self._save_scrubbed_output()

            # Calculate total runtime
            total_end_time = time.time()
            total_runtime = total_end_time - total_start_time

            print(f"\n✅ Pipeline completed successfully!")
            print(f"🏁 Total pipeline runtime: {format_runtime(total_runtime)}")

            return self._get_pipeline_results(total_runtime)

        except Exception as e:
            print(f"\n❌ Pipeline failed: {e}")
            raise PhilAnalyticsError(f"Pipeline execution failed: {e}")

    def _run_combine_step(self) -> None:
        """Run the file combination step."""
        print(f"\n📁 Step 1: Combining Excel files")
        step_start_time = time.time()

        self.combiner = ExcelCombiner(self.input_folder, max_files=self.max_files)
        self.combined_data = self.combiner.combine_files()

        step_end_time = time.time()
        step_runtime = step_end_time - step_start_time
        print(f"⏱️ Combining runtime: {format_runtime(step_runtime)}")

    def _run_scrub_step(self) -> None:
        """Run the data scrubbing step."""
        print(f"\n🧹 Step 2: Scrubbing and cleaning data")
        step_start_time = time.time()

        self.cleaner = DataCleaner(self.mapping_file)
        self.scrubbed_data = self.cleaner.clean_data(self.combined_data)

        step_end_time = time.time()
        step_runtime = step_end_time - step_start_time
        print(f"⏱️ Scrubbing runtime: {format_runtime(step_runtime)}")

    def _save_scrubbed_output(self) -> None:
        """Save the scrubbed data to output folder."""
        print(f"\n💾 Step 3: Saving output files")
        step_start_time = time.time()

        # Create output folder if it doesn't exist
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)
            print(f"📁 Created output folder: {self.output_folder}")

        # Save scrubbed file
        scrubbed_filename = f"{self.payer_folder}_Scrubbed.xlsx"
        scrubbed_path = os.path.join(self.output_folder, scrubbed_filename)

        self.cleaner.save_to_file(self.scrubbed_data, scrubbed_path)

        step_end_time = time.time()
        step_runtime = step_end_time - step_start_time
        print(f"⏱️ File saving runtime: {format_runtime(step_runtime)}")

    def _get_pipeline_results(self, total_runtime: float) -> Dict[str, Any]:
        """
        Get comprehensive pipeline results.

        Args:
            total_runtime (float): Total pipeline runtime in seconds

        Returns:
            Dict[str, Any]: Pipeline results and statistics
        """
        results = {
            'payer_folder': self.payer_folder,
            'total_runtime': total_runtime,
            'scrubbed_data': self.scrubbed_data,
            'file_summary': self.combiner.get_file_summary() if self.combiner else {},
            'cleaning_stats': self.cleaner.get_cleaning_stats() if self.cleaner else {},
            'output_folder': self.output_folder,
            'scrubbed_file': os.path.join(self.output_folder, f"{self.payer_folder}_Scrubbed.xlsx")
        }

        return results


# Quick test function for development
def test_pipeline(payer_folder: str = "Regence", max_files: int = 3) -> Dict[str, Any]:
    """
    Quick test function for pipeline development.

    Args:
        payer_folder (str): Payer folder to test with
        max_files (int): Maximum number of files to process for testing

    Returns:
        Dict[str, Any]: Pipeline results
    """
    print(f"🧪 Testing PHIL Analytics Pipeline with {payer_folder}")
    print(f"🔧 Test mode: Processing only {max_files} files for faster testing")

    pipeline = PhilPipeline(payer_folder, max_files=max_files)
    results = pipeline.run_combine_and_scrub()

    print(f"\n📊 Test Results Summary:")
    print(f"   • Files processed: {results['file_summary'].get('total_files', 'Unknown')}")
    print(f"   • Total rows: {results['file_summary'].get('total_rows', 'Unknown'):,}")
    print(f"   • Bad rows removed: {results['cleaning_stats'].get('bad_rows_removed', 0):,}")
    print(f"   • Runtime: {format_runtime(results['total_runtime'])}")

    return results