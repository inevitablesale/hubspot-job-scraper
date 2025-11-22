/**
 * Log Console Component
 * 
 * Terminal-like log viewer with color-coded output.
 */

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
            const message = this.escape(log.message || log);
            
            return `<div class="log-line ${level}">${time ? `[${time}] ` : ''}${message}</div>`;
        }).join('');
        
        if (this.autoScroll) {
            this.jumpToLatest();
        }
    }
    
    escape(text) {
        const div = document.createElement('div');
        div.textContent = String(text);
        return div.innerHTML;
    }
    
    download() {
        const content = this.logs.map(log => {
            const time = log.timestamp ? new Date(log.timestamp).toISOString() : '';
            const level = log.level || 'INFO';
            const message = log.message || log;
            return `${time} [${level}] ${message}`;
        }).join('\n');
        
        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `logs-${new Date().toISOString()}.txt`;
        a.click();
        URL.revokeObjectURL(url);
    }
}
