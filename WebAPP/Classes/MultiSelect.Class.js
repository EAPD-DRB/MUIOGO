import { escapeHtml } from "./Html.Class.js";

// Checkbox dropdown with a search box and a select-all, checked state held on each item as $checked.
export class MultiSelect {

    constructor(selector, options = {}) {
        this.host = typeof selector == 'string' ? document.querySelector(selector) : selector;
        if (!this.host) throw new Error(`MultiSelect host not found: ${selector}`);
        this.placeholder = options.placeholder || 'Select';
        this.headerFormat = options.headerFormat || '{count} selected';
        this.displayMemberPath = options.displayMemberPath || 'text';
        this.showSelectAllCheckbox = options.showSelectAllCheckbox !== false;
        this.showFilterInput = options.showFilterInput !== false;
        this.checkedItemsChanged = options.checkedItemsChanged || null;
        this.items = [];
        this.search = '';
        this.build();
        this.itemsSource = options.itemsSource || [];
    }

    build() {
        this.host.classList.add('muio-multiselect');
        this.host.innerHTML =
            '<button type="button" class="muio-multiselect-toggle" aria-haspopup="true" aria-expanded="false"></button>' +
            '<div class="muio-multiselect-panel" hidden>' +
            (this.showFilterInput
                ? '<input type="search" class="muio-multiselect-search" placeholder="Search">' : '') +
            (this.showSelectAllCheckbox
                ? '<label class="muio-multiselect-all"><input type="checkbox"><span>Select All</span></label>' : '') +
            '<div class="muio-multiselect-list"></div></div>';
        this.toggle = this.host.querySelector('.muio-multiselect-toggle');
        this.panel = this.host.querySelector('.muio-multiselect-panel');
        this.list = this.host.querySelector('.muio-multiselect-list');
        this.searchBox = this.host.querySelector('.muio-multiselect-search');
        this.allBox = this.host.querySelector('.muio-multiselect-all input');

        this.onToggle = () => this.setOpen(this.panel.hidden);
        this.onListChange = event => {
            const box = event.target.closest('input[type=checkbox]');
            if (!box) return;
            // Rows are indexed against the filtered view, not the whole source.
            const item = this.rows[Number(box.dataset.index)];
            if (!item) return;
            item.$checked = box.checked;
            // Only the header and the select-all state change, so the rows are left alone.
            this.refreshSelectAll();
            this.refreshHeader();
            this.notify();
        };
        // Narrowing the visible rows must never change what is checked.
        this.onSearch = () => {
            this.search = this.searchBox.value.trim().toLowerCase();
            this.renderList();
        };
        // Select All ticks the rows in view; clearing it drops every check, as Wijmo did.
        this.onSelectAll = () => {
            const visible = new Set(this.visibleItems());
            const checked = this.allBox.checked;
            this.items.forEach(item => { item.$checked = checked && visible.has(item); });
            this.renderList();
            this.refreshHeader();
            this.notify();
        };
        this.onOutside = event => {
            if (!this.panel.hidden && !this.host.contains(event.target)) this.setOpen(false);
        };
        this.onKey = event => {
            if (event.key == 'Escape' && !this.panel.hidden) {
                this.setOpen(false);
                this.toggle.focus();
            }
        };

        this.toggle.addEventListener('click', this.onToggle);
        this.list.addEventListener('change', this.onListChange);
        if (this.searchBox) this.searchBox.addEventListener('input', this.onSearch);
        if (this.allBox) this.allBox.addEventListener('change', this.onSelectAll);
        document.addEventListener('mousedown', this.onOutside);
        this.host.addEventListener('keydown', this.onKey);
    }

    get itemsSource() {
        return this.items;
    }

    // Reassigning the source redraws from each item's own `$checked`, so callers can set the selection.
    set itemsSource(items) {
        this.items = Array.isArray(items) ? items : [];
        this.search = '';
        if (this.searchBox) this.searchBox.value = '';
        this.renderList();
        this.refreshHeader();
    }

    get checkedItems() {
        return this.items.filter(item => item.$checked === true);
    }

    visibleItems() {
        if (!this.search) return this.items;
        return this.items.filter(item =>
            String(item[this.displayMemberPath] ?? '').toLowerCase().includes(this.search));
    }

    // One pass over the visible rows: build the markup and count the checks for the select-all.
    renderList() {
        const visible = this.visibleItems();
        const rows = [];
        let checked = 0;
        visible.forEach((item, index) => {
            if (item.$checked === true) checked++;
            const label = escapeHtml(String(item[this.displayMemberPath] ?? ''));
            rows.push(`<label class="muio-multiselect-item"><input type="checkbox" data-index="${index}"` +
                `${item.$checked ? ' checked' : ''}><span>${label}</span></label>`);
        });
        this.list.innerHTML = rows.length ? rows.join('') : '<p class="muio-multiselect-empty">No matching items.</p>';
        this.rows = visible;
        this.setSelectAll(visible.length, checked);
    }

    // Ticked when every visible row is checked, indeterminate while only some are.
    refreshSelectAll() {
        const visible = this.rows || [];
        this.setSelectAll(visible.length, visible.filter(item => item.$checked === true).length);
    }

    setSelectAll(total, checked) {
        if (!this.allBox) return;
        this.allBox.disabled = total === 0;
        this.allBox.checked = total > 0 && checked === total;
        this.allBox.indeterminate = checked > 0 && checked < total;
    }

    refreshHeader() {
        const count = this.checkedItems.length;
        this.toggle.textContent = count
            ? this.headerFormat.replace(/\{count(:[^}]*)?\}/, String(count))
            : this.placeholder;
    }

    notify() {
        if (this.checkedItemsChanged) this.checkedItemsChanged(this);
    }

    setOpen(open) {
        this.panel.hidden = !open;
        this.toggle.setAttribute('aria-expanded', String(open));
        if (open && this.searchBox) this.searchBox.focus();
    }

    destroy() {
        this.toggle.removeEventListener('click', this.onToggle);
        this.list.removeEventListener('change', this.onListChange);
        if (this.searchBox) this.searchBox.removeEventListener('input', this.onSearch);
        if (this.allBox) this.allBox.removeEventListener('change', this.onSelectAll);
        document.removeEventListener('mousedown', this.onOutside);
        this.host.removeEventListener('keydown', this.onKey);
        this.host.classList.remove('muio-multiselect');
        this.host.innerHTML = '';
        this.items = [];
        this.rows = [];
    }
}
