/**
 * Timeline Component
 * 
 * Vertical timeline for displaying crawl events.
 */

export class Timeline {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.events = [];
    }
    
    addEvent(event) {
        this.events.push(event);
        this.render();
    }
    
    clear() {
        this.events = [];
        this.render();
    }
    
    render() {
        if (!this.container) return;
        
        if (this.events.length === 0) {
            this.container.innerHTML = `
                <div class="timeline-item">
                    <div class="timeline-dot"></div>
                    <div class="timeline-content">
                        <div class="timeline-domain">Waiting for crawl...</div>
                        <span class="badge badge-gray">Idle</span>
                    </div>
                </div>
            `;
            return;
        }
        
        this.container.innerHTML = this.events.map(event => `
            <div class="timeline-item">
                <div class="timeline-dot"></div>
                <div class="timeline-content">
                    <div class="timeline-domain">${this.escape(event.domain)}</div>
                    <span class="badge badge-${event.statusColor || 'gray'}">${event.status}</span>
                    ${event.note ? `<div class="timeline-note">${this.escape(event.note)}</div>` : ''}
                    ${event.timestamp ? `<div class="timeline-note">${new Date(event.timestamp).toLocaleTimeString()}</div>` : ''}
                </div>
            </div>
        `).join('');
    }
    
    escape(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
