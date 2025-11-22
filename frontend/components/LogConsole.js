/**
 * Log Console Component
 * 
 * Terminal-like log viewer with color-coded output.
 */

import { escapeHtml, downloadFile } from './utils.js';

export class LogConsole {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.autoScroll = options.autoScroll !== false;
        this.maxLines = options.maxLines || 1000;
        this.logs = [];
    }
    
    addLog(log) {
        this.logs.push(log);
        if (this.logs.length > this.maxLines) {
            this.logs.shift();
        }
        this.render();
    }
    
    addLogs(logs) {
        logs.forEach(log => {
            this.logs.push(log);
        });
        
        while (this.logs.length > this.maxLines) {
            this.logs.shift();
        }
        
        this.render();
    }
    
    clear() {
        this.logs = [];
        this.render();
    }
    
    setAutoScroll(enabled) {
        this.autoScroll = enabled;
    }
    
    jumpToLatest() {
        if (this.container) {
            this.container.scrollTop = this.container.scrollHeight;
        }
    }
    
    render() {
        if (!this.container) return;
        
        if (this.logs.length === 0) {
            this.container.innerHTML = '<div class="log-line info">Waiting for logs...</div>';
            return;
        }
        
        this.container.innerHTML = this.logs.map(log => {
            const time = log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : '';
            const level = (log.level || 'info').toLowerCase();
            const message = escapeHtml(log.message || log);
            
            return `<div class="log-line ${level}">${time ? `[${time}] ` : ''}${message}</div>`;
        }).join('');
        
        if (this.autoScroll) {
            this.jumpToLatest();
        }
    }
    
    download() {
        const content = this.logs.map(log => {
            const time = log.timestamp ? new Date(log.timestamp).toISOString() : '';
            const level = log.level || 'INFO';
            const message = log.message || log;
            return `${time} [${level}] ${message}`;
        }).join('\n');
        
        downloadFile(content, `logs-${new Date().toISOString()}.txt`, 'text/plain');
    }
}
