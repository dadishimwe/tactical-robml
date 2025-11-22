/*
============================================================================
ROBOT CONTROL SYSTEM - KEYBOARD CONTROLS
============================================================================
Keyboard mapping for desktop control
============================================================================
*/

let keyboardEnabled = true;
let activeKeys = new Set();

// ============================================================================
// KEYBOARD MAPPING
// ============================================================================

const keyMap = {
    // Movement
    'w': () => sendCommand('motor/forward'),
    's': () => sendCommand('motor/backward'),
    'a': () => sendCommand('motor/left'),
    'd': () => sendCommand('motor/right'),
    ' ': () => sendCommand('motor/stop'),
    
    // Speed
    'q': () => adjustSpeed(-20),
    'e': () => adjustSpeed(20),
    
    // Servos (select)
    '1': () => selectServo(1),
    '2': () => selectServo(2),
    '3': () => selectServo(3),
    '4': () => selectServo(4),
    
    // Recording
    'r': () => toggleRecording(),
    
    // Screenshot (placeholder)
    'p': () => takeScreenshot(),
    
    // HUD toggle
    'h': () => toggleHUD(),
    
    // ML toggle
    'm': () => toggleML(),
    
    // Fullscreen
    'f': () => toggleFullscreen(),
    
    // Emergency stop
    'Escape': () => emergencyStop()
};

const arrowKeyMap = {
    'ArrowUp': () => adjustSelectedServo(5),
    'ArrowDown': () => adjustSelectedServo(-5),
    'Home': () => centerServos(),
    'PageUp': () => loadPreset(1),
    'PageDown': () => loadPreset(0)
};

let selectedServo = 1;

// ============================================================================
// EVENT LISTENERS
// ============================================================================

document.addEventListener('keydown', function(e) {
    if (!keyboardEnabled) return;
    
    // Prevent default for control keys
    if (keyMap[e.key] || arrowKeyMap[e.key]) {
        e.preventDefault();
    }
    
    // Ignore repeated keydown events
    if (activeKeys.has(e.key)) return;
    activeKeys.add(e.key);
    
    // Handle regular keys
    if (keyMap[e.key]) {
        keyMap[e.key]();
    }
    
    // Handle arrow keys
    if (arrowKeyMap[e.key]) {
        arrowKeyMap[e.key]();
    }
});

document.addEventListener('keyup', function(e) {
    if (!keyboardEnabled) return;
    
    activeKeys.delete(e.key);
    
    // Stop motors when movement keys are released
    if (['w', 's', 'a', 'd'].includes(e.key)) {
        sendCommand('motor/stop');
    }
});

// ============================================================================
// KEYBOARD FUNCTIONS
// ============================================================================

function adjustSpeed(delta) {
    const slider = document.getElementById('speed-slider');
    let newSpeed = parseInt(slider.value) + delta;
    newSpeed = Math.max(50, Math.min(255, newSpeed));
    
    slider.value = newSpeed;
    updateSpeed(newSpeed);
}

function selectServo(num) {
    selectedServo = num;
    console.log(`[Keyboard] Servo ${num} selected`);
    
    // Visual feedback
    for (let i = 1; i <= 4; i++) {
        const slider = document.getElementById(`servo${i}`);
        if (i === num) {
            slider.style.boxShadow = '0 0 10px var(--color-accent-primary)';
        } else {
            slider.style.boxShadow = 'none';
        }
    }
}

function adjustSelectedServo(delta) {
    const slider = document.getElementById(`servo${selectedServo}`);
    let newAngle = parseInt(slider.value) + delta;
    newAngle = Math.max(0, Math.min(180, newAngle));
    
    slider.value = newAngle;
    updateServo(selectedServo, newAngle);
}

function takeScreenshot() {
    console.log('[Keyboard] Screenshot requested');
    
    // Get video feed image
    const videoFeed = document.getElementById('video-feed');
    
    // Create canvas to capture frame
    const canvas = document.createElement('canvas');
    canvas.width = videoFeed.naturalWidth || 640;
    canvas.height = videoFeed.naturalHeight || 480;
    
    const ctx = canvas.getContext('2d');
    ctx.drawImage(videoFeed, 0, 0, canvas.width, canvas.height);
    
    // Download as image
    canvas.toBlob(function(blob) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `robot_screenshot_${Date.now()}.png`;
        a.click();
        URL.revokeObjectURL(url);
        
        console.log('[Keyboard] Screenshot saved');
    });
}

function toggleFullscreen() {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(err => {
            console.error('[Keyboard] Fullscreen error:', err);
        });
    } else {
        document.exitFullscreen();
    }
}

function emergencyStop() {
    console.log('[Keyboard] EMERGENCY STOP');
    
    // Stop all motors
    sendCommand('motor/stop');
    
    // Stop autonomous mode if active
    if (isAutonomous) {
        toggleAutonomous();
    }
    
    // Visual feedback
    const body = document.body;
    body.style.borderColor = 'var(--color-accent-danger)';
    body.style.borderWidth = '5px';
    body.style.borderStyle = 'solid';
    
    setTimeout(() => {
        body.style.border = 'none';
    }, 500);
}

function toggleKeyboard() {
    keyboardEnabled = !keyboardEnabled;
    const btn = document.getElementById('keyboard-toggle-btn');
    
    if (keyboardEnabled) {
        btn.textContent = 'ON';
        btn.classList.remove('off');
        console.log('[Keyboard] Enabled');
    } else {
        btn.textContent = 'OFF';
        btn.classList.add('off');
        console.log('[Keyboard] Disabled');
    }
}

// ============================================================================
// HELP OVERLAY
// ============================================================================

function showKeyboardHelp() {
    const helpText = `
KEYBOARD CONTROLS
═════════════════════════════════════════

MOVEMENT:
  W - Forward
  S - Backward
  A - Turn Left
  D - Turn Right
  SPACE - Stop

SPEED:
  Q - Decrease Speed
  E - Increase Speed

SERVOS:
  1/2/3/4 - Select Servo
  ↑/↓ - Adjust Selected Servo
  HOME - Center All Servos
  PAGE UP - Preset 1
  PAGE DOWN - Preset 0

SYSTEM:
  R - Toggle Recording
  P - Take Screenshot
  H - Toggle HUD
  M - Toggle ML Detection
  F - Fullscreen
  ESC - Emergency Stop
    `;
    
    alert(helpText);
}

// Add help button listener
document.addEventListener('DOMContentLoaded', function() {
    // You can add a help button to the UI that calls showKeyboardHelp()
    console.log('[Keyboard] Controls loaded. Press ? for help.');
    
    // Show help on '?' key
    document.addEventListener('keydown', function(e) {
        if (e.key === '?' && e.shiftKey) {
            showKeyboardHelp();
        }
    });
});

console.log('[Keyboard] Script loaded');
