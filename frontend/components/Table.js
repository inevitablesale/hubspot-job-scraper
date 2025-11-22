/**
 * Table Component
 * 
 * Data table with sorting, filtering, and sticky headers.
 */

export class Table {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.columns = options.columns || [];
        this.data = options.data || [];
        this.sortColumn = null;
        this.sortDirection = 'asc';
    }
    
    setData(data) {
        this.data = data;
        this.render();
    }
    
    sort(column) {
        if (this.sortColumn === column) {
            this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortColumn = column;
            this.sortDirection = 'asc';
        }
        
        this.data.sort((a, b) => {
            const aVal = a[column];
            const bVal = b[column];
            const modifier = this.sortDirection === 'asc' ? 1 : -1;
            
            if (aVal < bVal) return -1 * modifier;
            if (aVal > bVal) return 1 * modifier;
            return 0;
        });
        
        this.render();
    }
    
    render() {
        if (!this.container) return;
        
        const headers = this.columns.map(col => `
            <th onclick="table.sort('${col.key}')" style="cursor: pointer;">
                ${col.label}
                ${this.sortColumn === col.key ? (this.sortDirection === 'asc' ? '↑' : '↓') : ''}
            </th>
        `).join('');
        
        const rows = this.data.length > 0
            ? this.data.map(row => `
                <tr>
                    ${this.columns.map(col => `<td>${col.render ? col.render(row[col.key], row) : this.escape(row[col.key])}</td>`).join('')}
                </tr>
            `).join('')
            : `<tr><td colspan="${this.columns.length}" style="text-align: center; color: var(--text-secondary-dark);">No data available</td></tr>`;
        
        this.container.innerHTML = `
            <table>
                <thead>
                    <tr>${headers}</tr>
                </thead>
                <tbody>
                    ${rows}
                </tbody>
            </table>
        `;
    }
    
    escape(text) {
        if (text === null || text === undefined) return '—';
        const div = document.createElement('div');
        div.textContent = String(text);
        return div.innerHTML;
    }
}
