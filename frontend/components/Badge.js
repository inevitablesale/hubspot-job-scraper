/**
 * Badge Component
 * 
 * Small pill-shaped badges with color variants.
 * Supports: gray, green, yellow, red, blue
 */

export class Badge {
    static render(text, variant = 'gray', icon = null) {
        const iconHtml = icon ? `<i data-lucide="${icon}"></i>` : '';
        return `
            <span class="badge badge-${variant}">
                ${iconHtml}
                <span>${text}</span>
            </span>
        `;
    }
    
    static status(state) {
        const variants = {
            'idle': { color: 'gray', icon: 'circle' },
            'running': { color: 'green', icon: 'activity' },
            'completed': { color: 'blue', icon: 'check-circle' },
            'error': { color: 'red', icon: 'alert-circle' }
        };
        
        const config = variants[state] || variants.idle;
        return this.render(state.charAt(0).toUpperCase() + state.slice(1), config.color, config.icon);
    }
}
