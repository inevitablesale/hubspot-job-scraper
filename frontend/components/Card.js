/**
 * Card Component
 * 
 * Reusable card component following the design system.
 * Variants: default, stat, hero
 */

export class Card {
    constructor(options = {}) {
        this.variant = options.variant || 'default';
        this.className = options.className || '';
        this.shadow = options.shadow !== false;
    }
    
    render(content) {
        const classes = ['card'];
        
        if (this.variant === 'stat') {
            classes.push('stat-card');
        } else if (this.variant === 'hero') {
            classes.push('hero-card');
        }
        
        if (this.className) {
            classes.push(this.className);
        }
        
        return `<div class="${classes.join(' ')}">${content}</div>`;
    }
    
    static stat(label, value, variant = 'default') {
        const colorClass = variant === 'error' ? 'style="color: var(--error);"' : '';
        return `
            <div class="stat-card">
                <div class="stat-label">${label}</div>
                <div class="stat-value" ${colorClass}>${value}</div>
            </div>
        `;
    }
}
