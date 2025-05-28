// Global configuration
const CONFIG = {
    API_VERSION: '1.0.0',
    API_BASE_URL: '/api/v1',
    REFRESH_INTERVAL: 5000, // 5 seconds
    MAX_RETRIES: 3,
    TIMEOUT: 10000 // 10 seconds
};

// Global error handler
window.onerror = function(msg, url, lineNo, columnNo, error) {
    console.error('Global error:', {
        message: msg,
        url: url,
        line: lineNo,
        column: columnNo,
        error: error,
        timestamp: new Date().toISOString()
    });
    
    // Show user friendly error
    showNotification('An error occurred. Please try again or contact support.', 'error');
    return false;
};

// Utility functions
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} notification`;
    notification.textContent = message;
    
    // Remove existing notifications
    document.querySelectorAll('.notification').forEach(n => n.remove());
    
    // Add new notification
    document.body.prepend(notification);
    
    // Remove after 5 seconds
    setTimeout(() => notification.remove(), 5000);
}

function formatBytes(bytes, decimals = 2) {
    if (!bytes) return '0 Bytes';
    
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

function formatUptime(seconds) {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = seconds % 60;
    
    return `${days}d ${hours}h ${minutes}m ${remainingSeconds}s`;
}

// Authentication functions
function checkAuth() {
    const token = localStorage.getItem('token');
    if (!token && !window.location.pathname.includes('/login')) {
        window.location.href = '/login';
        return false;
    }
    return true;
}

async function refreshToken() {
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/auth/refresh`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Token refresh failed');
        }
        
        const data = await response.json();
        localStorage.setItem('token', data.token);
        return true;
    } catch (error) {
        console.error('Token refresh error:', error);
        logout();
        return false;
    }
}

async function fetchWithAuth(url, options = {}) {
    if (!checkAuth()) return;
    
    let retries = 0;
    
    while (retries < CONFIG.MAX_RETRIES) {
        try {
            const token = localStorage.getItem('token');
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), CONFIG.TIMEOUT);
            
            const response = await fetch(url, {
                ...options,
                headers: {
                    ...options.headers,
                    'Authorization': `Bearer ${token}`,
                    'X-API-Version': CONFIG.API_VERSION
                },
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (response.status === 401) {
                // Token expired
                const refreshed = await refreshToken();
                if (refreshed) {
                    retries++;
                    continue;
                }
                logout();
                return;
            }
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return response;
            
        } catch (error) {
            if (error.name === 'AbortError') {
                console.error('Request timeout');
                showNotification('Request timeout. Please try again.', 'warning');
            } else {
                console.error('Fetch error:', error);
                if (retries === CONFIG.MAX_RETRIES - 1) {
                    showNotification('Failed to complete request. Please try again.', 'error');
                }
            }
            retries++;
        }
    }
}

function logout() {
    try {
        // Clear all auth data
        localStorage.clear();
        // Clear any sensitive data from sessionStorage
        sessionStorage.clear();
        // Clear any cookies
        document.cookie.split(";").forEach(c => {
            document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/");
        });
        // Redirect to login
        window.location.href = '/login';
    } catch (error) {
        console.error('Logout error:', error);
        // Force redirect even if there's an error
        window.location.href = '/login';
    }
}

// Dashboard functions
async function updateStats() {
    try {
        const response = await fetchWithAuth(`${CONFIG.API_BASE_URL}/stats`);
        if (!response) return;
        
        const data = await response.json();
        
        if (!data.system) {
            throw new Error('Invalid response format: missing system data');
        }
        
        // Update memory
        updateSystemMetric('memory', data.system.memory);
        
        // Update CPU
        updateSystemMetric('cpu', {
            percent: data.system.cpu_percent,
            label: `${data.system.cpu_percent}%`
        });
        
        // Update disk
        updateSystemMetric('disk', data.system.disk);
        
    } catch (error) {
        console.error('Error updating stats:', error);
        showNotification('Failed to update system stats', 'warning');
    }
}

function updateSystemMetric(type, data) {
    const bar = document.getElementById(`${type}Bar`);
    const detail = document.getElementById(`${type}Detail`);
    
    if (!bar || !detail) return;
    
    const percent = data.percent;
    bar.style.width = `${percent}%`;
    bar.className = `progress ${percent > 90 ? 'bg-danger' : percent > 70 ? 'bg-warning' : 'bg-success'}`;
    
    if (type === 'memory' || type === 'disk') {
        detail.textContent = `${percent}% (${formatBytes(data.used)} / ${formatBytes(data.total)})`;
    } else {
        detail.textContent = `${percent}%`;
    }
}

async function refreshLogs() {
    try {
        const logLevel = document.getElementById('logLevel').value;
        const response = await fetchWithAuth(`${CONFIG.API_BASE_URL}/logs?level=${logLevel}`);
        if (!response) return;
        
        const data = await response.json();
        const logsView = document.getElementById('logsView');
        
        if (!logsView) return;
        
        logsView.innerHTML = data.logs.map(log => `
            <div class="log-entry ${log.level.toLowerCase()}">
                <span class="timestamp">${log.timestamp}</span>
                <span class="level">${log.level}</span>
                <span class="message">${log.message}</span>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error refreshing logs:', error);
        showNotification('Failed to refresh logs', 'error');
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    try {
        // Check authentication
        if (!checkAuth()) return;
        
        // Setup error handling for dynamic elements
        setupErrorHandling();
        
        // Initialize dashboard if on dashboard page
        if (window.location.pathname.includes('/dashboard')) {
            initializeDashboard();
        }
        
        // Add CSRF token to all forms
        setupCSRF();
        
    } catch (error) {
        console.error('Initialization error:', error);
        showNotification('Failed to initialize application', 'error');
    }
});

function setupErrorHandling() {
    // Handle form submissions
    document.addEventListener('submit', function(event) {
        const form = event.target;
        if (form.hasAttribute('data-confirm')) {
            if (!confirm(form.getAttribute('data-confirm'))) {
                event.preventDefault();
            }
        }
    });
    
    // Handle button clicks
    document.addEventListener('click', function(event) {
        const button = event.target.closest('button');
        if (button && button.hasAttribute('data-action')) {
            try {
                const action = button.getAttribute('data-action');
                if (typeof window[action] === 'function') {
                    window[action]();
                }
            } catch (error) {
                console.error('Button action error:', error);
                showNotification('Failed to perform action', 'error');
            }
        }
    });
}

function initializeDashboard() {
    // Initial stats update
    updateStats();
    
    // Set up periodic updates
    setInterval(updateStats, CONFIG.REFRESH_INTERVAL);
    
    // Update server time
    setInterval(() => {
        const serverTime = document.getElementById('serverTime');
        if (serverTime) {
            serverTime.textContent = new Date().toISOString().replace('T', ' ').substr(0, 19) + ' UTC';
        }
    }, 1000);
    
    // Initial logs refresh
    refreshLogs();
}

function setupCSRF() {
    const token = document.querySelector('meta[name="csrf-token"]')?.content;
    if (token) {
        document.querySelectorAll('form').forEach(form => {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = '_csrf';
            input.value = token;
            form.appendChild(input);
        });
    }
}