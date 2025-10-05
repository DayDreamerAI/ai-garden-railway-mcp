#!/usr/bin/env python3
"""
AI Garden Logging Infrastructure
Provides structured, timestamped logging with audit trail capabilities
for multi-agent federation operational visibility.

Created: 2025-09-12T22:48:30Z
Phase: 0.1 - Operational Infrastructure Setup
"""

import logging
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional


class AIGardenLogger:
    """
    Structured logger for AI Garden operations with audit trail capabilities.
    
    Features:
    - ISO 8601 timestamps for all entries
    - JSON-structured audit logs
    - Component-based log segregation
    - Automatic log rotation by date
    - Console and file output
    """
    
    def __init__(self, component_name: str, log_level: str = "INFO"):
        self.component = component_name
        self.log_level = getattr(logging, log_level.upper())
        self.setup_timestamp = datetime.now(timezone.utc).isoformat()
        
        # Ensure log directory exists
        self.log_dir = Path("/tmp/ai-garden-logs")
        self.log_dir.mkdir(exist_ok=True)
        
        self.setup_logging()
        self.audit("logger_initialized", {
            "component": component_name,
            "log_level": log_level,
            "log_dir": str(self.log_dir),
            "setup_timestamp": self.setup_timestamp
        })
    
    def setup_logging(self):
        """Configure logging handlers for console and file output."""
        
        # Create logger
        self.logger = logging.getLogger(f"ai-garden.{self.component}")
        self.logger.setLevel(self.log_level)
        
        # Prevent duplicate handlers
        if self.logger.handlers:
            return
        
        # JSON formatter for structured logging
        log_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_format)
        console_handler.setLevel(self.log_level)
        
        # File handler with daily rotation
        log_file = self.log_dir / f"ai-garden-{self.component}-{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(str(log_file))
        file_handler.setFormatter(log_format)
        file_handler.setLevel(self.log_level)
        
        # Add handlers
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
    
    def audit(self, action: str, details: Dict[str, Any], level: str = "INFO"):
        """
        Create timestamped audit entry with structured data.
        
        Args:
            action: Action being audited (snake_case)
            details: Structured details about the action
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "component": self.component,
            "action": action,
            "details": details,
            "type": "AUDIT",
            "log_level": level
        }
        
        # Log to main logger
        log_func = getattr(self.logger, level.lower())
        log_func(json.dumps(audit_entry, separators=(',', ':')))
        
        # Also write to audit-specific file
        audit_file = self.log_dir / f"ai-garden-audit-{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(audit_file, 'a') as f:
            f.write(json.dumps(audit_entry) + "\\n")
    
    def info(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Log info message with optional structured details."""
        if details:
            self.audit("info_message", {"message": message, **details}, "INFO")
        else:
            self.logger.info(message)
    
    def error(self, message: str, error: Optional[Exception] = None, details: Optional[Dict[str, Any]] = None):
        """Log error message with exception details."""
        error_details = {"message": message}
        
        if error:
            error_details.update({
                "error_type": type(error).__name__,
                "error_message": str(error),
                "error_args": error.args if error.args else None
            })
        
        if details:
            error_details.update(details)
        
        self.audit("error_logged", error_details, "ERROR")
    
    def performance(self, operation: str, duration_ms: float, details: Optional[Dict[str, Any]] = None):
        """Log performance metrics for operations."""
        perf_details = {
            "operation": operation,
            "duration_ms": round(duration_ms, 2)
        }
        
        if details:
            perf_details.update(details)
        
        self.audit("performance_metric", perf_details, "INFO")
    
    def security(self, event: str, details: Dict[str, Any], level: str = "WARNING"):
        """Log security-related events."""
        security_details = {
            "security_event": event,
            **details
        }
        
        self.audit("security_event", security_details, level)


class OperationalMetrics:
    """
    Centralized metrics collection for AI Garden operations.
    """
    
    def __init__(self):
        self.logger = AIGardenLogger("metrics")
        self.metrics_file = Path("/tmp/ai-garden-logs/operational-metrics.json")
        self.start_time = datetime.now(timezone.utc).isoformat()
        
        self.metrics = {
            "session_start": self.start_time,
            "phases_completed": [],
            "current_phase": None,
            "agents_configured": 0,
            "operations_count": 0,
            "errors_count": 0,
            "last_updated": self.start_time
        }
        
        self.save_metrics()
    
    def update_phase(self, phase: str, status: str = "started"):
        """Update current phase status."""
        self.metrics["current_phase"] = f"{phase}_{status}"
        
        if status == "completed":
            self.metrics["phases_completed"].append({
                "phase": phase,
                "completed_at": datetime.now(timezone.utc).isoformat()
            })
        
        self.save_metrics()
        self.logger.audit("phase_update", {
            "phase": phase,
            "status": status,
            "total_phases_completed": len(self.metrics["phases_completed"])
        })
    
    def increment_counter(self, counter: str, amount: int = 1):
        """Increment operational counters."""
        if counter in self.metrics:
            self.metrics[counter] += amount
        else:
            self.metrics[counter] = amount
        
        self.save_metrics()
    
    def save_metrics(self):
        """Save metrics to file with timestamp."""
        self.metrics["last_updated"] = datetime.now(timezone.utc).isoformat()
        
        with open(self.metrics_file, 'w') as f:
            json.dump(self.metrics, f, indent=2)


# Global metrics instance
operational_metrics = OperationalMetrics()


def get_logger(component: str, log_level: str = "INFO") -> AIGardenLogger:
    """Factory function to create component loggers."""
    return AIGardenLogger(component, log_level)


if __name__ == "__main__":
    # Test the logging system
    print(f"🚀 AI Garden Logging System Test - {datetime.now(timezone.utc).isoformat()}")
    
    # Test basic logging
    logger = get_logger("test")
    logger.info("Logging system initialized successfully")
    
    # Test audit logging
    logger.audit("system_test", {
        "test_type": "initialization", 
        "duration_ms": 150,
        "status": "success"
    })
    
    # Test performance logging  
    logger.performance("logging_test", 45.7, {"components_tested": 3})
    
    # Test error logging
    try:
        raise ValueError("Test error for logging validation")
    except ValueError as e:
        logger.error("Test error logged", e, {"test_context": "validation"})
    
    # Test metrics
    operational_metrics.update_phase("0_test", "completed")
    operational_metrics.increment_counter("test_operations")
    
    print("✅ Logging system validation complete")
    print(f"📊 Logs location: /tmp/ai-garden-logs/")
    print(f"📋 Audit trail: ai-garden-audit-{datetime.now().strftime('%Y%m%d')}.jsonl")