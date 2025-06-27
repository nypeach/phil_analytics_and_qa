"""
PHIL Analytics and QA Library

A Python library for processing Excel payment data from payer folders,
scrubbing and validating payment data, and generating analytics reports.

This library provides a complete pipeline for payment data processing including:
- Combining multiple Excel files from payer folders
- Scrubbing and validating payment data with business rules
- Processing Excel data for detailed analytics
- Generating comprehensive analytics reports in GitHub-flavored markdown

Example usage:
    >>> from phil_analytics import PhilPipeline
    >>> pipeline = PhilPipeline("Regence")
    >>> result = pipeline.run_full_pipeline()

    Or use individual components:
    >>> from phil_analytics.combiner import ExcelCombiner
    >>> from phil_analytics.scrubber import DataCleaner
    >>> from phil_analytics.excel_data_processor import ExcelDataProcessor
    >>> from phil_analytics.analytics import AnalyticsGenerator
"""

# Version information
__version__ = "1.0.0"
__author__ = "PHIL Analytics Team"
__description__ = "Payment data analytics and quality assurance pipeline"

# Import main classes for easy access
try:
    from .combiner import ExcelCombiner
    from .scrubber import DataCleaner
    from .excel_data_processor import ExcelDataProcessor
    from .pipeline import PhilPipeline
    from .exceptions import (
        PhilAnalyticsError,
        DataProcessingError,
        FileNotFoundError,
        ValidationError
    )
except ImportError as e:
    # Handle cases where dependencies might not be installed
    import warnings
    warnings.warn(f"Some components could not be imported: {e}")
    # Set to None so we can check later
    PhilPipeline = None

# Define what gets imported with "from phil_analytics import *"
__all__ = [
    # Main pipeline class
    'PhilPipeline',
    'quick_pipeline',

    # Individual component classes
    'ExcelCombiner',
    'DataCleaner',
    'ExcelDataProcessor',

    # Exception classes
    'PhilAnalyticsError',
    'DataProcessingError',
    'FileNotFoundError',
    'ValidationError',

    # Version info
    '__version__',
    '__author__',
    '__description__'
]

# Configuration defaults (can be overridden by user config.py)
DEFAULT_CONFIG = {
    'VERBOSE_OUTPUT': True,
    'DEFAULT_USE_GITHUB_FORMAT': True,
    'DEFAULT_MAPPING_FILE': 'Proliance Mapping.xlsx',
    'SAVE_INTERMEDIATE_FILES': False
}

def get_version():
    """Return the version string."""
    return __version__

def get_supported_payers():
    """
    Return list of supported payer folders.

    Returns:
        list: List of supported payer folder names
    """
    return [
        "Aetna", "Amerigroup", "Bundled EFT Coral", "Care Credit", "Centene",
        "ChampVA", "CHPWA", "Cigna", "Corvel Treasury", "DSHS", "Exceptions",
        "HMSO", "HNB Echo", "Humana", "Jopari", "Kaiser", "Medicare", "Optum",
        "Premera", "Providence", "Regence", "Small Payers", "Tricare", "UHC",
        "USDOL", "VSP", "WA ST & Other", "WA ST L&I", "Zelis"
    ]

def quick_pipeline(payer_folder, max_files=None, input_folder=None, output_folder=None, mapping_file=None, save_combined=True):
    """
    Quick pipeline runner for common use cases.

    Args:
        payer_folder (str): Name of the payer folder to process
        max_files (int, optional): Maximum number of files to process (for testing)
        input_folder (str, optional): Override default input folder path
        output_folder (str, optional): Override default output folder path
        mapping_file (str, optional): Override default mapping file path
        save_combined (bool): Whether to save a _combined.xlsx file for testing

    Returns:
        dict: Results containing analytics data and file paths

    Example:
        >>> # Production run
        >>> result = quick_pipeline("Regence")
        >>> # Test run with limited files and combined output
        >>> result = quick_pipeline("Regence", max_files=3, save_combined=True)
        >>> print(f"Processed {result['file_summary']['total_rows']} rows")
        >>> print(f"Found {result['excel_stats']['total_eft_nums']} EFTs")
    """
    if PhilPipeline is None:
        raise ImportError("PhilPipeline could not be imported. Check your dependencies and file structure.")

    pipeline = PhilPipeline(
        payer_folder=payer_folder,
        input_folder=input_folder,
        output_folder=output_folder,
        mapping_file=mapping_file,
        max_files=max_files,
        save_combined=save_combined
    )
    return pipeline.run_full_pipeline()

# Library initialization
print(f"PHIL Analytics and QA Library v{__version__} loaded")
print(f"Supported payers: {len(get_supported_payers())} payer folders")