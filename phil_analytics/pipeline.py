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
from .excel_data_processor import ExcelDataObjectCreator, EncounterTagger, PaymentTagger, AnalyticsProcessor
from .markdown_generator import MarkdownGenerator
from .exceptions import PhilAnalyticsError
from .utils import format_runtime


class PhilPipeline:
    """
    Main pipeline orchestrator for PHIL Analytics processing.

    This class coordinates the full workflow from combining Excel files
    through data cleaning, validation, and analytics generation.
    """

    def __init__(self, payer_folder: str, input_folder: Optional[str] = None,
                 output_folder: Optional[str] = None, mapping_file: Optional[str] = None,
                 max_files: Optional[int] = None, save_combined: bool = True):
        """
        Initialize the PHIL Analytics pipeline.

        Args:
            payer_folder (str): Name of the payer folder to process
            input_folder (str, optional): Override default input folder path
            output_folder (str, optional): Override default output folder path
            mapping_file (str, optional): Override default mapping file path
            max_files (int, optional): Maximum number of files to process (for testing)
            save_combined (bool): Whether to save a _combined.xlsx file for testing
        """
        print(f"🚀 Initializing PHIL Analytics Pipeline for: {payer_folder}")
        if max_files:
            print(f"🧪 Test mode: Limited to {max_files} files")

        self.payer_folder = payer_folder
        self.max_files = max_files
        self.save_combined = save_combined

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
        self.data_object_creator = None
        self.encounter_tagger = None
        self.payment_tagger = None
        self.analytics_processor = None
        self.markdown_generator = None

        # Results storage
        self.combined_data = None
        self.scrubbed_data = None
        self.scrubbed_file_path = None
        self.data_object = None
        self.analytics_results = None

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
        print(f"\n🚀 Starting Combine and Scrub Pipeline for {self.payer_folder}")
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

            print(f"\n✅ Combine and Scrub Pipeline completed successfully!")
            print(f"🏁 Total pipeline runtime: {format_runtime(total_runtime)}")

            return self._get_pipeline_results(total_runtime)

        except Exception as e:
            print(f"\n❌ Pipeline failed: {e}")
            raise PhilAnalyticsError(f"Pipeline execution failed: {e}")

    def run_full_pipeline(self) -> Dict[str, Any]:
        """
        Run the complete pipeline including combine, scrub, and analytics generation.

        Returns:
            Dict[str, Any]: Results containing all data and statistics
        """
        print(f"\n🚀 Starting Full PHIL Analytics Pipeline for {self.payer_folder}")
        total_start_time = time.time()

        try:
            # Step 1: Combine files
            self._run_combine_step()

            # Step 2: Scrub data
            self._run_scrub_step()

            # Step 3: Save output
            self._save_scrubbed_output()

            # Step 4: Create data object
            self._run_data_object_creation_step()

            # Step 5: Tag encounters
            self._run_encounter_tagging_step()

            # Step 6: Tag payments
            self._run_payment_tagging_step()

            # Step 7: Run analytics
            self._run_analytics_step()

            # Step 8: Generate markdown
            self._run_markdown_generation_step()

            # Calculate total runtime
            total_end_time = time.time()
            total_runtime = total_end_time - total_start_time

            print(f"\n✅ Full Pipeline completed successfully!")
            print(f"🏁 Total pipeline runtime: {format_runtime(total_runtime)}")

            return self._get_full_pipeline_results(total_runtime)

        except Exception as e:
            print(f"\n❌ Pipeline failed: {e}")
            raise PhilAnalyticsError(f"Pipeline execution failed: {e}")

    def _run_combine_step(self) -> None:
        """Run the file combination step."""
        print(f"\n📁 Step 1: Combining Excel files")
        step_start_time = time.time()

        self.combiner = ExcelCombiner(self.input_folder, max_files=self.max_files, save_combined=self.save_combined, output_folder=self.output_folder)
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
        self.scrubbed_file_path = os.path.join(self.output_folder, scrubbed_filename)

        self.cleaner.save_to_file(self.scrubbed_data, self.scrubbed_file_path)

        step_end_time = time.time()
        step_runtime = step_end_time - step_start_time
        print(f"⏱️ File saving runtime: {format_runtime(step_runtime)}")

    def _run_data_object_creation_step(self) -> None:
        """Run the data object creation step."""
        print(f"\n🏗️ Step 4: Creating data object")
        step_start_time = time.time()

        # Create data object from scrubbed Excel file
        process_limit = self.max_files * 1000 if self.max_files else None  # Estimate rows based on files
        self.data_object_creator = ExcelDataObjectCreator(self.scrubbed_file_path, process_limit)
        self.data_object = self.data_object_creator.create_data_object()

        # Get summary stats
        stats = self.data_object_creator.get_summary_stats()
        print(f"   📋 Created data object with {stats['total_eft_nums']} EFTs from {stats['total_rows']:,} rows")

        # Report missing encounter EFTs if any
        missing_encounter_efts = self.data_object_creator.get_missing_encounter_efts()
        if missing_encounter_efts:
            print(f"   ⚠️ Found {len(missing_encounter_efts)} EFTs with missing encounters (excluded from processing)")

        step_end_time = time.time()
        step_runtime = step_end_time - step_start_time
        print(f"⏱️ Data object creation runtime: {format_runtime(step_runtime)}")

    def _run_encounter_tagging_step(self) -> None:
        """Run the encounter tagging step."""
        print(f"\n🏷️ Step 5: Tagging encounters")
        step_start_time = time.time()

        self.encounter_tagger = EncounterTagger()
        self.data_object = self.encounter_tagger.tag_encounters(self.data_object)

        step_end_time = time.time()
        step_runtime = step_end_time - step_start_time
        print(f"⏱️ Encounter tagging runtime: {format_runtime(step_runtime)}")

    def _run_payment_tagging_step(self) -> None:
        """Run the payment tagging step."""
        print(f"\n🏷️ Step 6: Tagging payments and EFTs")
        step_start_time = time.time()

        self.payment_tagger = PaymentTagger()
        self.data_object = self.payment_tagger.tag_payments(self.data_object)

        step_end_time = time.time()
        step_runtime = step_end_time - step_start_time
        print(f"⏱️ Payment tagging runtime: {format_runtime(step_runtime)}")

    def _run_analytics_step(self) -> None:
        """Run the analytics processing step."""
        print(f"\n📊 Step 7: Running analytics")
        step_start_time = time.time()

        self.analytics_processor = AnalyticsProcessor()
        self.analytics_results = self.analytics_processor.analyze_mixed_post_payments(self.data_object)

        # Print analytics summary
        self.analytics_processor.print_analytics_summary()

        step_end_time = time.time()
        step_runtime = step_end_time - step_start_time
        print(f"⏱️ Analytics runtime: {format_runtime(step_runtime)}")

    def _run_markdown_generation_step(self) -> None:
        """Run the markdown generation step."""
        print(f"\n📝 Step 8: Generating markdown files")
        step_start_time = time.time()

        # Get missing encounter EFTs from the data object creator
        missing_encounter_efts = self.data_object_creator.get_missing_encounter_efts() if self.data_object_creator else []

        self.markdown_generator = MarkdownGenerator(self.payer_folder)

        # Generate EFTs markdown
        self.markdown_file_path = self.markdown_generator.generate_efts_markdown(
            self.data_object,
            self.output_folder,
            missing_encounter_efts,
            self.analytics_results  # Pass analytics results
        )

        # Generate QA It Shoulds markdown
        self.it_shoulds_file_path = self.markdown_generator.generate_it_shoulds_markdown(
            self.output_folder
        )

        # Get markdown stats with missing encounter EFTs info
        markdown_stats = self.markdown_generator.generate_summary_stats(self.data_object, missing_encounter_efts)
        print(f"   📊 Generated EFTs markdown for {markdown_stats['total_efts']} EFTs")
        print(f"   🔍 Found {markdown_stats['total_encounters_to_check']} encounters to check")
        print(f"   📋 Generated QA It Shoulds markdown with payment type specifications")
        if missing_encounter_efts:
            print(f"   ⚠️ Found {len(missing_encounter_efts)} EFTs with missing encounters")

        step_end_time = time.time()
        step_runtime = step_end_time - step_start_time
        print(f"⏱️ Markdown generation runtime: {format_runtime(step_runtime)}")

    def _get_pipeline_results(self, total_runtime: float) -> Dict[str, Any]:
        """
        Get pipeline results for combine and scrub only.

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
            'scrubbed_file': self.scrubbed_file_path
        }

        return results

    def _get_full_pipeline_results(self, total_runtime: float) -> Dict[str, Any]:
        """
        Get comprehensive pipeline results including all processing steps.

        Args:
            total_runtime (float): Total pipeline runtime in seconds

        Returns:
            Dict[str, Any]: Full pipeline results and statistics
        """
        # Get markdown stats with missing encounter EFTs
        missing_encounter_efts = self.data_object_creator.get_missing_encounter_efts() if self.data_object_creator else []
        markdown_stats = self.markdown_generator.generate_summary_stats(self.data_object, missing_encounter_efts) if self.markdown_generator else {}

        results = {
            'payer_folder': self.payer_folder,
            'total_runtime': total_runtime,
            'scrubbed_data': self.scrubbed_data,
            'data_object': self.data_object,
            'analytics_results': self.analytics_results,
            'file_summary': self.combiner.get_file_summary() if self.combiner else {},
            'cleaning_stats': self.cleaner.get_cleaning_stats() if self.cleaner else {},
            'data_object_stats': self.data_object_creator.get_summary_stats() if self.data_object_creator else {},
            'markdown_stats': markdown_stats,
            'missing_encounter_efts': missing_encounter_efts,
            'output_folder': self.output_folder,
            'scrubbed_file': self.scrubbed_file_path,
            'markdown_file': getattr(self, 'markdown_file_path', ''),
            'it_shoulds_file': getattr(self, 'it_shoulds_file_path', ''),
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
    print(f"🧪 Testing PHIL Analytics Full Pipeline with {payer_folder}")
    print(f"🔧 Test mode: Processing only {max_files} files for faster testing")

    pipeline = PhilPipeline(payer_folder, max_files=max_files)
    results = pipeline.run_full_pipeline()

    print(f"\n📊 Test Results Summary:")
    print(f"   • Files processed: {results['file_summary'].get('total_files', 'Unknown')}")
    print(f"   • Total rows: {results['file_summary'].get('total_rows', 'Unknown'):,}")
    print(f"   • Bad rows removed: {results['cleaning_stats'].get('bad_rows_removed', 0):,}")
    print(f"   • EFTs found: {results['data_object_stats'].get('total_eft_nums', 0)}")
    print(f"   • Missing encounter EFTs: {len(results.get('missing_encounter_efts', []))}")
    print(f"   • Split EFTs: {results['markdown_stats'].get('split_efts', 0)}")
    print(f"   • Encounters to check: {results['markdown_stats'].get('total_encounters_to_check', 0)}")

    # Print analytics summary
    if results.get('analytics_results'):
        analytics_summary = results['analytics_results'].get('summary', {})
        print(f"   • Mixed Post (No PLAs): {analytics_summary.get('mixed_post_no_plas_count', 0)}")
        print(f"   • Mixed Post (L6 Only): {analytics_summary.get('mixed_post_l6_only_count', 0)}")
        print(f"   • Charge Mismatch CPT4: {analytics_summary.get('charge_mismatch_cpt4_count', 0)}")

    print(f"   • Runtime: {format_runtime(results['total_runtime'])}")
    print(f"   • EFTs markdown: {results['markdown_file']}")
    print(f"   • QA It Shoulds markdown: {results['it_shoulds_file']}")

    return results