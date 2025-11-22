/**
 * Table Component
 * 
 * Data table with sorting, filtering, and sticky headers.
 */

import { escapeHtml } from './utils.js';

export class Table {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.columns = options.columns || [];
        this.data = options.data || [];
        this.sortColumn = null;
        this.sortDirection = 'asc';
        this.instanceId = 'table_' + Math.random().toString(36).substr(2, 9);
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
            <th data-sort-column="${col.key}" data-table-instance="${this.instanceId}" style="cursor: pointer;">
                ${col.label}
                ${this.sortColumn === col.key ? (this.sortDirection === 'asc' ? '↑' : '↓') : ''}
            </th>
        `).join('');
        
        const rows = this.data.length > 0
            ? this.data.map(row => `
                <tr>
                    ${this.columns.map(col => `<td>${col.render ? col.render(row[col.key], row) : escapeHtml(row[col.key])}</td>`).join('')}
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
        
        // Add click listeners for sorting
        this.container.querySelectorAll(`th[data-table-instance="${this.instanceId}"]`).forEach(th => {
            th.addEventListener('click', () => {
                this.sort(th.dataset.sortColumn);
            });
        });
    }
}
