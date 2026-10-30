import { ResultAggregator } from "./ResultAggregator.Class.js";
import { escapeHtml } from "./Html.Class.js";

// Display aggregated Results data in an interactive Tabulator table.
export class ResultGrid {

    constructor(selector, options = {}) {
        if (!window.Tabulator) throw new Error('The Results grid could not be loaded.');
        this.selector = selector;
        this.options = options;
        this.table = null;
        this.tableReady = false;
        this.detailTable = null;
        this.detailDialog = null;
        this.result = null;
        this.valueColumns = [];
        this.columnSignature = '';
        this.numberFormat = 'n2';
        this.currency = options.currency || 'USD';
        this.autoScrollCleanup = null;
        this.clipboardCleanup = null;
        this.pending = null;
    }

    // Run renders one at a time: destroying a table while it still builds leaves Tabulator's data promise to reject.
    render(result, numberFormat = 'n2') {
        this.pending = Promise.resolve(this.pending).then(() => this.build(result, numberFormat), () => {});
        return this.pending;
    }

    // Display the aggregated rows and columns without changing their values or identifiers.
    build(result, numberFormat = 'n2') {
        // A pending variable change can resolve after the page moved on and removed the host.
        if (!document.querySelector(this.selector)) return;
        const view = this.view(result);
        this.result = result;
        this.valueColumns = view.columns;
        this.numberFormat = numberFormat;
        const contextMenu = (event, cell) => this.cellMenu(cell);
        const columns = result.rowFields.map((field, index) => ({
            title: escapeHtml(this.displayText((result.rowHeaders || [])[index] || field)),
            titleDownload: this.displayText((result.rowHeaders || [])[index] || field),
            titleClipboard: this.displayText((result.rowHeaders || [])[index] || field),
            field: `row_${index}`,
            formatter: cell => this.rowField(cell, index),
            accessorClipboard: (value, data) => data[`row_${index}_display`],
            accessorDownload: value => ResultGrid.csvSafe(value),
            contextMenu: contextMenu,
            // Wijmo keeps row fields sorted; a header click toggles direction for sortableFields.
            headerSort: false,
            cssClass: this.isSortable(field) ? 'result-grid-row-field result-grid-sortable' : 'result-grid-row-field',
            headerClick: () => {
                if (this.isSortable(field) && typeof this.options.toggleFieldSort == 'function') {
                    this.options.toggleFieldSort(field);
                }
            },
            minWidth: 110
        })).concat(view.columns.map((entry, index) => ({
            // Headers are rendered as HTML by Tabulator, so the label is converted to text up front.
            title: escapeHtml(this.displayText(this.keyLabel(entry))),
            titleDownload: this.displayText(this.keyLabel(entry)),
            titleClipboard: this.displayText(this.keyLabel(entry)),
            field: `value_${index}`,
            cssClass: entry.isTotal ? 'result-grid-total-column' : '',
            hozAlign: 'right',
            headerHozAlign: 'left',
            headerSort: false,
            formatter: cell => this.number(cell.getValue(), numberFormat),
            accessorClipboard: value => this.number(value, numberFormat),
            contextMenu: contextMenu,
            minWidth: 105
        })));
        // Rebuild columns when field labels, totals, or numeric formatting change.
        const columnSignature = JSON.stringify({
            format: numberFormat,
            rows: result.rowFields.map((field, index) => [field, (result.rowHeaders || [])[index] || field]),
            columns: view.columns.map(entry => [entry.key, this.keyLabel(entry), entry.isTotal === true])
        });

        if (this.table && this.columnSignature != columnSignature) {
            this.clearRangeSelection();
            this.clearSelectionHighlight();
            if (this.autoScrollCleanup) this.autoScrollCleanup();
            if (this.clipboardCleanup) this.clipboardCleanup();
            this.table.destroy();
            this.table = null;
            this.tableReady = false;
        }
        this.columnSignature = columnSignature;
        if (this.table) {
            this.clearRangeSelection();
            this.clearSelectionHighlight();
            return this.table.replaceData(view.rows);
        }
        this.table = new Tabulator(this.selector, {
            data: view.rows,
            columns: columns,
            layout: 'fitData',
            maxHeight: '45vh',
            // Render only the columns in view: result sets reach dozens of technology columns.
            renderHorizontal: 'virtual',
            movableColumns: false,
            selectableRange: 1,
            selectableRangeColumns: true,
            selectableRangeRows: true,
            // Open with nothing selected instead of Tabulator's default first-cell range.
            selectableRangeInitializeDefault: false,
            selectableRangeAutoFocus: false,
            clipboard: true,
            clipboardCopyRowRange: 'range',
            clipboardCopyStyled: false,
            clipboardCopyConfig: {
                rowHeaders: false,
                columnHeaders: false,
                columnGroups: false,
                rowGroups: false,
                columnCalcs: false
            },
            placeholder: 'No result data is available for this view.',
            columnDefaults: { resizable: 'header', vertAlign: 'middle' },
            rowFormatter: row => {
                const data = row.getData();
                const element = row.getElement();
                element.classList.toggle('result-grid-total', data._isTotal);
                element.classList.toggle('result-grid-outer-total', data._isOuterTotal);
                element.classList.toggle('result-grid-grand-total', data._isGrandTotal);
                element.classList.toggle('result-grid-group-start', data._groupStart);
            }
        });
        this.table.on('cellDblClick', (event, cell) => {
            if (this.isValueCell(cell)) this.showDetail(cell);
        });
        this.table.on('renderComplete', () => this.paintRangeHighlight());
        this.table.on('rangeChanged', () => this.paintRangeHighlight());
        return new Promise(resolve => this.table.on('tableBuilt', () => {
            this.tableReady = true;
            this.bindRangeAutoScroll();
            this.bindRangeClipboard();
            resolve();
        }));
    }

    // Mark the selected columns' headers and each row's innermost field cell, from the current ranges.
    paintRangeHighlight() {
        const root = document.querySelector(this.selector);
        if (!root || !this.table || !this.tableReady) return;
        this.clearSelectionHighlight();

        const leafField = `row_${this.result.rowFields.length - 1}`;
        const fields = new Set();
        (this.table.getRanges() || []).forEach(range => {
            (range.getColumns() || []).forEach(column => fields.add(column.getField()));
            (range.getRows() || []).forEach(row => {
                const cell = (row.getCells() || []).find(item => item.getColumn().getField() == leafField);
                if (cell) cell.getElement().classList.add('result-grid-range-row-header');
            });
        });
        fields.forEach(field => {
            const header = root.querySelector(`.tabulator-col[tabulator-field="${field}"]`);
            if (header) header.classList.add('result-grid-range-header');
        });
    }

    // Copy the selected range as TSV with row-field values and column headers, as Wijmo did.
    bindRangeClipboard() {
        const root = document.querySelector(this.selector);
        if (!root || this.clipboardCleanup) return;
        const onCopy = event => {
            const text = this.rangeText();
            if (text == null) return;
            event.preventDefault();
            event.stopImmediatePropagation();
            if (event.clipboardData) event.clipboardData.setData('text/plain', text);
        };
        root.addEventListener('copy', onCopy, true);
        this.clipboardCleanup = () => {
            root.removeEventListener('copy', onCopy, true);
            this.clipboardCleanup = null;
        };
    }

    rangeText() {
        if (!this.table) return null;
        const ranges = this.table.getRanges() || [];
        if (!ranges.length) return null;
        const rows = ranges[0].getRows() || [];
        const columns = (ranges[0].getColumns() || []).filter(column => this.isValueField(column.getField()));
        if (!rows.length || !columns.length) return null;

        const fieldCount = this.result.rowFields.length;
        const header = this.result.rowFields.map((field, index) =>
            this.displayText((this.result.rowHeaders || [])[index] || field))
            .concat(columns.map(column => column.getDefinition().titleClipboard || ''));
        const lines = [header.join('\t')];
        rows.forEach(row => {
            const data = row.getData();
            const labels = [];
            for (let index = 0; index < fieldCount; index++) {
                labels.push(this.displayText(data[`row_${index}`]));
            }
            columns.forEach(column => {
                const value = data[column.getField()];
                labels.push(this.number(value, this.numberFormat));
            });
            lines.push(labels.join('\t'));
        });
        return lines.join('\n');
    }

    isValueField(field) {
        return /^value_\d+$/.test(field || '');
    }

    // Tabulator's range module has no drag auto-scroll, so scroll while dragging near an edge.
    bindRangeAutoScroll() {
        const holder = document.querySelector(`${this.selector} .tabulator-tableholder`);
        if (!holder || this.autoScrollCleanup) return;
        const margin = 45;
        const step = 14;
        let dragging = false;
        let timer = null;
        let dx = 0;
        let dy = 0;

        const stopTimer = () => {
            if (timer) clearInterval(timer);
            timer = null;
        };
        const onMove = event => {
            if (!dragging) return;
            const box = holder.getBoundingClientRect();
            dx = event.clientX > box.right - margin ? step : event.clientX < box.left + margin ? -step : 0;
            dy = event.clientY > box.bottom - margin ? step : event.clientY < box.top + margin ? -step : 0;
            if (!dx && !dy) return stopTimer();
            if (!timer) {
                timer = setInterval(() => {
                    holder.scrollLeft += dx;
                    holder.scrollTop += dy;
                }, 30);
            }
        };
        const onUp = () => {
            dragging = false;
            stopTimer();
        };
        const onDown = () => { dragging = true; };

        holder.addEventListener('mousedown', onDown);
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
        this.autoScrollCleanup = () => {
            stopTimer();
            holder.removeEventListener('mousedown', onDown);
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('mouseup', onUp);
            this.autoScrollCleanup = null;
        };
    }

    // Build ordered display rows and columns from regular and total cells.
    view(result) {
        const rows = this.orderedEntries(result.rowKeys, result.totals.rowKeys);
        const columns = result.valueFields.length
            ? this.orderedEntries(result.columnKeys, result.totals.columnKeys)
            : [];
        const valueField = result.valueFields.length ? result.valueFields[0].field : null;
        const groups = this.rowGroups(rows, result.rowFields.length);
        const cells = new Map();
        [result.cells, result.totals.cells].forEach(list => list.forEach(cell => {
            cells.set(ResultAggregator.cellID(ResultAggregator.keyID(cell.rowKey), ResultAggregator.keyID(cell.columnKey)),
                valueField ? cell.values[valueField] : null);
        }));
        // Build displayed row and column identifiers once instead of once per table cell.
        const columnIDs = columns.map(column => ResultAggregator.keyID(column.key));
        const valueKeys = columns.map((column, index) => `value_${index}`);
        const fieldKeys = result.rowFields.map((_, index) => `row_${index}`);
        const displayKeys = fieldKeys.map(key => `${key}_display`);

        return {
            columns: columns,
            rows: rows.map((row, rowIndex) => {
                const data = {
                    id: rowIndex,
                    _isTotal: row.isTotal,
                    // Depth of the total: the fewer fields it keys on, the wider it aggregates.
                    _isGrandTotal: row.isTotal && row.key.length == 0,
                    _isOuterTotal: row.isTotal && row.key.length > 0 && row.key.length < result.rowFields.length,
                    _rowKey: row.key.slice(),
                    _rowGroups: groups[rowIndex],
                    _groupStart: groups[rowIndex].some((group, index) =>
                        group && group.start && index < groups[rowIndex].length - 1 && rowIndex > 0)
                };
                this.rowLabels(row, result.rowFields.length).forEach((value, index) => {
                    // Convert display labels to safe text while preserving raw keys for detail lookup.
                    const text = this.displayText(value);
                    data[fieldKeys[index]] = text;
                    // A total shows only its marker; blank the display only, so exports stay labelled.
                    const marker = row.isTotal && index == row.key.length;
                    const totalKeyCell = row.isTotal && index < row.key.length;
                    data[displayKeys[index]] = marker ? text
                        : groups[rowIndex][index].display && !totalKeyCell ? text : '';
                });
                const rowID = ResultAggregator.keyID(row.key);
                for (let index = 0; index < columns.length; index++) {
                    const value = cells.get(ResultAggregator.cellID(rowID, columnIDs[index]));
                    data[valueKeys[index]] = value === undefined ? null : value;
                }
                return data;
            })
        };
    }

    // Place each repeated row label at the visual center of its hierarchical group.
    rowGroups(rows, fieldCount) {
        // end: true by default, so a level a row does not reach still draws its bottom rule.
        const groups = rows.map(() => Array.from({ length: fieldCount }, () => ({ start: false, end: true, display: false })));
        for (let level = 0; level < fieldCount; level++) {
            let start = 0;
            while (start < rows.length) {
                // A row joins a level only when its key reaches it, so a Year subtotal stays in its Case.
                if (rows[start].key.length <= level) {
                    start++;
                    continue;
                }
                const prefix = rows[start].key.slice(0, level + 1);
                let end = start;
                while (end + 1 < rows.length && rows[end + 1].key.length > level &&
                    this.samePrefix(rows[end + 1].key, prefix)) end++;
                // Centre the label on a row that can show it; subtotals blank the values they total.
                const candidates = [];
                for (let index = start; index <= end; index++) {
                    if (!(rows[index].isTotal && level < rows[index].key.length)) candidates.push(index);
                }
                const middle = candidates.length ? candidates[Math.floor((candidates.length - 1) / 2)] : -1;
                for (let index = start; index <= end; index++) {
                    groups[index][level] = { start: index == start, end: index == end, display: index == middle };
                }
                start = end + 1;
            }
        }
        return groups;
    }

    // Apply group boundary classes while resetting recycled Tabulator cells.
    rowField(cell, index) {
        const data = cell.getRow().getData();
        const group = data._rowGroups[index];
        const element = cell.getElement();
        element.classList.toggle('result-grid-group-first-cell', group.start);
        element.classList.toggle('result-grid-group-last-cell', group.end);
        element.classList.toggle('result-grid-group-middle-cell', group.display);
        return escapeHtml(data[`row_${index}_display`]);
    }

    // Place each subtotal after its final child and grand totals at the end.
    orderedEntries(keys, totalKeys) {
        const totals = new Map(totalKeys.map(key => [ResultAggregator.keyID(key), key]));
        const entries = [];
        keys.forEach((key, index) => {
            entries.push({ key: key, isTotal: false });
            const next = keys[index + 1];
            for (let length = key.length - 1; length >= 0; length--) {
                const prefix = key.slice(0, length);
                const prefixID = ResultAggregator.keyID(prefix);
                if (totals.has(prefixID) && (!next || !this.samePrefix(next, prefix))) {
                    entries.push({ key: totals.get(prefixID), isTotal: true });
                    totals.delete(prefixID);
                }
            }
        });
        totals.forEach(key => entries.push({ key: key, isTotal: true }));
        return entries;
    }

    samePrefix(key, prefix) {
        return prefix.every((value, index) => Object.is(key[index], value));
    }

    isSortable(field) {
        const sortable = this.options.sortableFields;
        return Array.isArray(sortable) ? sortable.includes(field) : false;
    }

    rowLabels(entry, fieldCount) {
        const labels = entry.key.slice();
        // A total over no field at all spans the whole result, so name it accordingly.
        if (entry.isTotal) labels.push(entry.key.length ? 'Subtotal' : 'Grand Total');
        while (labels.length < fieldCount) labels.push('');
        return labels;
    }

    keyLabel(entry) {
        if (!entry.key.length) return this.result && this.result.valueFields.length ? this.result.valueFields[0].header : 'Value';
        return entry.key.join(' / ') + (entry.isTotal ? ' Total' : '');
    }

    // Provide the PivotGrid-compatible commands that apply to the selected cell.
    cellMenu(cell) {
        const field = this.targetField(cell);
        const items = [];
        if (field) {
            items.push({
                label: '<i class="fa fa-times"></i> Remove Field',
                disabled: typeof this.options.removeField != 'function',
                action: () => this.options.removeField(field)
            });
            items.push({
                label: '<i class="fa fa-cog"></i> Field Settings&hellip;',
                disabled: typeof this.options.editField != 'function',
                action: () => this.options.editField(field)
            });
        }
        if (this.isValueCell(cell)) {
            items.push({ separator: true });
            items.push({
                label: '<i class="fa fa-list-alt"></i> Show Detail&hellip;',
                disabled: typeof this.options.getDetail != 'function',
                action: () => this.showDetail(cell)
            });
        }
        return items;
    }

    targetField(cell) {
        const field = cell.getColumn().getField();
        const rowMatch = /^row_(\d+)$/.exec(field);
        if (rowMatch) return this.result.rowFields[Number(rowMatch[1])];
        return this.isValueCell(cell) && this.result.valueFields.length ? this.result.valueFields[0].field : null;
    }

    isValueCell(cell) {
        return this.isValueField(cell.getColumn().getField());
    }

    // Resolve the row and column keys represented by a displayed value cell.
    cellContext(cell) {
        const columnIndex = Number(cell.getColumn().getField().slice('value_'.length));
        const column = this.valueColumns[columnIndex];
        return {
            rowKey: cell.getRow().getData()._rowKey.slice(),
            columnKey: column ? column.key.slice() : [],
            rowHeader: cell.getRow().getData()._rowKey.map(value => this.displayText(value)).join(' / ') || 'All rows',
            columnHeader: column ? this.displayText(this.keyLabel(column)) : 'All columns',
            value: cell.getValue()
        };
    }

    // Convert stored HTML labels into safe plain text for dialogs and exports.
    displayText(value) {
        return typeof this.options.plainText == 'function' ? this.options.plainText(value) : String(value ?? '');
    }

    // Open a read-only MUIOGO detail grid for the records summarized by a cell.
    showDetail(cell) {
        if (!this.isValueCell(cell) || typeof this.options.getDetail != 'function') return;
        const context = this.cellContext(cell);
        const records = this.options.getDetail(context);
        this.openDetailDialog(Array.isArray(records) ? records : [], context);
    }

    // Create the reusable Bootstrap dialog without inserting result values as HTML.
    createDetailDialog() {
        if (this.detailDialog) return this.detailDialog;
        const dialog = document.createElement('div');
        dialog.className = 'modal fade result-grid-detail-dialog';
        dialog.tabIndex = -1;
        dialog.setAttribute('role', 'dialog');
        dialog.innerHTML = '<div class="modal-dialog modal-lg" role="document"><div class="modal-content">' +
            '<div class="modal-header"><button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>' +
            '<h4 class="modal-title">Detail View</h4></div><div class="modal-body"><p class="result-grid-detail-summary"></p>' +
            '<div class="result-grid-detail-table"></div></div><div class="modal-footer">' +
            '<button type="button" class="btn btn-default" data-dismiss="modal">Close</button></div></div></div>';
        document.body.appendChild(dialog);
        this.detailDialog = dialog;
        return dialog;
    }

    openDetailDialog(records, context) {
        const dialog = this.createDetailDialog();
        const summary = dialog.querySelector('.result-grid-detail-summary');
        summary.textContent = `${context.rowHeader} | ${context.columnHeader} | ${records.length.toLocaleString()} item${records.length == 1 ? '' : 's'}`;
        const detailRecords = records.map(record => Object.fromEntries(Object.entries(record).map(([field, value]) => [
            field,
            typeof value == 'string'
                ? this.displayText(value)
                : value
        ])));
        const render = () => {
            if (this.detailTable) this.detailTable.destroy();
            this.detailTable = new Tabulator(dialog.querySelector('.result-grid-detail-table'), {
                data: detailRecords,
                autoColumns: true,
                layout: 'fitDataStretch',
                maxHeight: '55vh',
                placeholder: 'No detail records are available for this cell.',
                columnDefaults: {
                    headerSort: true,
                    resizable: 'header',
                    formatter: cell => escapeHtml(cell.getValue())
                }
            });
        };
        if (window.jQuery && typeof window.jQuery(dialog).modal == 'function') {
            window.jQuery(dialog).one('shown.bs.modal', render).modal('show');
        } else {
            dialog.style.display = 'block';
            dialog.classList.add('in');
            render();
        }
    }

    clearSelectionHighlight() {
        const root = document.querySelector(this.selector);
        if (!root) return;
        root.querySelectorAll('.result-grid-range-header, .result-grid-range-row-header').forEach(element => {
            element.classList.remove('result-grid-range-header', 'result-grid-range-row-header');
        });
    }

    // Remove grid-owned ranges before Tabulator replaces the elements they reference.
    clearRangeSelection() {
        if (this.table && this.tableReady) (this.table.getRanges() || []).forEach(range => range.remove());
        const root = document.querySelector(this.selector);
        const selection = window.getSelection ? window.getSelection() : null;
        if (root && selection && selection.rangeCount &&
            (root.contains(selection.anchorNode) || root.contains(selection.focusNode))) {
            selection.removeAllRanges();
        }
    }

    // Format numbers with the MUIO field format while leaving First/Last text values intact.
    number(value, format) {
        if (value === null || value === undefined) return '';
        const number = Number(value);
        if (!Number.isFinite(number)) return this.displayText(value);
        const match = /^(n|c|p)(\d*)(,*)$/.exec(format || '');
        if (!match) return number.toLocaleString();
        const decimals = match[2] === '' ? 2 : Number(match[2]);
        const scaled = number / Math.pow(1000, match[3].length);
        const options = {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        };
        if (match[1] == 'c') {
            options.style = 'currency';
            options.currency = this.currency;
        } else if (match[1] == 'p') options.style = 'percent';
        return scaled.toLocaleString(undefined, options);
    }

    // Neutralise formula injection: Excel and Calc execute cells starting with = + - @.
    static csvSafe(value) {
        if (typeof value != 'string' || value === '') return value;
        return /^[\t\r]*[=+\-@]/.test(value) ? `'${value}` : value;
    }

    downloadCSV(fileName = 'PivotGrid.csv') {
        if (this.table) this.table.download('csv', fileName);
    }

    destroy() {
        this.clearRangeSelection();
        if (this.autoScrollCleanup) this.autoScrollCleanup();
        if (this.clipboardCleanup) this.clipboardCleanup();
        if (this.table) this.table.destroy();
        if (this.detailTable) this.detailTable.destroy();
        if (this.detailDialog) this.detailDialog.remove();
        this.table = null;
        this.tableReady = false;
        this.detailTable = null;
        this.detailDialog = null;
        this.columnSignature = '';
    }
}
