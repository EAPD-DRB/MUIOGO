import { escapeHtml } from "./Html.Class.js";
import { ResultAggregator } from "./ResultAggregator.Class.js";

const AGGREGATIONS = Object.freeze([
    ['sum','Sum'], ['count','Count'], ['average','Average'], ['max','Max'], ['min','Min'],
    ['range','Range'], ['std','Std'], ['variance','Variance'], ['stdPopulation','Std Population'],
    ['variancePopulation','Variance Population'], ['first','First'], ['last','Last']
]);
const SHOW_AS = Object.freeze([
    ['none','No calculation'], ['differenceRow','Difference from previous row'],
    ['differenceRowPercent','% difference from previous row'], ['differenceColumn','Difference from previous column'],
    ['differenceColumnPercent','% difference from previous column'], ['percentGrand','% of grand total'],
    ['percentRow','% of row total'], ['percentColumn','% of column total'], ['runningTotal','Running total'],
    ['runningTotalPercent','% running total'], ['percentPreviousRow','% of previous row'],
    ['percentPreviousColumn','% of previous column']
]);
const NUMBER_FORMATS = Object.freeze([
    ['n0','Integer (n0)'], ['n2','Float (n2)'], ['n3','Float (n3)'], ['n4','Float (n4)'],
    ['c','Currency (c)'], ['p0','Percentage (p0)'], ['p2','Percentage (p2)'],
    ['n2,','Thousands (n2,)'], ['n2,,','Millions (n2,,)'], ['n2,,,','Billions (n2,,,)']
]);
const FILTER_OPERATORS = Object.freeze([
    ['equals','Equals'], ['notEquals','Does not equal'], ['greaterThan','Greater than'],
    ['greaterThanOrEqual','Greater than or equal'], ['lessThan','Less than'], ['lessThanOrEqual','Less than or equal'],
    ['beginsWith','Begins with'], ['notBeginsWith','Does not begin with'], ['endsWith','Ends with'],
    ['notEndsWith','Does not end with'], ['contains','Contains'], ['notContains','Does not contain']
]);

// One dialog element is reused for every field so repeated opens cannot accumulate listeners.
let sharedDialog = null;
let activeEditor = null;

const handlers = {
    input: event => activeEditor && activeEditor.handleInput(event),
    change: event => activeEditor && activeEditor.handleChange(event),
    click: event => activeEditor && activeEditor.handleClick(event),
    hidden: () => { activeEditor = null; }
};

function dialogElement() {
    if (sharedDialog) return sharedDialog;
    const dialog = document.createElement('div');
    dialog.className = 'modal fade result-field-settings';
    dialog.tabIndex = -1;
    dialog.setAttribute('role', 'dialog');
    dialog.innerHTML =
        '<div class="modal-dialog" role="document"><div class="modal-content">' +
        '<div class="modal-header"><h4 class="modal-title"></h4></div>' +
        '<div class="modal-body">' +
        '<div class="result-field-row"><label for="resultFieldHeader">Header:</label>' +
        '<input id="resultFieldHeader" class="form-control result-field-header" type="text"></div>' +
        '<div class="result-field-row"><label for="resultFieldSummary">Summary:</label>' +
        `<select id="resultFieldSummary" class="form-control result-field-summary">${AGGREGATIONS.map(option =>
            `<option value="${option[0]}">${option[1]}</option>`).join('')}</select></div>` +
        '<div class="result-field-row"><label for="resultFieldShowAs">Show As:</label>' +
        `<select id="resultFieldShowAs" class="form-control result-field-show-as">${SHOW_AS.map(option =>
            `<option value="${option[0]}">${option[1]}</option>`).join('')}</select></div>` +
        '<div class="result-field-row"><label for="resultFieldWeight">Weigh by:</label>' +
        '<select id="resultFieldWeight" class="form-control result-field-weight"></select></div>' +
        '<div class="result-field-row result-field-sort-section"><label for="resultFieldSort">Sort:</label>' +
        '<select id="resultFieldSort" class="form-control result-field-sort"><option value="asc">Ascending</option>' +
        '<option value="desc">Descending</option></select></div>' +
        '<div class="result-field-row"><label>Filter:</label><div class="result-field-filter-actions">' +
        '<button type="button" class="btn btn-default result-field-edit">Edit&hellip;</button>' +
        '<button type="button" class="btn btn-default result-field-clear">Clear</button></div></div>' +
        '<div class="result-field-filter-editor" hidden>' +
        '<div class="result-field-filter-tabs"><button type="button" data-mode="condition">Filter by Condition</button>' +
        '<span> | </span><button type="button" data-mode="value">Filter by Value</button></div>' +
        '<input class="result-field-filter-mode" type="hidden" value="value">' +
        '<div class="result-field-value-filter">' +
        '<label class="sr-only" for="resultFieldSearch">Search filter values</label>' +
        '<input id="resultFieldSearch" type="text" class="form-control result-field-search" placeholder="Search values">' +
        '<div class="result-field-actions"><label class="result-field-select-all">' +
        '<input type="checkbox" class="result-field-all"> Select All</label>' +
        '<span class="result-field-count"></span></div>' +
        '<div class="result-field-values"></div>' +
        '<p class="result-field-hint">Select at least one value to apply.</p></div>' +
        '<div class="result-field-condition-filter" hidden>' +
        [0, 1].map(index => '<div class="result-field-condition">' +
            `<select class="form-control result-field-condition-operator" data-index="${index}"><option value="">(none)</option>` +
            FILTER_OPERATORS.map(option => `<option value="${option[0]}">${option[1]}</option>`).join('') + '</select>' +
            `<input class="form-control result-field-condition-value" data-index="${index}" type="text"></div>`).join('') +
        '<div class="result-field-condition-join"><label><input type="radio" name="resultConditionJoin" value="and" checked> And</label>' +
        '<label><input type="radio" name="resultConditionJoin" value="or"> Or</label></div></div>' +
        '<div class="result-field-filter-footer"><button type="button" class="btn btn-default btn-sm result-field-filter-ok">OK</button></div></div>' +
        '<div class="result-field-row result-field-format-section"><label for="resultFieldFormat">Format:</label>' +
        `<select id="resultFieldFormat" class="form-control result-field-format">${NUMBER_FORMATS.map(option =>
            `<option value="${option[0]}">${option[1]}</option>`).join('')}</select></div>` +
        '<div class="result-field-row result-field-sample-row"><label>Sample:</label>' +
        '<input class="form-control result-field-sample" type="text" readonly></div>' +
        '</div><div class="modal-footer">' +
        '<button type="button" class="btn btn-default" data-dismiss="modal">Cancel</button>' +
        '<button type="button" class="btn btn-default result-field-apply">OK</button>' +
        '</div></div></div>';
    document.body.appendChild(dialog);
    dialog.addEventListener('input', handlers.input);
    dialog.addEventListener('change', handlers.change);
    dialog.addEventListener('click', handlers.click);
    if (window.jQuery) window.jQuery(dialog).on('hidden.bs.modal', handlers.hidden);
    sharedDialog = dialog;
    return dialog;
}

// Field settings dialog: sort direction, filter values and measure number format.
export class ResultFieldSettings {

    // Open the dialog for one field. Nothing is written to the state until Apply.
    static open(field, state, options = {}) {
        const entry = state.fields.find(item => item.field == field);
        if (!entry) return null;
        activeEditor = new ResultFieldSettings(entry, state, options);
        activeEditor.show();
        return activeEditor;
    }

    // Drop the shared dialog and its listeners, for callers tearing the Results page down.
    static destroy() {
        if (!sharedDialog) return;
        if (window.jQuery && typeof window.jQuery(sharedDialog).modal == 'function') {
            window.jQuery(sharedDialog).removeClass('fade').modal('hide');
        }
        sharedDialog.removeEventListener('input', handlers.input);
        sharedDialog.removeEventListener('change', handlers.change);
        sharedDialog.removeEventListener('click', handlers.click);
        if (window.jQuery) window.jQuery(sharedDialog).off('hidden.bs.modal', handlers.hidden);
        sharedDialog.remove();
        sharedDialog = null;
        activeEditor = null;
    }

    constructor(entry, state, options) {
        this.entry = entry;
        this.state = state;
        this.options = options;
        this.text = value => (typeof options.plainText == 'function' ? options.plainText(value) : String(value == null ? '' : value));
        // Raw values are kept against a stable identity so numbers and strings cannot collide.
        this.values = new Map();
        (typeof options.fieldValues == 'function' ? options.fieldValues(entry.field) || [] : [])
            .forEach(value => this.values.set(ResultAggregator.keyID([ResultAggregator.keyValue(value)]), value));
        const active = state.filters[entry.field];
        // No stored filter means every value is included, which is not the same as none selected.
        this.selected = new Set(active ? active.map(value => this.availableKey(value)).filter(key => key != null) : this.values.keys());
        this.descending = state.descending[entry.field] === true;
        this.fieldSettings = state.getFieldSettings(entry.field);
        this.condition = state.conditionFilters[entry.field]
            ? JSON.parse(JSON.stringify(state.conditionFilters[entry.field]))
            : { and: true, conditions: [] };
        this.search = '';
    }

    // Match legacy string values to one unambiguous raw value from the current model.
    availableKey(value) {
        const exact = ResultAggregator.keyID([ResultAggregator.keyValue(value)]);
        if (this.values.has(exact)) return exact;
        const matches = Array.from(this.values).filter(entry => String(entry[1]) == String(value));
        return matches.length == 1 ? matches[0][0] : null;
    }

    show() {
        const dialog = dialogElement();
        this.dialog = dialog;
        const field = this.state.fields.find(item => item.field == this.entry.field);
        dialog.querySelector('.modal-title').textContent = `Field settings: ${this.text(this.entry.header)}`;
        dialog.querySelector('.result-field-header').value = this.text(this.fieldSettings.header);
        dialog.querySelector('.result-field-header').setCustomValidity('');
        dialog.querySelector('.result-field-summary').innerHTML = AGGREGATIONS
            .filter(option => (field && field.isNumeric) || ['count', 'max', 'min', 'first', 'last'].includes(option[0]))
            .map(option => `<option value="${option[0]}">${option[1]}</option>`).join('');
        dialog.querySelector('.result-field-summary').value = this.fieldSettings.aggregation;
        dialog.querySelector('.result-field-show-as').value = this.fieldSettings.showAs;
        dialog.querySelector('.result-field-weight').innerHTML = '<option value="">(none)</option>' + this.state.fields
            .filter(field => field.field != this.entry.field && field.isNumeric)
            .map(field => `<option value="${escapeHtml(field.field)}">${escapeHtml(this.text(field.header))}</option>`).join('');
        dialog.querySelector('.result-field-weight').value = this.fieldSettings.weightField || '';
        dialog.querySelector('.result-field-sort').value = this.descending ? 'desc' : 'asc';
        dialog.querySelector('.result-field-format').value = this.fieldSettings.format || this.state.numberFormat;
        this.updateSample();
        dialog.querySelector('.result-field-search').value = '';
        dialog.querySelector('.result-field-filter-editor').hidden = true;
        dialog.querySelector('.result-field-filter-mode').value = this.condition.conditions.length ? 'condition' : 'value';
        dialog.querySelectorAll('.result-field-condition-operator').forEach(control => { control.value = ''; });
        dialog.querySelectorAll('.result-field-condition-value').forEach(control => { control.value = ''; });
        this.condition.conditions.forEach((condition, index) => {
            const operator = dialog.querySelector(`.result-field-condition-operator[data-index="${index}"]`);
            const value = dialog.querySelector(`.result-field-condition-value[data-index="${index}"]`);
            if (operator) operator.value = condition.operator;
            if (value) value.value = condition.value == null ? '' : condition.value;
        });
        dialog.querySelector(`input[name="resultConditionJoin"][value="${this.condition.and ? 'and' : 'or'}"]`).checked = true;
        this.updateFilterMode();
        dialog.querySelector('.result-field-clear').disabled = !this.state.filters[this.entry.field] && !this.state.conditionFilters[this.entry.field];
        this.renderValues();
        if (window.jQuery && typeof window.jQuery(dialog).modal == 'function') window.jQuery(dialog).modal('show');
        else dialog.style.display = 'block';
        return this;
    }

    handleInput(event) {
        if (!event.target.closest('.result-field-search')) return;
        this.search = event.target.value.trim().toLowerCase();
        this.renderValues();
    }

    handleChange(event) {
        if (event.target.closest('.result-field-format')) this.updateSample();
        if (event.target.closest('.result-field-show-as')) {
            const percentage = event.target.value.toLowerCase().includes('percent');
            const format = this.dialog.querySelector('.result-field-format');
            if (percentage && !format.value.startsWith('p')) format.value = 'p2';
            if (!percentage && format.value.startsWith('p')) format.value = 'n2';
            this.updateSample();
        }
        if (event.target.closest('.result-field-filter-mode')) this.updateFilterMode();
        if (event.target.closest('.result-field-all')) return this.setVisible(event.target.checked);
        const box = event.target.closest('.result-field-value input');
        // Searching only hides rows, so the checked set is edited here and nowhere else.
        if (!box) return;
        if (box.checked) this.selected.add(box.value);
        else this.selected.delete(box.value);
        this.renderCount();
    }

    handleClick(event) {
        const mode = event.target.closest('.result-field-filter-tabs button');
        if (mode) {
            this.dialog.querySelector('.result-field-filter-mode').value = mode.dataset.mode;
            this.updateFilterMode();
            return;
        }
        if (event.target.closest('.result-field-filter-ok')) {
            this.dialog.querySelector('.result-field-filter-editor').hidden = true;
            return;
        }
        if (event.target.closest('.result-field-edit')) {
            this.dialog.querySelector('.result-field-filter-editor').hidden = false;
            this.dialog.querySelector('.result-field-search').focus();
            return;
        }
        if (event.target.closest('.result-field-clear')) {
            this.selected = new Set(this.values.keys());
            this.condition = { and: true, conditions: [] };
            this.dialog.querySelectorAll('.result-field-condition-operator').forEach(control => { control.value = ''; });
            this.dialog.querySelectorAll('.result-field-condition-value').forEach(control => { control.value = ''; });
            event.target.closest('.result-field-clear').disabled = true;
            this.renderValues();
            return;
        }
        if (event.target.closest('.result-field-apply')) return this.apply();
    }

    updateSample() {
        const format = this.dialog.querySelector('.result-field-format').value;
        const match = /^(n|c|p)(\d*)(,*)$/.exec(format);
        if (!match) return this.dialog.querySelector('.result-field-sample').value = '1,234.5678';
        const decimals = match[2] === '' ? 2 : Number(match[2]);
        const divisor = Math.pow(1000, match[3].length);
        const options = {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        };
        if (match[1] == 'c') {
            options.style = 'currency';
            options.currency = this.options.currency || 'USD';
        } else if (match[1] == 'p') options.style = 'percent';
        this.dialog.querySelector('.result-field-sample').value = Number(match[1] == 'p' ? 0.123456 : 1234.5678 / divisor)
            .toLocaleString(undefined, options);
    }

    updateFilterMode() {
        const condition = this.dialog.querySelector('.result-field-filter-mode').value == 'condition';
        this.dialog.querySelectorAll('.result-field-filter-tabs button').forEach(button => {
            button.classList.toggle('active', button.dataset.mode == (condition ? 'condition' : 'value'));
        });
        this.dialog.querySelector('.result-field-value-filter').hidden = condition;
        this.dialog.querySelector('.result-field-condition-filter').hidden = !condition;
        this.renderCount();
    }

    visibleKeys() {
        return Array.from(this.values.keys()).filter(key =>
            !this.search || this.text(this.values.get(key)).toLowerCase().includes(this.search));
    }

    renderValues() {
        const keys = this.visibleKeys();
        this.dialog.querySelector('.result-field-values').innerHTML = keys.length
            ? keys.map(key => '<label class="result-field-value">' +
                `<input type="checkbox" value="${escapeHtml(key)}"${this.selected.has(key) ? ' checked' : ''}> ` +
                `<span>${escapeHtml(this.text(this.values.get(key)))}</span></label>`).join('')
            : '<p class="result-field-empty">No values match the search.</p>';
        this.renderCount();
    }

    // An empty selection would hide every row, so Apply stays disabled until something is chosen.
    renderCount() {
        const valueMode = this.dialog.querySelector('.result-field-filter-mode').value == 'value';
        const empty = valueMode && this.values.size > 0 && this.selected.size == 0;
        this.dialog.querySelector('.result-field-count').textContent =
            `${this.selected.size} of ${this.values.size} selected`;
        const selectAll = this.dialog.querySelector('.result-field-all');
        selectAll.checked = this.values.size > 0 && this.selected.size == this.values.size;
        selectAll.indeterminate = this.selected.size > 0 && this.selected.size < this.values.size;
        this.dialog.querySelector('.result-field-hint').hidden = !empty;
        this.dialog.querySelector('.result-field-apply').disabled = empty;
    }

    setVisible(checked) {
        this.visibleKeys().forEach(key => {
            if (checked) this.selected.add(key);
            else this.selected.delete(key);
        });
        this.renderValues();
    }

    // Commit every setting as one change so the grid and chart redraw once.
    apply() {
        if (this.values.size > 0 && this.selected.size == 0) return;
        const field = this.entry.field;
        const descending = this.dialog.querySelector('.result-field-sort').value == 'desc';
        const format = this.dialog.querySelector('.result-field-format').value;
        const headerControl = this.dialog.querySelector('.result-field-header');
        const header = headerControl.value.trim();
        if (!header) {
            headerControl.focus();
            return;
        }
        const duplicate = this.state.fields.some(item => item.field != this.entry.field && item.header == header);
        headerControl.setCustomValidity(duplicate ? 'Field headers must be unique.' : '');
        if (duplicate) return headerControl.reportValidity();
        const aggregation = this.dialog.querySelector('.result-field-summary').value;
        const showAs = this.dialog.querySelector('.result-field-show-as').value;
        const weightField = this.dialog.querySelector('.result-field-weight').value || null;
        const conditionMode = this.dialog.querySelector('.result-field-filter-mode').value == 'condition';
        const conditions = Array.from(this.dialog.querySelectorAll('.result-field-condition-operator')).map(control => {
            const index = control.dataset.index;
            return { operator: control.value, value: this.dialog.querySelector(`.result-field-condition-value[data-index="${index}"]`).value };
        }).filter(condition => condition.operator);
        const condition = conditionMode && conditions.length ? {
            and: this.dialog.querySelector('input[name="resultConditionJoin"]:checked').value == 'and',
            conditions: conditions
        } : null;
        this.state.defer(state => {
            state.setHeader(field, header);
            state.setAggregation(field, aggregation);
            state.setShowAs(field, showAs);
            state.setWeightField(field, weightField);
            state.setFieldFormat(field, format);
            state.setDescending(field, descending);
            // Selecting everything means no restriction, so later data is not silently excluded.
            if (conditionMode) {
                state.setFilter(field, null);
                state.setConditionFilter(field, condition);
            } else {
                state.setConditionFilter(field, null);
                if (this.selected.size == this.values.size) state.setFilter(field, null);
                else state.setFilter(field, Array.from(this.selected).map(key => this.values.get(key)));
            }
        });
        if (window.jQuery && typeof window.jQuery(this.dialog).modal == 'function') window.jQuery(this.dialog).modal('hide');
        else this.dialog.style.display = 'none';
    }
}
