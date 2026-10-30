import { escapeHtml } from "./Html.Class.js";
import { ResultFieldSettings } from "./ResultFieldSettings.Class.js";

const PANEL_AREAS = Object.freeze([
    Object.freeze({ key: 'filters', label: 'Filters', glyph: '▼' }),
    Object.freeze({ key: 'columns', label: 'Columns', glyph: '⫴' }),
    Object.freeze({ key: 'rows', label: 'Rows', glyph: '≡' }),
    Object.freeze({ key: 'values', label: 'Values', glyph: 'Σ' })
]);

// Results field panel: edits a ResultLayoutState by dragging fields between areas.
export class ResultPanel {

    static get Areas() {
        return PANEL_AREAS;
    }

    constructor(selector, state, options = {}) {
        if (!window.jQuery || typeof window.jQuery.fn.sortable != 'function') {
            throw new Error('The Results field panel could not be loaded.');
        }
        this.selector = selector;
        this.state = state;
        this.options = options;
        this.deferred = false;
        this.pending = false;
        this.unsubscribe = null;
        this.lists = null;
        // Stored as fields so destroy() can detach them and a rebuilt panel cannot double-fire.
        this.onChangeEvent = event => this.handleChange(event);
        this.onClickEvent = event => this.handleClick(event);
        this.onContextMenuEvent = event => this.handleContextMenu(event);
        this.onKeyDownEvent = event => this.handleKeyDown(event);
        this.onDocumentClickEvent = event => {
            const command = event.target.closest('.result-panel-menu-command');
            if (command && !command.disabled) this.runMenuCommand(command.dataset.action);
            else if (!event.target.closest('.result-panel-menu')) this.closeMenu();
        };
        this.build();
    }

    root() {
        return document.querySelector(this.selector);
    }

    displayText(value) {
        return typeof this.options.plainText == 'function'
            ? this.options.plainText(value)
            : String(value == null ? '' : value);
    }

    // Draw the fixed shell once; refresh() fills the field list and the four areas.
    build() {
        const root = this.root();
        if (!root) return;
        root.classList.add('result-panel');
        root.innerHTML =
            '<div class="result-panel-section"><label class="result-panel-title">Choose fields to add to report:</label>' +
            '<div class="result-panel-fields"></div></div>' +
            '<div class="result-panel-section"><label class="result-panel-title">Drag fields between areas below:</label>' +
            '<div class="result-panel-layout">' + ResultPanel.Areas.map(area =>
                `<div class="result-panel-area" data-area="${area.key}">` +
                `<label class="result-panel-area-title"><span class="result-panel-glyph">${area.glyph}</span> ${area.label}</label>` +
                '<ul class="result-panel-list"></ul></div>').join('') +
            '</div></div>' +
            '<div class="result-panel-section result-panel-controls">' +
            '<label><input type="checkbox" class="result-panel-defer"> Defer Updates</label>' +
            '<button type="button" class="btn btn-default btn-sm result-panel-update" disabled>Update</button>' +
            '</div>';

        root.addEventListener('change', this.onChangeEvent);
        root.addEventListener('click', this.onClickEvent);
        root.addEventListener('contextmenu', this.onContextMenuEvent);
        root.addEventListener('keydown', this.onKeyDownEvent);
        document.addEventListener('click', this.onDocumentClickEvent);
        this.bindSortables();
        this.unsubscribe = this.state.onChange(() => this.stateChanged());
        this.refresh();
    }

    handleChange(event) {
        const box = event.target.closest('.result-panel-field input[type="checkbox"]');
        if (box) return this.toggleField(box.value, box.checked);
        const defer = event.target.closest('.result-panel-defer');
        if (defer) this.setDeferred(defer.checked);
    }

    handleClick(event) {
        if (event.target.closest('.result-panel-update')) this.apply();
    }

    handleContextMenu(event) {
        const chip = event.target.closest('.result-panel-chip');
        if (!chip) return;
        event.preventDefault();
        this.openMenu(chip.dataset.field, event.clientX, event.clientY);
    }

    handleKeyDown(event) {
        const chip = event.target.closest('.result-panel-chip');
        if (!chip || !(event.key == 'ContextMenu' || (event.shiftKey && event.key == 'F10'))) return;
        event.preventDefault();
        const bounds = chip.getBoundingClientRect();
        this.openMenu(chip.dataset.field, bounds.left + 12, bounds.bottom);
    }

    // Show the former PivotPanel commands without keeping controls on every field row.
    openMenu(field, x, y) {
        this.closeMenu();
        const areas = this.state.getAreas();
        const area = ResultPanel.Areas.find(item => areas[item.key].includes(field));
        const index = area ? areas[area.key].indexOf(field) : -1;
        const disabled = value => value ? ' disabled' : '';
        const command = (action, icon, label, isDisabled = false) =>
            `<button type="button" class="result-panel-menu-command" data-action="${action}"${disabled(isDisabled)}>` +
            `<i class="fa ${icon}"></i>${label}</button>`;
        const menu = document.createElement('div');
        menu.className = 'result-panel-menu';
        menu.innerHTML =
            command('up', 'fa-angle-up', 'Move Up', !area || index == 0) +
            command('down', 'fa-angle-down', 'Move Down', !area || index == areas[area.key].length - 1) +
            command('first', 'fa-angle-double-up', 'Move to Beginning', !area || index == 0) +
            command('last', 'fa-angle-double-down', 'Move to End', !area || index == areas[area.key].length - 1) +
            '<div class="result-panel-menu-separator"></div>' +
            command('area:filters', 'fa-filter', 'Move to Report Filter', area && area.key == 'filters') +
            command('area:rows', 'fa-bars', 'Move to Row Labels', area && area.key == 'rows') +
            command('area:columns', 'fa-columns', 'Move to Column Labels', area && area.key == 'columns') +
            command('area:values', 'fa-bar-chart-o', 'Move to Values', area && area.key == 'values') +
            '<div class="result-panel-menu-separator"></div>' +
            command('remove', 'fa-times', 'Remove Field') +
            '<div class="result-panel-menu-separator"></div>' +
            command('settings', 'fa-cog', 'Field Settings&hellip;');
        document.body.appendChild(menu);
        this.menu = menu;
        this.menuField = field;
        const bounds = menu.getBoundingClientRect();
        menu.style.left = `${Math.max(4, Math.min(x, window.innerWidth - bounds.width - 4))}px`;
        menu.style.top = `${Math.max(4, Math.min(y, window.innerHeight - bounds.height - 4))}px`;
    }

    runMenuCommand(action) {
        const field = this.menuField;
        const areas = this.state.getAreas();
        const area = ResultPanel.Areas.find(item => areas[item.key].includes(field));
        const index = area ? areas[area.key].indexOf(field) : -1;
        this.closeMenu();
        if (action == 'settings') return this.openSettings(field);
        if (action == 'remove') return this.state.assignField(field, null);
        if (action.startsWith('area:')) return this.state.assignField(field, action.slice(5));
        if (!area) return;
        if (action == 'up') return this.state.assignField(field, area.key, index - 1);
        if (action == 'down') return this.state.assignField(field, area.key, index + 1);
        if (action == 'first') return this.state.assignField(field, area.key, 0);
        if (action == 'last') return this.state.assignField(field, area.key, areas[area.key].length);
    }

    closeMenu() {
        if (this.menu) this.menu.remove();
        this.menu = null;
        this.menuField = null;
    }

    openSettings(field) {
        ResultFieldSettings.open(field, this.state, {
            fieldValues: this.options.fieldValues,
            plainText: this.options.plainText,
            currency: this.options.currency
        });
    }

    // Let every area accept chips dragged from the other three.
    bindSortables() {
        const lists = window.jQuery(`${this.selector} .result-panel-list`);
        lists.sortable({
            connectWith: `${this.selector} .result-panel-list`,
            placeholder: 'result-panel-placeholder',
            forcePlaceholderSize: true,
            tolerance: 'pointer',
            cursor: 'move',
            // update fires once per affected list, so a transfer would sync twice; stop fires once.
            stop: () => this.syncFromDom()
        });
        this.lists = lists;
    }

    // Read the dropped layout out of all four lists and apply it as one batched change.
    syncFromDom() {
        const root = this.root();
        if (!root) return;
        const dropped = {};
        ResultPanel.Areas.forEach(area => {
            const list = root.querySelector(`.result-panel-area[data-area="${area.key}"] .result-panel-list`);
            dropped[area.key] = Array.from(list.querySelectorAll('.result-panel-chip')).map(chip => chip.dataset.field);
        });
        // stop also fires when a drag is cancelled or dropped back, which must not force a redraw.
        const current = this.state.getAreas();
        const moved = ResultPanel.Areas.some(area => dropped[area.key].length != current[area.key].length ||
            dropped[area.key].some((field, index) => field != current[area.key][index]));
        if (!moved) return;
        this.state.defer(state => {
            ResultPanel.Areas.forEach(area => {
                dropped[area.key].forEach((field, index) => state.assignField(field, area.key, index));
            });
        });
    }

    // Ticking a field drops it into the area its catalogue entry belongs to, as the Wijmo panel did.
    toggleField(field, checked) {
        if (!checked) return this.state.assignField(field, null);
        const entry = this.state.fields.find(item => item.field == field);
        this.state.assignField(field, entry && entry.isMeasure ? 'values' : 'rows');
    }

    setDeferred(deferred) {
        this.deferred = deferred;
        if (!deferred && this.pending) this.apply();
        else this.updateControls();
    }

    // Repaint on every state change, then notify immediately or hold until Update is pressed.
    stateChanged() {
        this.refresh();
        if (this.deferred) {
            this.pending = true;
            this.updateControls();
            return;
        }
        this.apply();
    }

    // The one signal callers redraw on, so deferring here defers the grid and chart with it.
    apply() {
        this.pending = false;
        this.updateControls();
        if (typeof this.options.onApply == 'function') this.options.onApply(this.state);
    }

    updateControls() {
        const button = this.root() && this.root().querySelector('.result-panel-update');
        if (button) button.disabled = !this.deferred || !this.pending;
    }

    // Rebuild the field checkboxes and area chips to match the current state.
    refresh() {
        const root = this.root();
        if (!root) return;
        this.closeMenu();
        const areas = this.state.getAreas();
        const placed = new Set(Object.keys(areas).reduce((all, key) => all.concat(areas[key]), []));
        root.querySelector('.result-panel-fields').innerHTML = this.state.fields.map(field => {
            const filtered = this.state.filters[field.field] || this.state.conditionFilters[field.field];
            const indicator = filtered ? '<i class="fa fa-filter result-panel-filter" title="Filter applied"></i>' : '';
            return '<label class="result-panel-field">' +
            `<input type="checkbox" value="${escapeHtml(field.field)}"${placed.has(field.field) ? ' checked' : ''}> ` +
            `${indicator}<span>${escapeHtml(this.displayText(field.header))}</span></label>`;
        }).join('');

        ResultPanel.Areas.forEach(area => {
            const list = root.querySelector(`.result-panel-area[data-area="${area.key}"] .result-panel-list`);
            list.innerHTML = areas[area.key].map(name => this.chip(name, area.key)).join('');
        });
    }

    // Value fields show the summary calculation currently stored in the layout.
    chip(field, area) {
        const entry = this.state.fields.find(item => item.field == field);
        const header = this.displayText(entry ? entry.header : field);
        const settings = this.state.getFieldSettings(field);
        const aggregation = settings ? settings.aggregation : 'sum';
        const summary = aggregation.replace(/([a-z])([A-Z])/g, '$1 $2');
        const suffix = area == 'values' ? ` (${summary.charAt(0).toUpperCase()}${summary.slice(1)})` : '';
        const filtered = this.state.filters[field] || this.state.conditionFilters[field];
        const indicator = filtered ? '<i class="fa fa-filter result-panel-filter" title="Filter applied"></i>' : '';
        const label = indicator + escapeHtml(header) + escapeHtml(suffix);
        return `<li class="result-panel-chip" data-field="${escapeHtml(field)}" tabindex="0" title="Right-click for field commands">` +
            `<span class="result-panel-chip-label">${label}</span></li>`;
    }

    destroy() {
        ResultFieldSettings.destroy();
        if (this.unsubscribe) this.unsubscribe();
        this.unsubscribe = null;
        const root = this.root();
        if (root) {
            root.removeEventListener('change', this.onChangeEvent);
            root.removeEventListener('click', this.onClickEvent);
            root.removeEventListener('contextmenu', this.onContextMenuEvent);
            root.removeEventListener('keydown', this.onKeyDownEvent);
        }
        document.removeEventListener('click', this.onDocumentClickEvent);
        this.closeMenu();
        if (this.lists) {
            // jQuery UI keeps the widget under this data key and calling destroy without one throws.
            this.lists.filter((index, list) => !!window.jQuery.data(list, 'ui-sortable')).sortable('destroy');
            this.lists = null;
        }
        if (root) {
            root.innerHTML = '';
            root.classList.remove('result-panel');
        }
    }
}
