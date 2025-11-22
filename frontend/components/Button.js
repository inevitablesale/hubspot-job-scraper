/**
 * Button Component
 * 
 * Buttons with variants: primary, secondary, danger
 */

export class Button {
    static render(text, variant = 'primary', icon = null, options = {}) {
        const iconHtml = icon ? `<i data-lucide="${icon}"></i>` : '';
        const disabled = options.disabled ? 'disabled' : '';
        const onClick = options.onClick || '';
        const id = options.id || '';
        
        return `
            <button 
                class="btn btn-${variant}" 
                ${disabled} 
                ${id ? `id="${id}"` : ''}
                ${onClick ? `onclick="${onClick}"` : ''}
            >
                ${iconHtml}
                <span>${text}</span>
            </button>
        `;
    }
    
    static primary(text, icon = null, options = {}) {
        return this.render(text, 'primary', icon, options);
    }
    
    static secondary(text, icon = null, options = {}) {
        return this.render(text, 'secondary', icon, options);
    }
    
    static danger(text, icon = null, options = {}) {
        return this.render(text, 'danger', icon, options);
    }
}
