/**
 * Shared Utilities
 * 
 * Common utility functions used across components.
 */

/**
 * Escape HTML to prevent XSS attacks
 * @param {string} text - Text to escape
 * @returns {string} Escaped HTML
 */
export function escapeHtml(text) {
    if (text === null || text === undefined) return '—';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

/**
 * Validate URL
 * @param {string} url - URL to validate
 * @returns {boolean} True if valid HTTP(S) URL
 */
export function isValidUrl(url) {
    try {
        const parsed = new URL(url);
        return parsed.protocol === 'http:' || parsed.protocol === 'https:';
    } catch {
        return false;
    }
}

/**
 * Format date for display
 * @param {string|Date} date - Date to format
 * @returns {string} Formatted date string
 */
export function formatDate(date) {
    if (!date) return '—';
    const d = typeof date === 'string' ? new Date(date) : date;
    return d.toLocaleString();
}

/**
 * Format timestamp for display
 * @param {string|Date} timestamp - Timestamp to format
 * @returns {string} Formatted time string
 */
export function formatTime(timestamp) {
    if (!timestamp) return '—';
    const d = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
    return d.toLocaleTimeString();
}

/**
 * Debounce function
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
export function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Throttle function
 * @param {Function} func - Function to throttle
 * @param {number} limit - Time limit in milliseconds
 * @returns {Function} Throttled function
 */
export function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Download text as file
 * @param {string} content - File content
 * @param {string} filename - Filename
 * @param {string} type - MIME type
 */
export function downloadFile(content, filename, type = 'text/plain') {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

/**
 * Copy text to clipboard
 * @param {string} text - Text to copy
 * @returns {Promise<boolean>} Success status
 */
export async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        return true;
    } catch {
        return false;
    }
}

/**
 * Get status color variant
 * @param {string} status - Status value
 * @returns {string} Color variant (gray, green, yellow, red, blue)
 */
export function getStatusColor(status) {
    const statusLower = (status || '').toLowerCase();
    
    if (statusLower.includes('running') || statusLower.includes('active')) {
        return 'green';
    }
    if (statusLower.includes('error') || statusLower.includes('failed')) {
        return 'red';
    }
    if (statusLower.includes('warning') || statusLower.includes('pending')) {
        return 'yellow';
    }
    if (statusLower.includes('completed') || statusLower.includes('success')) {
        return 'blue';
    }
    return 'gray';
}
