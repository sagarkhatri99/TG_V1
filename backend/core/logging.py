"""
Structured JSON logging setup for FastAPI application.
Provides correlation IDs and request tracing across all modules.
"""

import logging
import json
import sys
import uuid
from datetime import datetime
from typing import Optional
from pythonjsonlogger import jsonlogger
from fastapi import Request
from contextvars import ContextVar

# Context variable for storing correlation ID per request
correlation_id_var: ContextVar[str] = ContextVar('correlation_id', default=None)


class CorrelationIdFilter(logging.Filter):
    """Add correlation_id to all log records"""
    def filter(self, record):
        correlation_id = correlation_id_var.get()
        record.correlation_id = correlation_id or 'no-correlation-id'
        return True


class JSONFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional context"""
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp in ISO format
        log_record['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        
        # Add log level
        log_record['level'] = record.levelname
        
        # Add module name
        log_record['module'] = record.name
        
        # Add correlation ID
        log_record['correlation_id'] = record.correlation_id
        
        # Add function and line number for debugging
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno
        
        # Add process/thread info in dev mode only
        if hasattr(record, 'process'):
            log_record['process_id'] = record.process
        if hasattr(record, 'thread'):
            log_record['thread_id'] = record.thread


def setup_json_logging(
    environment: str = "development",
    log_level: str = "INFO"
) -> None:
    """
    Configure structured JSON logging across all modules.
    
    Args:
        environment: "production" or "development"
        log_level: logging level (INFO, DEBUG, WARNING, ERROR)
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler with JSON formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level))
    
    # Apply JSON formatter
    json_formatter = JSONFormatter(
        '%(timestamp)s %(level)s %(correlation_id)s %(module)s %(function)s %(line)d %(message)s'
    )
    console_handler.setFormatter(json_formatter)
    
    # Add correlation ID filter to all handlers
    correlation_filter = CorrelationIdFilter()
    console_handler.addFilter(correlation_filter)
    
    root_logger.addHandler(console_handler)
    
    # Set specific loggers to avoid noise
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    # In development, enable SQL query logging at DEBUG level
    if environment == "development":
        logging.getLogger("sqlalchemy.engine").setLevel(logging.DEBUG)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


async def set_correlation_id(request: Request) -> Optional[str]:
    """
    Extract or generate correlation ID from request and store in context.
    
    Args:
        request: FastAPI request object
    
    Returns:
        Correlation ID string
    """
    # Try to get from headers (X-Correlation-ID or X-Request-ID)
    correlation_id = (
        request.headers.get('X-Correlation-ID') or
        request.headers.get('X-Request-ID') or
        str(uuid.uuid4())
    )
    
    # Set in context variable
    correlation_id_var.set(correlation_id)
    
    return correlation_id


# Convenience function to set correlation ID in other contexts
def set_correlation_id_for_context(cid: str) -> None:
    """Set correlation ID in current context"""
    correlation_id_var.set(cid)


def get_correlation_id() -> Optional[str]:
    """Get correlation ID from current context"""
    return correlation_id_var.get()
