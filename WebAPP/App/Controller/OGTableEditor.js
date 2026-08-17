const clone = value => JSON.parse(JSON.stringify(value));

const equal = (left, right) => {
    if ($.isArray(left) || $.isArray(right)){
        if (!$.isArray(left) || !$.isArray(right) || left.length != right.length){
            return false;
        }
        for (let i = 0; i < left.length; i++){
            if (!equal(left[i], right[i])) return false;
        }
        return true;
    }
    let a = parseFloat(left);
    let b = parseFloat(right);
    if (!isNaN(a) && !isNaN(b)) return Math.abs(a - b) < 1e-12;
    return left === right;
};

const flatten = value => {
    if (!$.isArray(value)) return [value];
    let out = [];
    $.each(value, function (id, item) { out = out.concat(flatten(item)); });
    return out;
};

const dimensions = value => {
    let out = [];
    let current = value;
    while ($.isArray(current)){
        out.push(current.length);
        current = current.length ? current[0] : null;
    }
    return out;
};

const unflatten = (values, shape) => {
    if (!shape.length) return values.shift();
    let out = [];
    for (let i = 0; i < shape[0]; i++){
        out.push(unflatten(values, shape.slice(1)));
    }
    return out;
};

const columnCoordinates = (index, shape) => {
    if (shape.length <= 1) return String(index + 1);
    let coordinates = [];
    for (let i = shape.length - 1; i >= 0; i--){
        let size = shape[i] || 1;
        coordinates.unshift((index % size) + 1);
        index = Math.floor(index / size);
    }
    return coordinates.join(', ');
};

export class OGTableEditor {

    static numericValue(value){
        if (typeof value == 'number') return Number.isFinite(value) ? value : null;
        if (typeof value != 'string' || $.trim(value) === '') return null;
        let number = Number($.trim(value));
        return Number.isFinite(number) ? number : null;
    }

    static validValue(value){
        let number = OGTableEditor.numericValue(value);
        if (number === null) return false;
        let options = OGTableEditor.options || {};
        if (Number.isFinite(options.min) && number < options.min) return false;
        return !(Number.isFinite(options.max) && number > options.max);
    }

    static shapeLabel(value){
        let shape = dimensions(value);
        if (shape.length == 1) return shape[0] + (shape[0] == 1 ? ' value' : ' values');
        return shape.join(' × ');
    }

    static rows(value, reference){
        let shape = dimensions(value);
        let first = shape[0] || 0;
        let rows = [];
        for (let i = 0; i < first; i++){
            let values = shape.length == 1 ? [value[i]] : flatten(value[i]);
            let baseline = $.isArray(reference)
                ? (shape.length == 1 ? [reference[i]] : flatten(reference[i]))
                : [];
            let row = { id: i + 1, label: String(i + 1), _baseline: baseline };
            $.each(values, function (column, item) { row['value_' + column] = item; });
            rows.push(row);
        }
        return rows;
    }

    static value(rows, shape){
        if (shape.length == 1){
            return rows.map(row => OGTableEditor.numericValue(row.value_0));
        }
        let trailing = shape.slice(1);
        let width = trailing.reduce((total, size) => total * size, 1);
        return rows.map(function (row) {
            let values = [];
            for (let i = 0; i < width; i++){
                values.push(OGTableEditor.numericValue(row['value_' + i]));
            }
            return unflatten(values, trailing);
        });
    }

    static selectedText(){
        if (!OGTableEditor.table) return null;
        let ranges = OGTableEditor.table.getRanges();
        if (!ranges.length) return null;
        let rows = ranges[ranges.length - 1].getCells();
        if (rows.length && !$.isArray(rows[0])) rows = [rows];
        let output = [];
        $.each(rows, function (id, cells) {
            let values = [];
            $.each(cells, function (cellId, cell) {
                let field = cell.getField();
                if (field.indexOf('value_') !== 0) return;
                let value = cell.getValue();
                values.push(value === null || value === undefined ? '' : String(value));
            });
            if (values.length) output.push(values.join('\t'));
        });
        return output.length ? output.join('\n') : null;
    }

    static open(options){
        if (!window.Tabulator){
            throw new Error('The table editor could not be loaded. Check the network connection and try again.');
        }
        if (!$.isArray(options.value)){
            throw new Error('This parameter does not contain a table value.');
        }

        OGTableEditor.close();
        OGTableEditor.options = options;
        OGTableEditor.shape = dimensions(options.value);
        OGTableEditor.returnFocus = document.activeElement;

        $('#ogcTableTitle').text(options.title);
        let meta = $('#ogcTableMeta').empty();
        $('<code>').text(String(options.name)).appendTo(meta);
        $('<span>').text(OGTableEditor.shapeLabel(options.value)).appendTo(meta);
        if (Number.isFinite(options.min) && Number.isFinite(options.max)){
            $('<span>').text('Allowed range ' + options.min + ' to ' + options.max).appendTo(meta);
        }
        $('#ogcTableModal').css('display', 'flex').attr('aria-hidden', 'false');
        $('body').addClass('ogc-table-open');

        let rowData = OGTableEditor.rows(options.value, options.reference);
        let columnCount = rowData.length ? flatten(options.value[0]).length : 0;
        if (OGTableEditor.shape.length == 1) columnCount = 1;
        let trailingShape = OGTableEditor.shape.slice(1);
        let formatter = function (cell) {
            let row = cell.getRow().getData();
            let column = parseInt(cell.getField().slice(6), 10);
            let baseline = row._baseline[column];
            let changed = !equal(cell.getValue(), baseline);
            cell.getElement().classList.toggle('ogc-table-modified', changed);
            cell.getElement().classList.toggle('ogc-table-invalid', !OGTableEditor.validValue(cell.getValue()));
            cell.getElement().title = changed && baseline !== undefined
                ? 'Reference value ' + baseline
                : '';
            return cell.getValue();
        };
        let editorParams = { step: 'any' };
        if (Number.isFinite(options.min)) editorParams.min = options.min;
        if (Number.isFinite(options.max)) editorParams.max = options.max;
        let validators = ['required', 'numeric'];
        if (Number.isFinite(options.min)) validators.push('min:' + options.min);
        if (Number.isFinite(options.max)) validators.push('max:' + options.max);
        let columns = [];
        for (let i = 0; i < columnCount; i++){
            let columnTitle = OGTableEditor.shape.length == 1
                ? 'Value'
                : ((options.columnLabel ? options.columnLabel + ' ' : '') + columnCoordinates(i, trailingShape));
            columns.push({
                title: columnTitle,
                field: 'value_' + i,
                minWidth: 100,
                editor: 'number',
                editorParams: editorParams,
                mutatorClipboard: function (value) {
                    let text = $.trim(String(value));
                    if (text === '') return null;
                    let number = Number(text);
                    return Number.isFinite(number) ? number : value;
                },
                validator: validators,
                formatter: formatter,
                hozAlign: 'right',
                headerHozAlign: 'right'
            });
        }

        OGTableEditor.table = new Tabulator('#ogcTableGrid', {
            data: rowData,
            index: 'id',
            height: '100%',
            layout: columnCount == 1 ? 'fitColumns' : 'fitDataStretch',
            movableColumns: false,
            selectableRange: 1,
            selectableRangeColumns: true,
            selectableRangeRows: true,
            selectableRangeClearCells: true,
            editTriggerEvent: 'dblclick',
            validationMode: 'highlight',
            clipboard: true,
            clipboardCopyStyled: false,
            clipboardCopyConfig: { rowHeaders: false, columnHeaders: false },
            clipboardCopyRowRange: 'range',
            clipboardPasteParser: 'range',
            clipboardPasteAction: 'range',
            rowHeader: {
                title: options.rowLabel || (OGTableEditor.shape.length == 1 ? 'Position' : 'Row'),
                formatter: 'rownum',
                width: 70,
                minWidth: 70,
                resizable: false,
                frozen: true,
                editor: false,
                hozAlign: 'center',
                headerHozAlign: 'center'
            },
            columnDefaults: { headerSort: false, resizable: 'header', vertAlign: 'middle' },
            columns: columns
        });
        OGTableEditor.table.on('tableBuilt', () => OGTableEditor.refreshStatus());
        OGTableEditor.table.on('cellEdited', () => OGTableEditor.refreshStatus());
        OGTableEditor.table.on('dataChanged', () => OGTableEditor.refreshStatus());
        OGTableEditor.table.on('clipboardPasted', () => OGTableEditor.refreshStatus());
        $('#ogcTableModal [data-table-act="cancel"]').focus();
    }

    static refreshStatus(){
        if (!OGTableEditor.table) return;
        let count = 0;
        let invalid = 0;
        $.each(OGTableEditor.table.getData(), function (id, row) {
            $.each(row, function (field, value) {
                if (field.indexOf('value_') !== 0) return;
                let column = parseInt(field.slice(6), 10);
                if (!equal(value, row._baseline[column])) count++;
                if (!OGTableEditor.validValue(value)) invalid++;
            });
        });
        let status = count ? count + ' modified ' + (count == 1 ? 'value' : 'values') : 'No modified values';
        if (invalid) status += ' · ' + invalid + ' invalid ' + (invalid == 1 ? 'value' : 'values');
        $('#ogcTableStatus').text(status).toggleClass('ogc-table-status-invalid', invalid > 0);
    }

    static apply(){
        if (!OGTableEditor.table || !OGTableEditor.options) return;
        let rows = clone(OGTableEditor.table.getData());
        let invalid = 0;
        $.each(rows, function (id, row) {
            $.each(row, function (field, value) {
                if (field.indexOf('value_') === 0 && !OGTableEditor.validValue(value)) invalid++;
            });
        });
        if (invalid){
            OGTableEditor.refreshStatus();
            return;
        }
        let value = OGTableEditor.value(rows, OGTableEditor.shape);
        let callback = OGTableEditor.options.onApply;
        OGTableEditor.close();
        callback(value);
    }

    static close(){
        if (OGTableEditor.table){
            OGTableEditor.table.destroy();
            OGTableEditor.table = null;
        }
        $('#ogcTableModal').hide().attr('aria-hidden', 'true');
        $('body').removeClass('ogc-table-open');
        OGTableEditor.options = null;
        if (OGTableEditor.returnFocus && document.contains(OGTableEditor.returnFocus)){
            OGTableEditor.returnFocus.focus();
        }
        OGTableEditor.returnFocus = null;
    }

    static initEvents(){
        $('#ogcTableModal').off('click.ogctable').on('click.ogctable', '[data-table-act]', function () {
            if ($(this).attr('data-table-act') == 'apply') OGTableEditor.apply();
            else OGTableEditor.close();
        }).on('click.ogctable', function (event) {
            if (event.target === this) OGTableEditor.close();
        });
        $(document).off('keydown.ogctable').on('keydown.ogctable', function (event) {
            if (event.key == 'Escape' && $('#ogcTableModal').is(':visible')){
                OGTableEditor.close();
            }
        }).off('copy.ogctable').on('copy.ogctable', function (event) {
            if (!$('#ogcTableModal').is(':visible') || $(event.target).is('input, textarea')) return;
            let text = OGTableEditor.selectedText();
            let clipboard = event.originalEvent && event.originalEvent.clipboardData;
            if (text === null || !clipboard) return;
            event.preventDefault();
            clipboard.setData('text/plain', text);
        });
    }
}
