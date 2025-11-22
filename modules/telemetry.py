"""
============================================================================
TELEMETRY LOGGING MODULE
============================================================================

Handles logging of robot telemetry data for analysis and export.

Features:
  - Command logging
  - Distance measurements
  - Runtime statistics
  - CSV export
  - In-memory and file-based storage

============================================================================
"""

import json
import csv
import os
from datetime import datetime
from collections import deque
import threading
import time

class TelemetryLogger:
    """Telemetry data logger"""
    
    def __init__(self, log_dir='data/logs', max_memory_logs=1000):
        """
        Initialize telemetry logger
        
        Args:
            log_dir: Directory for log files
            max_memory_logs: Maximum logs to keep in memory
        """
        self.log_dir = log_dir
        self.max_memory_logs = max_memory_logs
        
        # In-memory log storage (for quick access)
        self.logs = deque(maxlen=max_memory_logs)
        self.lock = threading.Lock()
        
        # Statistics
        self.start_time = time.time()
        self.command_count = 0
        self.distance_readings = []
        
        # Create log directory
        os.makedirs(log_dir, exist_ok=True)
        
        # Current log file
        self.log_file = self._get_log_filename()
        
        print(f"[Telemetry] Initialized: {log_dir}")
    
    def _get_log_filename(self):
        """Generate log filename with date"""
        date_str = datetime.now().strftime('%Y%m%d')
        return os.path.join(self.log_dir, f'telemetry_{date_str}.jsonl')
    
    def log_command(self, category, command):
        """
        Log a command execution
        
        Args:
            category: Command category (motor, servo, recording, etc.)
            command: Command name or description
        """
        entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'command',
            'category': category,
            'command': command
        }
        
        self._add_log(entry)
        self.command_count += 1
    
    def log_distance(self, distance):
        """
        Log a distance measurement
        
        Args:
            distance: Distance in centimeters
        """
        entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'distance',
            'value': distance
        }
        
        self._add_log(entry)
        
        # Keep last 100 distance readings for statistics
        self.distance_readings.append(distance)
        if len(self.distance_readings) > 100:
            self.distance_readings.pop(0)
    
    def log_event(self, event_type, data):
        """
        Log a custom event
        
        Args:
            event_type: Type of event
            data: Event data (dict)
        """
        entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'event',
            'event_type': event_type,
            'data': data
        }
        
        self._add_log(entry)
    
    def _add_log(self, entry):
        """Add log entry to memory and file"""
        with self.lock:
            # Add to memory
            self.logs.append(entry)
            
            # Append to file
            try:
                with open(self.log_file, 'a') as f:
                    f.write(json.dumps(entry) + '\n')
            except Exception as e:
                print(f"[Telemetry] File write error: {e}")
    
    def get_recent_logs(self, limit=100):
        """
        Get recent log entries
        
        Args:
            limit: Maximum number of logs to return
        
        Returns:
            list: Recent log entries
        """
        with self.lock:
            logs = list(self.logs)
        
        # Return most recent first
        return logs[-limit:][::-1]
    
    def get_statistics(self):
        """
        Get telemetry statistics
        
        Returns:
            dict: Statistics summary
        """
        uptime = time.time() - self.start_time
        
        stats = {
            'uptime_seconds': int(uptime),
            'uptime_formatted': self._format_uptime(uptime),
            'total_commands': self.command_count,
            'total_logs': len(self.logs),
            'distance_stats': self._get_distance_stats()
        }
        
        return stats
    
    def _get_distance_stats(self):
        """Calculate distance statistics"""
        if not self.distance_readings:
            return {
                'count': 0,
                'min': 0,
                'max': 0,
                'avg': 0
            }
        
        return {
            'count': len(self.distance_readings),
            'min': min(self.distance_readings),
            'max': max(self.distance_readings),
            'avg': sum(self.distance_readings) / len(self.distance_readings)
        }
    
    def _format_uptime(self, seconds):
        """Format uptime as human-readable string"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def get_uptime(self):
        """Get formatted uptime"""
        return self._format_uptime(time.time() - self.start_time)
    
    def export_csv(self, filename=None):
        """
        Export logs to CSV file
        
        Args:
            filename: Output filename (auto-generated if None)
        
        Returns:
            str: Filename of exported CSV
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'telemetry_export_{timestamp}.csv'
        
        filepath = os.path.join(self.log_dir, filename)
        
        try:
            with self.lock:
                logs = list(self.logs)
            
            with open(filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow(['Timestamp', 'Type', 'Category', 'Command', 'Value', 'Data'])
                
                # Write data
                for log in logs:
                    writer.writerow([
                        log.get('timestamp', ''),
                        log.get('type', ''),
                        log.get('category', ''),
                        log.get('command', ''),
                        log.get('value', ''),
                        json.dumps(log.get('data', ''))
                    ])
            
            print(f"[Telemetry] Exported to {filename}")
            return filename
        
        except Exception as e:
            print(f"[Telemetry] Export error: {e}")
            return None
    
    def load_logs_from_file(self, date_str=None):
        """
        Load logs from file
        
        Args:
            date_str: Date string (YYYYMMDD) or None for today
        
        Returns:
            list: Log entries from file
        """
        if date_str is None:
            date_str = datetime.now().strftime('%Y%m%d')
        
        filename = os.path.join(self.log_dir, f'telemetry_{date_str}.jsonl')
        
        logs = []
        
        try:
            with open(filename, 'r') as f:
                for line in f:
                    logs.append(json.loads(line.strip()))
        
        except FileNotFoundError:
            print(f"[Telemetry] Log file not found: {filename}")
        except Exception as e:
            print(f"[Telemetry] Load error: {e}")
        
        return logs
    
    def clear_memory_logs(self):
        """Clear in-memory logs (file logs are preserved)"""
        with self.lock:
            self.logs.clear()
        
        print("[Telemetry] Memory logs cleared")
