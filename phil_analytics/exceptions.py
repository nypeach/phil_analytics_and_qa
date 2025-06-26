"""
PHIL Analytics and QA Library - Custom Exceptions

This module defines custom exception classes for the PHIL Analytics library
to provide clear error handling and debugging information.
"""


class PhilAnalyticsError(Exception):
    """
    Base exception class for all PHIL Analytics library errors.

    All other custom exceptions in this library inherit from this base class,
    allowing users to catch all library-specific errors with a single except clause.
    """

    def __init__(self, message, error_code=None, details=None):
        """
        Initialize the base exception.

        Args:
            message (str): Human-readable error message
            error_code (str, optional): Error code for programmatic handling
            details (dict, optional): Additional error details
        """
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}
        print(f"❌ PHIL Analytics Error: {message}")

    def __str__(self):
        """Return a formatted error message."""
        base_msg = super().__str__()
        if self.error_code:
            base_msg = f"[{self.error_code}] {base_msg}"
        if self.details:
            detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            base_msg = f"{base_msg} (Details: {detail_str})"
        return base_msg


class DataProcessingError(PhilAnalyticsError):
    """
    Exception raised when data processing operations fail.

    This includes errors during data transformation, validation,
    or any step in the scrubbing pipeline.
    """

    def __init__(self, message, operation=None, row_index=None, column=None, **kwargs):
        """
        Initialize data processing error.

        Args:
            message (str): Error description
            operation (str, optional): The operation that failed
            row_index (int, optional): Row index where error occurred
            column (str, optional): Column name where error occurred
        """
        details = kwargs
        if operation:
            details['operation'] = operation
        if row_index is not None:
            details['row_index'] = row_index
        if column:
            details['column'] = column

        super().__init__(message, error_code="DATA_PROCESSING", details=details)
        print(f"🔧 Data processing failed at operation: {operation}")


class FileNotFoundError(PhilAnalyticsError):
    """
    Exception raised when required files or folders cannot be found.

    This includes Excel files, mapping files, input folders, etc.
    """

    def __init__(self, file_path, file_type="file", expected_location=None):
        """
        Initialize file not found error.

        Args:
            file_path (str): Path that could not be found
            file_type (str): Type of file/folder (e.g., "Excel file", "mapping file")
            expected_location (str, optional): Where the file was expected to be
        """
        message = f"{file_type.title()} not found: {file_path}"
        details = {'file_path': file_path, 'file_type': file_type}
        if expected_location:
            details['expected_location'] = expected_location
            message += f" (Expected in: {expected_location})"

        super().__init__(message, error_code="FILE_NOT_FOUND", details=details)
        print(f"📁 Missing {file_type}: {file_path}")


class ValidationError(PhilAnalyticsError):
    """
    Exception raised when data validation fails.

    This includes header mismatches, data type validation failures,
    business rule violations, etc.
    """

    def __init__(self, message, validation_type=None, expected=None, actual=None, **kwargs):
        """
        Initialize validation error.

        Args:
            message (str): Validation error description
            validation_type (str, optional): Type of validation that failed
            expected (any, optional): Expected value
            actual (any, optional): Actual value found
        """
        details = kwargs
        if validation_type:
            details['validation_type'] = validation_type
        if expected is not None:
            details['expected'] = expected
        if actual is not None:
            details['actual'] = actual

        super().__init__(message, error_code="VALIDATION", details=details)
        print(f"✅ Validation failed: {validation_type}")


class MappingError(PhilAnalyticsError):
    """
    Exception raised when mapping file operations fail.

    This includes missing mapping sheets, invalid mapping data,
    or lookup failures.
    """

    def __init__(self, message, mapping_type=None, sheet_name=None, lookup_key=None):
        """
        Initialize mapping error.

        Args:
            message (str): Mapping error description
            mapping_type (str, optional): Type of mapping (e.g., "practice", "payer")
            sheet_name (str, optional): Excel sheet name
            lookup_key (str, optional): Key that failed lookup
        """
        details = {}
        if mapping_type:
            details['mapping_type'] = mapping_type
        if sheet_name:
            details['sheet_name'] = sheet_name
        if lookup_key:
            details['lookup_key'] = lookup_key

        super().__init__(message, error_code="MAPPING", details=details)
        print(f"🗺️ Mapping error in {mapping_type}: {lookup_key}")


class ConfigurationError(PhilAnalyticsError):
    """
    Exception raised when configuration is invalid or missing.

    This includes missing config files, invalid paths,
    or incorrect configuration values.
    """

    def __init__(self, message, config_key=None, config_value=None):
        """
        Initialize configuration error.

        Args:
            message (str): Configuration error description
            config_key (str, optional): Configuration key with issue
            config_value (any, optional): Invalid configuration value
        """
        details = {}
        if config_key:
            details['config_key'] = config_key
        if config_value is not None:
            details['config_value'] = config_value

        super().__init__(message, error_code="CONFIGURATION", details=details)
        print(f"⚙️ Configuration error: {config_key}")


class AnalyticsError(PhilAnalyticsError):
    """
    Exception raised when analytics generation fails.

    This includes report generation errors, data aggregation failures,
    or output file writing issues.
    """

    def __init__(self, message, analytics_type=None, payer_folder=None, **kwargs):
        """
        Initialize analytics error.

        Args:
            message (str): Analytics error description
            analytics_type (str, optional): Type of analytics operation
            payer_folder (str, optional): Payer folder being processed
        """
        details = kwargs
        if analytics_type:
            details['analytics_type'] = analytics_type
        if payer_folder:
            details['payer_folder'] = payer_folder

        super().__init__(message, error_code="ANALYTICS", details=details)
        print(f"📊 Analytics generation failed: {analytics_type}")


# Utility function for error reporting
def handle_error(error, context=None, reraise=True):
    """
    Centralized error handling utility.

    Args:
        error (Exception): The exception that occurred
        context (str, optional): Additional context about where error occurred
        reraise (bool): Whether to re-raise the exception after logging

    Raises:
        Exception: Re-raises the original exception if reraise=True
    """
    error_type = type(error).__name__
    error_msg = str(error)

    if context:
        print(f"🚨 Error in {context}: {error_type} - {error_msg}")
    else:
        print(f"🚨 {error_type}: {error_msg}")

    # Log additional details if it's a PhilAnalyticsError
    if isinstance(error, PhilAnalyticsError):
        if hasattr(error, 'details') and error.details:
            print(f"   📋 Details: {error.details}")

    if reraise:
        raise error