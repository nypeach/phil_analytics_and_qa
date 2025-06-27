# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PHIL Analytics and QA is a Python library for processing healthcare payment data from insurance payers. The system combines multiple Excel files, scrubs and validates payment data, and generates analytics reports. It processes "Import Posting Reports" from various insurance payers like Regence, Zelis, and others.

## Architecture

The system follows a pipeline architecture with these main components:

- **PhilPipeline** (`phil_analytics/pipeline.py`): Main orchestrator that coordinates the full workflow
- **ExcelCombiner** (`phil_analytics/combiner.py`): Combines multiple Excel files from payer folders
- **DataCleaner** (`phil_analytics/scrubber.py`): Scrubs and validates payment data using business rules
- **ExcelDataProcessor** (`phil_analytics/excel_data_processor.py`): Processes Excel data for detailed analytics
- **AnalyticsGenerator** (`phil_analytics/analytics.py`): Generates analytics reports (currently empty)

The data flow: Raw Excel files → Combined DataFrame → Scrubbed DataFrame → Analytics Reports → Output files

## Configuration

- Copy `config.py.template` to `config.py` and customize paths
- Main config options:
  - `PAYERS`: List of supported payer folder names (29 payers supported)
  - `DATA_ROOT`, `INPUT_FOLDER`, `OUTPUT_FOLDER`: Data path configuration
  - `MAPPING_FILE`: Excel mapping file for data validation
  - `VERBOSE_OUTPUT`: Enable detailed logging
  - `SAVE_INTERMEDIATE_FILES`: Save scrubbed files during processing

## Common Commands

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Setup configuration
cp config.py.template config.py
# Edit config.py with your specific paths
```

### Running the Pipeline
```bash
# Run the library directly (processes Regence payer by default)
python -m phil_analytics

# Run test pipeline with limited file processing
python -c "from phil_analytics import test_pipeline; test_pipeline('Regence', max_files=3)"

# Use the quick pipeline function
python -c "from phil_analytics import quick_pipeline; quick_pipeline('Regence')"
```

### Development Usage
```python
# Full pipeline
from phil_analytics import PhilPipeline
pipeline = PhilPipeline("Regence")
results = pipeline.run_combine_and_scrub()

# Individual components
from phil_analytics.combiner import ExcelCombiner
from phil_analytics.scrubber import DataCleaner

combiner = ExcelCombiner("data/input/Regence")
combined_data = combiner.combine_files()

cleaner = DataCleaner("data/mappings/Proliance Mapping.xlsx")
scrubbed_data = cleaner.clean_data(combined_data)
```

## Data Structure

- **Input**: Excel files in `data/input/{payer_folder}/` named like `{Payer}_{YYYYMMDD}_{NN}_Import Posting Report.xlsx`
- **Mappings**: `data/mappings/Proliance Mapping.xlsx` contains validation rules
- **Output**: Processed files saved to `data/output/{payer_folder}_output/{payer_folder}_Scrubbed.xlsx`

## Dependencies

Based on the imports found in the codebase:
- `pandas` - Data manipulation and analysis
- `openpyxl` - Excel file reading/writing
- Built-in modules: `os`, `time`, `re`, `typing`, `collections`, `decimal`

Note: `requirements.txt` appears to be empty and should be populated with the actual dependencies.

## Development Notes

- The system processes healthcare payment data and handles sensitive information
- Data folders are gitignored for security
- The pipeline supports test mode with limited file processing (`max_files` parameter)
- Error handling is implemented through custom exceptions in `phil_analytics/exceptions.py`
- Utility functions for formatting and processing are in `phil_analytics/utils.py`
- The main entry point supports both library usage and direct execution
- Pipeline provides detailed logging with emoji indicators for different processing stages