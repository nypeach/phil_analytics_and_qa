"""
PHIL Analytics and QA Library - Main Runner

This is the main entry point for running the PHIL Analytics pipeline.
Place this file in your project root directory and run it from your IDE.
"""

from phil_analytics import quick_pipeline

def main(payer_folder, max_files=None, save_combined=True):
    """
    Main function to run the PHIL Analytics pipeline.

    Args:
        payer_folder (str): Name of the payer folder to process
        max_files (int, optional): Maximum number of files to process (None for all files)
        save_combined (bool): Whether to save a _combined.xlsx file for testing
    """
    print("🚀 Starting PHIL Analytics Pipeline...")
    print(f"   📁 Payer: {payer_folder}")
    if max_files:
        print(f"   🧪 Test mode: Limited to {max_files} files")
    else:
        print(f"   🔥 Production mode: Processing all files")
    print(f"   💾 Combined file will be saved for testing")

    try:
        # Run the full pipeline
        results = quick_pipeline(
            payer_folder=payer_folder,
            max_files=max_files,
            save_combined=save_combined
        )

        # Print results summary
        print(f"\n🎉 Pipeline completed successfully!")
        print(f"📊 Results Summary:")
        print(f"   • Payer: {results['payer_folder']}")
        print(f"   • Files processed: {results['file_summary'].get('total_files', 'Unknown')}")
        print(f"   • Total rows: {results['file_summary'].get('total_rows', 'Unknown'):,}")
        print(f"   • Bad rows removed: {results['cleaning_stats'].get('bad_rows_removed', 0):,}")
        print(f"   • EFTs found: {results['data_object_stats'].get('total_eft_nums', 0)}")
        print(f"   • Split EFTs: {results['markdown_stats'].get('split_efts', 0)}")
        print(f"   • Not Split EFTs: {results['markdown_stats'].get('not_split_efts', 0)}")
        print(f"   • Total encounters: {results['markdown_stats'].get('total_encounters', 0)}")
        print(f"   • Encounters to check: {results['markdown_stats'].get('total_encounters_to_check', 0)}")
        print(f"   • Runtime: {results['total_runtime']:.1f} seconds")
        print(f"   • Output folder: {results['output_folder']}")
        print(f"   • Scrubbed file: {results['scrubbed_file']}")
        print(f"   • EFTs markdown: {results['markdown_file']}")

    except Exception as e:
        print(f"❌ Error running pipeline: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    payer_folder = "Amerigroup"
    max_files = None
    main(payer_folder, max_files)