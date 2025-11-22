/*
============================================================================
ROBOT CONTROL SYSTEM - TELEMETRY JAVASCRIPT
============================================================================
Handles telemetry data display and export
============================================================================
*/

// ============================================================================
// TELEMETRY UPDATES
// ============================================================================

function refreshStats() {
    fetch('/api/telemetry/stats')
    .then(response => response.json())
    .then(data => {
        updateTelemetryDisplay(data);
    })
    .catch(error => {
        console.error('[Telemetry] Error:', error);
    });
}

function updateTelemetryDisplay(stats) {
    // Update uptime
    if (stats.uptime_formatted) {
        document.getElementById('uptime').textContent = stats.uptime_formatted;
    }
    
    // Update command count
    if (stats.total_commands !== undefined) {
        document.getElementById('command-count').textContent = stats.total_commands;
    }
    
    // Update distance statistics
    if (stats.distance_stats) {
        const ds = stats.distance_stats;
        
        if (ds.count > 0) {
            document.getElementById('dist-min').textContent = `${ds.min} cm`;
            document.getElementById('dist-max').textContent = `${ds.max} cm`;
            document.getElementById('dist-avg').textContent = `${ds.avg.toFixed(1)} cm`;
        }
    }
}

function exportTelemetry() {
    console.log('[Telemetry] Exporting data...');
    
    // Trigger CSV download
    window.location.href = '/api/telemetry/export';
    
    // Show confirmation
    setTimeout(() => {
        alert('Telemetry data exported successfully!');
    }, 500);
}

// ============================================================================
// AUTO-REFRESH
// ============================================================================

// Refresh telemetry every 5 seconds
setInterval(refreshStats, 5000);

// Initial load
document.addEventListener('DOMContentLoaded', function() {
    refreshStats();
    console.log('[Telemetry] Script loaded');
});
