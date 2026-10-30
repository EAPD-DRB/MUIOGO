import { ResultAggregator, RESULT_FILTER_CONDITION_LIMIT } from "./ResultAggregator.Class.js";

const RESULT_LAYOUT_VERSION = 2;
const RESULT_AGGREGATIONS = Object.freeze(['sum', 'count', 'average', 'max', 'min', 'range', 'std', 'variance', 'stdPopulation', 'variancePopulation', 'countAll', 'first', 'last']);
const RESULT_SHOW_AS = Object.freeze(['none', 'differenceRow', 'differenceRowPercent', 'differenceColumn', 'differenceColumnPercent', 'percentGrand', 'percentRow', 'percentColumn', 'runningTotal', 'runningTotalPercent', 'percentPreviousRow', 'percentPreviousColumn']);
// Numeric settings Wijmo persisted inside saved views, mapped back by the legacy reader.
const WIJMO_TOTALS = Object.freeze({
    0: ResultAggregator.ShowTotals.None,
    1: ResultAggregator.ShowTotals.GrandTotals,
    2: ResultAggregator.ShowTotals.Subtotals
});
const WIJMO_AGGREGATIONS = Object.freeze({
    1: 'sum', 2: 'count', 3: 'average', 4: 'max', 5: 'min', 6: 'range', 7: 'std',
    8: 'variance', 9: 'stdPopulation', 10: 'variancePopulation', 11: 'countAll', 12: 'first', 13: 'last'
});
const WIJMO_SHOW_AS = Object.freeze({
    0: 'none', 1: 'differenceRow', 2: 'differenceRowPercent', 3: 'differenceColumn',
    4: 'differenceColumnPercent', 5: 'percentGrand', 6: 'percentRow', 7: 'percentColumn',
    8: 'runningTotal', 9: 'runningTotalPercent', 10: 'percentPreviousRow', 11: 'percentPreviousColumn'
});

// Store the model-specific Results field layout and provide ResultAggregator configuration.
export class ResultLayoutState {

    static get Version() {
        return RESULT_LAYOUT_VERSION;
    }

    static get Aggregations() {
        return RESULT_AGGREGATIONS;
    }

    static get ShowAs() {
        return RESULT_SHOW_AS;
    }

    static isTotalMode(mode) {
        return Object.values(ResultAggregator.ShowTotals).includes(mode);
    }

    constructor(fields = [], numberFormat = 'n2') {
        this.rows = [];
        this.columns = [];
        this.filterFields = [];
        this.values = [];
        this.filters = {};
        this.conditionFilters = {};
        this.descending = {};
        this.fieldSettings = {};
        this.totals = { rows: ResultAggregator.ShowTotals.None, columns: ResultAggregator.ShowTotals.None };
        this.numberFormat = numberFormat;
        this.defaultNumberFormat = numberFormat;
        this.warnings = [];
        this.listeners = [];
        this.fields = [];
        this.setFields(fields);
    }

    // Swap the catalogue when the variable changes, dropping entries the new fields do not have.
    setFields(fields) {
        const previous = this.fieldSettings;
        this.fields = (fields || []).map(field => ({
            field: field.field,
            header: field.header == null ? field.field : field.header,
            defaultHeader: field.header == null ? field.field : field.header,
            isHtml: field.isHtml === true,
            isNumeric: field.isNumeric === true,
            // Declared by the caller: measures belong in Values, every other field in Rows.
            isMeasure: field.isMeasure === true
        }));
        this.fieldSettings = {};
        this.fields.forEach(field => {
            const settings = previous[field.field] || {};
            this.fieldSettings[field.field] = {
                header: settings.header || field.header,
                aggregation: RESULT_AGGREGATIONS.includes(settings.aggregation) ? settings.aggregation : (field.isMeasure ? 'sum' : 'count'),
                showAs: RESULT_SHOW_AS.includes(settings.showAs) ? settings.showAs : 'none',
                weightField: settings.weightField || null,
                format: settings.format || (field.isMeasure ? this.numberFormat : '')
            };
            field.header = this.fieldSettings[field.field].header;
        });
        const known = name => this.fields.some(field => field.field == name);
        return this.defer(() => {
            const areas = this.getAreas();
            Object.keys(areas).forEach(area => {
                areas[area].splice(0, areas[area].length, ...areas[area].filter(known));
            });
            [this.filters, this.conditionFilters, this.descending].forEach(map => {
                Object.keys(map).forEach(name => { if (!known(name)) delete map[name]; });
            });
            Object.keys(this.fieldSettings).forEach(name => {
                const weight = this.fieldSettings[name].weightField;
                if (weight && !known(weight)) this.fieldSettings[name].weightField = null;
            });
        });
    }

    // Saved views name fields by header ("Tech Desc") while data uses the binding ("TechDesc").
    resolveField(fieldName) {
        if (fieldName == null) return null;
        const match = this.fields.find(field => field.field == fieldName || field.header == fieldName || field.defaultHeader == fieldName);
        return match ? match.field : null;
    }

    getAreas() {
        return { rows: this.rows, columns: this.columns, filters: this.filterFields, values: this.values };
    }

    // Move a field to one area, or out of all of them when area is null.
    assignField(fieldName, area, index = -1) {
        const field = this.resolveField(fieldName);
        if (!field) return this;
        const areas = this.getAreas();
        // Reject an unknown area before detaching the field, so a bad name cannot silently drop it.
        if (area != null && !areas[area]) throw new Error(`Unknown layout area: ${area}`);
        Object.keys(areas).forEach(key => {
            const position = areas[key].indexOf(field);
            if (position >= 0) areas[key].splice(position, 1);
        });
        if (area && areas[area]) {
            const target = areas[area];
            if (index < 0 || index > target.length) target.push(field);
            else target.splice(index, 0, field);
        }
        return this.changed();
    }

    setFilter(fieldName, values) {
        const field = this.resolveField(fieldName);
        if (!field) return this;
        if (values == null) delete this.filters[field];
        else {
            if (typeof values == 'string' || typeof values[Symbol.iterator] != 'function') {
                throw new TypeError('Result filter values must be an iterable collection.');
            }
            this.filters[field] = Array.from(values);
        }
        return this.changed();
    }

    setConditionFilter(fieldName, definition) {
        const field = this.resolveField(fieldName);
        if (!field) return this;
        if (definition == null) delete this.conditionFilters[field];
        else this.conditionFilters[field] = {
            and: definition.and !== false,
            // MUIO combines at most two conditions in one field filter.
            conditions: (definition.conditions || []).slice(0, RESULT_FILTER_CONDITION_LIMIT).map(condition => ({
                operator: condition.operator,
                value: condition.value
            }))
        };
        return this.changed();
    }

    getFieldSettings(fieldName) {
        const field = this.resolveField(fieldName);
        return field ? this.fieldSettings[field] : null;
    }

    resetFieldSettings() {
        this.numberFormat = this.defaultNumberFormat;
        this.fields.forEach(field => {
            field.header = field.defaultHeader;
            this.fieldSettings[field.field] = {
                header: field.defaultHeader,
                aggregation: field.isMeasure ? 'sum' : 'count',
                showAs: 'none',
                weightField: null,
                format: field.isMeasure ? this.defaultNumberFormat : ''
            };
        });
    }

    setHeader(fieldName, header) {
        const field = this.resolveField(fieldName);
        const text = String(header == null ? '' : header).trim();
        if (!field || !text) return this;
        if (this.fields.some(item => item.field != field && item.header == text)) {
            throw new Error(`Result field headers must be unique: ${text}`);
        }
        this.fieldSettings[field].header = text;
        const entry = this.fields.find(item => item.field == field);
        if (entry) entry.header = text;
        return this.changed();
    }

    setAggregation(fieldName, aggregation) {
        const settings = this.getFieldSettings(fieldName);
        if (!settings) return this;
        if (!RESULT_AGGREGATIONS.includes(aggregation)) throw new Error(`Unsupported result aggregation: ${aggregation}`);
        settings.aggregation = aggregation;
        return this.changed();
    }

    setShowAs(fieldName, showAs) {
        const settings = this.getFieldSettings(fieldName);
        if (!settings) return this;
        if (!RESULT_SHOW_AS.includes(showAs)) throw new Error(`Unsupported Show As calculation: ${showAs}`);
        settings.showAs = showAs;
        return this.changed();
    }

    setWeightField(fieldName, weightField) {
        const settings = this.getFieldSettings(fieldName);
        if (!settings) return this;
        const weight = weightField == null || weightField === '' ? null : this.resolveField(weightField);
        if (weightField && !weight) throw new Error(`Unknown result weight field: ${weightField}`);
        settings.weightField = weight;
        return this.changed();
    }

    setFieldFormat(fieldName, format) {
        const field = this.resolveField(fieldName);
        if (!field || typeof format != 'string' || !format.trim()) return this;
        this.fieldSettings[field].format = format;
        if (this.values.includes(field)) this.numberFormat = format;
        return this.changed();
    }

    // Drop filter values absent from the new data, so a stale selection cannot empty the grid.
    pruneFilterValues(items) {
        const names = Object.keys(this.filters);
        if (!names.length) return this;
        // Collect values for every active filter during one pass over the result records.
        const present = new Map(names.map(name => [name, new Map()]));
        (items || []).forEach(item => {
            names.forEach(name => {
                const value = ResultAggregator.keyValue(item[name]);
                present.get(name).set(ResultAggregator.keyID([value]), value);
            });
        });
        return this.defer(() => {
            names.forEach(name => {
                const available = present.get(name);
                const kept = this.filters[name].map(value => {
                    const exact = available.get(ResultAggregator.keyID([ResultAggregator.keyValue(value)]));
                    if (exact !== undefined) return exact;
                    const matches = Array.from(available.values()).filter(item => String(item) == String(value));
                    return matches.length == 1 ? matches[0] : undefined;
                }).filter(value => value !== undefined);
                if (kept.length) this.filters[name] = kept;
                else delete this.filters[name];
            });
        });
    }

    setDescending(fieldName, descending) {
        const field = this.resolveField(fieldName);
        if (!field) return this;
        if (descending) this.descending[field] = true;
        else delete this.descending[field];
        return this.changed();
    }

    setTotals(area, mode) {
        if (area != 'rows' && area != 'columns') throw new Error(`Unknown totals area: ${area}`);
        if (!ResultLayoutState.isTotalMode(mode)) throw new Error(`Unknown totals mode: ${mode}`);
        this.totals[area] = mode;
        return this.changed();
    }

    setNumberFormat(format) {
        if (typeof format != 'string' || !format.trim()) throw new TypeError('Result number format must be a non-empty string.');
        this.numberFormat = format;
        this.values.forEach(field => { if (this.fieldSettings[field]) this.fieldSettings[field].format = format; });
        return this.changed();
    }

    // Returns an unsubscribe function so a rebuilt panel does not leave stale listeners behind.
    onChange(listener) {
        if (typeof listener != 'function') return () => {};
        this.listeners.push(listener);
        return () => this.offChange(listener);
    }

    offChange(listener) {
        const index = this.listeners.indexOf(listener);
        if (index >= 0) this.listeners.splice(index, 1);
        return this;
    }

    changed() {
        if (!this.deferred) this.listeners.slice().forEach(listener => listener(this));
        return this;
    }

    // Batch edits into one notification, as the panel's Defer Updates option needs.
    defer(apply) {
        const nested = this.deferred === true;
        this.deferred = true;
        try {
            apply(this);
        } finally {
            this.deferred = nested;
        }
        return nested ? this : this.changed();
    }

    // Build the field, filter, sorting, and total settings used to aggregate Results data.
    configuration() {
        const definition = name => ({
            field: name,
            header: this.fieldSettings[name] ? this.fieldSettings[name].header : name,
            descending: this.descending[name] === true
        });
        return {
            rowFields: this.rows.map(definition),
            columnFields: this.columns.map(definition),
            valueFields: this.values.map(name => Object.assign({ field: name }, this.fieldSettings[name])),
            // Apply active filters regardless of their displayed field area to preserve Wijmo behavior.
            filters: Array.from(new Set(Object.keys(this.filters).concat(Object.keys(this.conditionFilters)))).map(name => ({
                field: name,
                values: this.filters[name] ? this.filters[name].slice() : null,
                condition: this.conditionFilters[name] || null
            })),
            totals: { rows: this.totals.rows, columns: this.totals.columns }
        };
    }

    // MUIOGO saved-view format: fields by binding, so it stays readable once Wijmo is gone.
    definition() {
        const filters = {};
        Object.keys(this.filters).forEach(name => { filters[name] = this.filters[name].slice(); });
        const conditionFilters = {};
        Object.keys(this.conditionFilters).forEach(name => {
            conditionFilters[name] = JSON.parse(JSON.stringify(this.conditionFilters[name]));
        });
        return {
            version: ResultLayoutState.Version,
            rows: this.rows.slice(),
            columns: this.columns.slice(),
            filterFields: this.filterFields.slice(),
            values: this.values.slice(),
            filters: filters,
            conditionFilters: conditionFilters,
            fieldSettings: JSON.parse(JSON.stringify(this.fieldSettings)),
            descending: Object.keys(this.descending),
            totals: { rows: this.totals.rows, columns: this.totals.columns },
            numberFormat: this.numberFormat
        };
    }

    // Read both the existing Wijmo saved-view format and the versioned MUIOGO format.
    apply(definition) {
        const source = typeof definition == 'string' ? JSON.parse(definition) : definition;
        this.warnings = [];
        if (!source || typeof source != 'object') return this;
        return ResultLayoutState.isLegacy(source) ? this.applyLegacy(source) : this.applyDefinition(source);
    }

    static isLegacy(source) {
        return source.version == null &&
            (Array.isArray(source.fields) || (source.rowFields && source.rowFields.items));
    }

    warn(setting, detail) {
        this.warnings.push(detail ? `${setting}: ${detail}` : setting);
    }

    applyDefinition(source) {
        // Reject unknown formats instead of partially loading incompatible saved-view state.
        if (source.version !== 1 && source.version !== ResultLayoutState.Version) {
            this.warn('Unsupported saved view version; view was not loaded', String(source.version));
            return this;
        }
        const claimed = new Set();
        const list = (names, area) => {
            if (names == null) return [];
            if (!Array.isArray(names)) {
                this.warn('Invalid field area', area);
                return [];
            }
            return names.map(name => ({ name: name, field: this.resolveField(name) })).filter(entry => {
                if (!entry.field) {
                    this.warn('Unknown field', String(entry.name));
                    return false;
                }
                if (claimed.has(entry.field)) {
                    this.warn('Duplicate field placement ignored', entry.field);
                    return false;
                }
                claimed.add(entry.field);
                return true;
            }).map(entry => entry.field);
        };
        return this.defer(() => {
            this.resetFieldSettings();
            this.totals = { rows: ResultAggregator.ShowTotals.None, columns: ResultAggregator.ShowTotals.None };
            this.rows = list(source.rows, 'rows');
            this.columns = list(source.columns, 'columns');
            this.filterFields = list(source.filterFields, 'filters');
            this.values = list(source.values, 'values');
            this.filters = {};
            Object.keys(source.filters || {}).forEach(name => {
                const field = this.resolveField(name);
                const values = source.filters[name];
                if (!field) this.warn('Unknown filter field', name);
                else if (!Array.isArray(values)) this.warn('Invalid filter values', name);
                else this.filters[field] = values.slice();
            });
            this.conditionFilters = {};
            Object.keys(source.conditionFilters || {}).forEach(name => {
                const field = this.resolveField(name);
                if (field) this.conditionFilters[field] = JSON.parse(JSON.stringify(source.conditionFilters[name]));
                else this.warn('Unknown condition filter field', name);
            });
            Object.keys(source.fieldSettings || {}).forEach(name => {
                const field = this.resolveField(name);
                if (!field) return this.warn('Unknown field settings', name);
                const settings = source.fieldSettings[name] || {};
                if (settings.header) {
                    try { this.setHeader(field, settings.header); }
                    catch (error) { this.warn('Duplicate field header ignored', settings.header); }
                }
                if (RESULT_AGGREGATIONS.includes(settings.aggregation)) this.fieldSettings[field].aggregation = settings.aggregation;
                if (RESULT_SHOW_AS.includes(settings.showAs)) this.fieldSettings[field].showAs = settings.showAs;
                if (settings.weightField) this.fieldSettings[field].weightField = this.resolveField(settings.weightField);
                if (settings.format) this.fieldSettings[field].format = settings.format;
            });
            this.descending = {};
            if (source.descending != null && !Array.isArray(source.descending)) {
                this.warn('Invalid descending fields');
            } else {
                (source.descending || []).forEach(name => {
                const field = this.resolveField(name);
                    if (field) this.descending[field] = true;
                    else this.warn('Unknown descending field', String(name));
                });
            }
            const totals = source.totals || {};
            ['rows', 'columns'].forEach(area => {
                if (totals[area] == null) return;
                if (ResultLayoutState.isTotalMode(totals[area])) this.totals[area] = totals[area];
                else this.warn('Invalid totals mode', `${area}: ${totals[area]}`);
            });
            if (typeof source.numberFormat == 'string' && source.numberFormat.trim()) {
                this.numberFormat = source.numberFormat;
                this.values.forEach(field => {
                    if (this.fieldSettings[field] && !(source.fieldSettings && source.fieldSettings[field])) {
                        this.fieldSettings[field].format = source.numberFormat;
                    }
                });
            } else if (source.numberFormat != null) this.warn('Invalid number format');
        });
    }

    // Wijmo kept area membership under `{items:[...]}` and filters as `{showValues:{value:true}}`.
    applyLegacy(source) {
        const claimed = new Set();
        const list = area => ((source[area] && source[area].items) || [])
            .map(name => this.resolveField(name)).filter(field => {
                if (!field || claimed.has(field)) {
                    if (field) this.warn('Duplicate field placement ignored', field);
                    return false;
                }
                claimed.add(field);
                return true;
            });
        return this.defer(() => {
            this.resetFieldSettings();
            this.totals = { rows: ResultAggregator.ShowTotals.None, columns: ResultAggregator.ShowTotals.None };
            this.rows = list('rowFields');
            this.columns = list('columnFields');
            this.filterFields = list('filterFields');
            this.values = list('valueFields');
            this.filters = {};
            this.conditionFilters = {};
            this.descending = {};
            (source.fields || []).forEach(entry => this.applyLegacyField(entry, source));
            const rows = WIJMO_TOTALS[source.showRowTotals];
            const columns = WIJMO_TOTALS[source.showColumnTotals];
            if (rows != null) this.totals.rows = rows;
            if (columns != null) this.totals.columns = columns;
            this.reportLegacyLayout(source);
        });
    }

    applyLegacyField(entry, source) {
        const field = this.resolveField(entry.key != null ? entry.key : entry.binding);
        const label = (entry.key != null ? entry.key : entry.binding) || 'field';
        if (!field) {
            // Only worth reporting when the missing field was actually placed in the layout.
            const placed = ['rowFields', 'columnFields', 'filterFields', 'valueFields']
                .some(area => ((source[area] && source[area].items) || []).includes(label));
            if (placed) this.warn('Unknown field', label);
            return;
        }
        if (entry.header) {
            try { this.setHeader(field, entry.header); }
            catch (error) { this.warn('Duplicate field header ignored', entry.header); }
        }
        if (entry.descending === true) this.descending[field] = true;

        const filter = entry.filter || {};
        const values = filter.showValues;
        // Empty showValues means no value restriction, not "exclude everything".
        if (values && Object.keys(values).length) {
            this.filters[field] = Object.keys(values).filter(value => values[value]);
        }
        // Warn when a legacy text search cannot be reproduced from its saved selected values.
        if (filter.filterText && !(values && Object.keys(values).length)) {
            this.warn('Text filter not applied', `${label} (${filter.filterText})`);
        }
        const legacyConditions = [filter.condition1, filter.condition2].filter(Boolean);
        if (legacyConditions.length) {
            this.conditionFilters[field] = {
                and: filter.and !== false,
                conditions: legacyConditions.map(condition => ({
                    operator: condition.operator,
                    value: condition.value
                }))
            };
        }

        if (this.values.includes(field)) {
            if (WIJMO_AGGREGATIONS[entry.aggregate]) this.fieldSettings[field].aggregation = WIJMO_AGGREGATIONS[entry.aggregate];
            if (WIJMO_SHOW_AS[entry.showAs] != null) this.fieldSettings[field].showAs = WIJMO_SHOW_AS[entry.showAs];
            if (entry.weightField) this.fieldSettings[field].weightField = this.resolveField(entry.weightField);
            // The value field's format drove the grid under Wijmo, so keep honouring it.
            if (entry.format) {
                this.fieldSettings[field].format = entry.format;
                this.numberFormat = entry.format;
            }
        }
    }

    reportLegacyLayout(source) {
        if (source.totalsBeforeData === true) this.warn('Totals are always shown after the data');
        if (source.showZeros === true) this.warn('Show zeros is not supported');
        if (WIJMO_TOTALS[source.showRowTotals] == null && source.showRowTotals != null) {
            this.warn('Unknown row totals mode', String(source.showRowTotals));
        }
        if (WIJMO_TOTALS[source.showColumnTotals] == null && source.showColumnTotals != null) {
            this.warn('Unknown column totals mode', String(source.showColumnTotals));
        }
    }
}
