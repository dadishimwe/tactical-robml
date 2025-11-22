/*
============================================================================
ROBOT CONTROL SYSTEM - MAIN CONTROLS JAVASCRIPT
============================================================================
Handles all robot control interactions and real-time updates
============================================================================
*/

// ============================================================================
// GLOBAL STATE
// ============================================================================

let socket = null;
let isRecording = false;
let isAutonomous = false;
let isMLEnabled = false;
let hudEnabled = true;
let currentSpeed = 200;

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('[Controls] Initializing...');
    
    // Initialize Socket.IO connection
    initializeSocket();
    
    // Start real-time updates
    startRealtimeUpdates();
    
    // Update clock
    updateClock();
    setInterval(updateClock, 1000);
    
    console.log('[Controls] Initialized');
});

// ============================================================================
// SOCKET.IO CONNECTION
// ============================================================================

function initializeSocket() {
    socket = io();
    
    socket.on('connect', function() {
        console.log('[Socket] Connected');
        updateConnectionStatus(true);
    });
    
    socket.on('disconnect', function() {
        console.log('[Socket] Disconnected');
        updateConnectionStatus(false);
    });
    
    socket.on('distance_update', function(data) {
        updateDistance(data.distance);
    });
    
    socket.on('status_update', function(data) {
        updateStatus(data);
    });
}

function updateConnectionStatus(connected) {
    const statusIcon = document.getElementById('connection-status');
    if (connected) {
        statusIcon.classList.remove('disconnected');
        statusIcon.style.color = 'var(--color-accent-primary)';
    } else {
        statusIcon.classList.add('disconnected');
        statusIcon.style.color = 'var(--color-accent-danger)';
    }
}

// ============================================================================
// MOTOR CONTROLS
// ============================================================================

function sendCommand(endpoint) {
    fetch(`/api/${endpoint}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (!data.success && data.error) {
            console.error('[Command] Error:', data.error);
        }
    })
    .catch(error => {
        console.error('[Command] Failed:', error);
    });
}

function updateSpeed(value) {
    currentSpeed = parseInt(value);
    document.getElementById('speed-display').textContent = currentSpeed;
    document.getElementById('hud-speed').textContent = currentSpeed;
    
    // Send speed update to server
    fetch('/api/motor/speed', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ speed: currentSpeed })
    })
    .then(response => response.json())
    .then(data => {
        if (!data.success) {
            console.error('[Speed] Update failed');
        }
    })
    .catch(error => {
        console.error('[Speed] Error:', error);
    });
}

// ============================================================================
// SERVO CONTROLS
// ============================================================================

function updateServo(servoNum, angle) {
    angle = parseInt(angle);
    
    // Update display
    document.getElementById(`servo${servoNum}-value`).textContent = `${angle}°`;
    
    // Send to server
    fetch('/api/servo/set', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ servo: servoNum, angle: angle })
    })
    .then(response => response.json())
    .then(data => {
        if (!data.success) {
            console.error(`[Servo ${servoNum}] Update failed`);
        }
    })
    .catch(error => {
        console.error(`[Servo ${servoNum}] Error:`, error);
    });
}

function loadPreset(presetNum) {
    fetch('/api/servo/preset', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ preset: presetNum })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log(`[Preset] Loaded preset ${presetNum}`);
            // Refresh servo positions from server
            setTimeout(refreshServoPositions, 500);
        }
    })
    .catch(error => {
        console.error('[Preset] Error:', error);
    });
}

function centerServos() {
    fetch('/api/servo/center', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Reset all sliders to 90
            for (let i = 1; i <= 4; i++) {
                document.getElementById(`servo${i}`).value = 90;
                document.getElementById(`servo${i}-value`).textContent = '90°';
            }
        }
    })
    .catch(error => {
        console.error('[Center] Error:', error);
    });
}

function refreshServoPositions() {
    fetch('/api/status')
    .then(response => response.json())
    .then(data => {
        if (data.servo && data.servo.positions) {
            data.servo.positions.forEach((angle, index) => {
                const servoNum = index + 1;
                document.getElementById(`servo${servoNum}`).value = angle;
                document.getElementById(`servo${servoNum}-value`).textContent = `${angle}°`;
            });
        }
    })
    .catch(error => {
        console.error('[Servo Refresh] Error:', error);
    });
}

// ============================================================================
// VIDEO RECORDING
// ============================================================================

function toggleRecording() {
    const btn = document.getElementById('record-btn');
    
    if (isRecording) {
        // Stop recording
        fetch('/api/recording/stop', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                isRecording = false;
                btn.classList.remove('recording');
                console.log('[Recording] Stopped:', data.filename);
            }
        })
        .catch(error => {
            console.error('[Recording] Stop error:', error);
        });
    } else {
        // Start recording
        fetch('/api/recording/start', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                isRecording = true;
                btn.classList.add('recording');
                console.log('[Recording] Started:', data.filename);
            }
        })
        .catch(error => {
            console.error('[Recording] Start error:', error);
        });
    }
}

// ============================================================================
// AUTONOMOUS MODE
// ============================================================================

function toggleAutonomous() {
    const btn = document.getElementById('auto-btn');
    
    if (isAutonomous) {
        // Stop autonomous
        fetch('/api/autonomous/stop', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                isAutonomous = false;
                btn.classList.remove('active');
                document.getElementById('current-mode').textContent = 'MANUAL';
                console.log('[Autonomous] Stopped');
            }
        })
        .catch(error => {
            console.error('[Autonomous] Stop error:', error);
        });
    } else {
        // Start autonomous
        fetch('/api/autonomous/start', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                isAutonomous = true;
                btn.classList.add('active');
                document.getElementById('current-mode').textContent = 'AUTO';
                console.log('[Autonomous] Started');
            }
        })
        .catch(error => {
            console.error('[Autonomous] Start error:', error);
        });
    }
}

// ============================================================================
// ML DETECTION
// ============================================================================

function toggleML() {
    const btn = document.getElementById('ml-btn');
    
    fetch('/api/ml/toggle', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ enable: !isMLEnabled })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            isMLEnabled = data.enabled;
            if (isMLEnabled) {
                btn.classList.add('active');
                console.log('[ML] Enabled');
            } else {
                btn.classList.remove('active');
                console.log('[ML] Disabled');
            }
        } else {
            console.warn('[ML] Not available');
            alert('ML module not available. Install dependencies to enable.');
        }
    })
    .catch(error => {
        console.error('[ML] Toggle error:', error);
    });
}

// ============================================================================
// REAL-TIME UPDATES
// ============================================================================

function startRealtimeUpdates() {
    // Request updates every 500ms
    setInterval(function() {
        if (socket && socket.connected) {
            socket.emit('request_update');
        }
    }, 500);
    
    // Fetch full status every 2 seconds
    setInterval(refreshStatus, 2000);
}

function refreshStatus() {
    fetch('/api/status')
    .then(response => response.json())
    .then(data => {
        updateStatus(data);
    })
    .catch(error => {
        console.error('[Status] Error:', error);
    });
}

function updateStatus(data) {
    // Update motor direction
    if (data.motor && data.motor.direction) {
        document.getElementById('hud-direction').textContent = data.motor.direction;
    }
    
    // Update speed
    if (data.speed !== undefined) {
        document.getElementById('hud-speed').textContent = data.speed;
    }
    
    // Update recording status
    if (data.recording !== undefined) {
        isRecording = data.recording;
        const btn = document.getElementById('record-btn');
        if (isRecording) {
            btn.classList.add('recording');
        } else {
            btn.classList.remove('recording');
        }
    }
    
    // Update autonomous status
    if (data.autonomous !== undefined) {
        isAutonomous = data.autonomous;
        const btn = document.getElementById('auto-btn');
        if (isAutonomous) {
            btn.classList.add('active');
            document.getElementById('current-mode').textContent = 'AUTO';
        } else {
            btn.classList.remove('active');
            document.getElementById('current-mode').textContent = 'MANUAL';
        }
    }
}

function updateDistance(distance) {
    // Update HUD display
    const distDisplay = document.querySelector('.distance-number');
    if (distDisplay) {
        distDisplay.textContent = distance > 0 ? distance : '--';
    }
    
    // Update telemetry
    document.getElementById('dist-current').textContent = `${distance} cm`;
    
    // Update radar blip position (closer = more centered)
    const blip = document.getElementById('radar-blip');
    if (blip && distance > 0) {
        const maxDist = 100; // cm
        const percentage = Math.min(distance / maxDist, 1);
        const offset = percentage * 40; // max 40px from center
        blip.style.transform = `translate(-50%, calc(-50% - ${offset}px))`;
    }
}

// ============================================================================
// UI CONTROLS
// ============================================================================

function toggleSettings() {
    const modal = document.getElementById('settings-modal');
    modal.classList.toggle('active');
}

function toggleHUD() {
    hudEnabled = !hudEnabled;
    const overlay = document.getElementById('hud-overlay');
    const btn = document.getElementById('hud-toggle-btn');
    
    if (hudEnabled) {
        overlay.style.display = 'block';
        btn.textContent = 'ON';
        btn.classList.remove('off');
    } else {
        overlay.style.display = 'none';
        btn.textContent = 'OFF';
        btn.classList.add('off');
    }
}

function toggleTelemetry() {
    const content = document.getElementById('telemetry-content');
    const icon = document.getElementById('telemetry-toggle');
    
    content.classList.toggle('collapsed');
    icon.textContent = content.classList.contains('collapsed') ? '▼' : '▲';
}

function updateClock() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('en-US', { hour12: false });
    document.getElementById('time-display').textContent = timeStr;
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

// Prevent context menu on long press (mobile)
document.addEventListener('contextmenu', function(e) {
    e.preventDefault();
});

// Prevent double-tap zoom (mobile)
let lastTouchEnd = 0;
document.addEventListener('touchend', function(e) {
    const now = Date.now();
    if (now - lastTouchEnd <= 300) {
        e.preventDefault();
    }
    lastTouchEnd = now;
}, false);

console.log('[Controls] Script loaded');
