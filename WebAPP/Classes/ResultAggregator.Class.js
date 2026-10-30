const RESULT_SHOW_TOTALS = Object.freeze({
    None: 'none',
    GrandTotals: 'grand',
    Subtotals: 'subtotals'
});
export const RESULT_FILTER_CONDITION_LIMIT = 2;

// Group Results records into rows, columns, filtered values, and totals for charts and tables.
export class ResultAggregator {

    // Provide the supported row and column total modes used in Results configuration.
    static get ShowTotals() {
        return RESULT_SHOW_TOTALS;
    }

    static aggregate(items, configuration = {}) {
        if (!Array.isArray(items)) {
            throw new TypeError('ResultAggregator items must be an array.');
        }

        // Validate and prepare the selected fields, filters, and totals before grouping records.
        const rowDefinitions = this.fieldDefinitions(configuration.rowFields || []);
        const columnDefinitions = this.fieldDefinitions(configuration.columnFields || []);
        const rowFields = rowDefinitions.map(field => field.field);
        const columnFields = columnDefinitions.map(field => field.field);
        const valueFields = this.valueFields(configuration.valueFields || ['Value']);
        const filters = this.filterDefinitions(configuration.filters || []);
        const totalConfiguration = this.totalConfiguration(configuration.totals || {});
        this.validateLayout(rowFields, columnFields, valueFields);

        const rowKeys = [];
        const columnKeys = [];
        const rowIDs = new Set();
        const columnIDs = new Set();
        const aggregates = new Map();

        // Apply active filters before grouping records into row and column cells.
        items.forEach(item => {
            if (!this.matchesFilters(item, filters)) return;
            const rowKey = rowFields.map(field => this.keyValue(item[field]));
            const columnKey = columnFields.map(field => this.keyValue(item[field]));
            const rowID = this.keyID(rowKey);
            const columnID = this.keyID(columnKey);

            if (!rowIDs.has(rowID)) {
                rowIDs.add(rowID);
                rowKeys.push(rowKey);
            }
            if (!columnIDs.has(columnID)) {
                columnIDs.add(columnID);
                columnKeys.push(columnKey);
            }

            const cellID = this.cellID(rowID, columnID);
            let cell = aggregates.get(cellID);
            if (!cell) {
                cell = {
                    rowKey: rowKey,
                    columnKey: columnKey,
                    values: {},
                    summaries: {}
                };
                valueFields.forEach(valueField => {
                    cell.summaries[valueField.field] = this.createSummary();
                });
                aggregates.set(cellID, cell);
            }

            valueFields.forEach(valueField => {
                const weight = valueField.weightField ? this.numberValue(item[valueField.weightField]) : null;
                this.addSummary(cell.summaries[valueField.field], item[valueField.field], weight);
            });
        });

        // Create result cells containing the summed values for each row and column combination.
        const cells = Array.from(aggregates.values()).map(cell => {
            const values = {};
            valueFields.forEach(valueField => {
                values[valueField.field] = this.aggregateSummary(cell.summaries[valueField.field], valueField);
            });
            return {
                rowKey: cell.rowKey.slice(),
                columnKey: cell.columnKey.slice(),
                values: values,
                summaries: cell.summaries
            };
        });

        // Sort keys and cells so charts, grids, and exports receive stable ordering.
        rowKeys.sort((left, right) => this.compareKeys(left, right, rowDefinitions));
        columnKeys.sort((left, right) => this.compareKeys(left, right, columnDefinitions));
        const rowOrder = new Map(rowKeys.map((key, index) => [this.keyID(key), index]));
        const columnOrder = new Map(columnKeys.map((key, index) => [this.keyID(key), index]));
        cells.sort((left, right) => {
            const rowDifference = rowOrder.get(this.keyID(left.rowKey)) - rowOrder.get(this.keyID(right.rowKey));
            return rowDifference || columnOrder.get(this.keyID(left.columnKey)) - columnOrder.get(this.keyID(right.columnKey));
        });

        // Calculate requested subtotals separately so charts cannot treat them as regular data.
        const totals = this.buildTotals(cells, rowDefinitions, columnDefinitions, valueFields, totalConfiguration);
        this.applyShowAs(cells, rowKeys, columnKeys, valueFields, totals);
        const resultCells = cells.map(cell => ({
            rowKey: cell.rowKey,
            columnKey: cell.columnKey,
            values: cell.values
        }));

        return {
            rowFields: rowFields,
            rowHeaders: rowDefinitions.map(field => field.header),
            columnFields: columnFields,
            columnHeaders: columnDefinitions.map(field => field.header),
            valueFields: valueFields,
            filters: filters.map(filter => ({
                field: filter.field,
                values: filter.values ? filter.values.slice() : null,
                condition: filter.condition
            })),
            rowKeys: rowKeys,
            columnKeys: columnKeys,
            cells: resultCells,
            totals: totals
        };
    }

    // Return the filtered source records represented by a regular or total result cell.
    static getDetail(items, configuration, rowKey = [], columnKey = []) {
        if (!Array.isArray(items)) {
            throw new TypeError('ResultAggregator items must be an array.');
        }
        const rowFields = this.fieldDefinitions(configuration.rowFields || []).map(field => field.field);
        const columnFields = this.fieldDefinitions(configuration.columnFields || []).map(field => field.field);
        const filters = this.filterDefinitions(configuration.filters || []);
        if (!Array.isArray(rowKey) || rowKey.length > rowFields.length) {
            throw new Error('The result detail row key does not match the active layout.');
        }
        if (!Array.isArray(columnKey) || columnKey.length > columnFields.length) {
            throw new Error('The result detail column key does not match the active layout.');
        }
        return items.filter(item => this.matchesFilters(item, filters) &&
            this.matchesKey(item, rowFields, rowKey) &&
            this.matchesKey(item, columnFields, columnKey));
    }

    static matchesKey(item, fields, key) {
        return key.every((value, index) => Object.is(this.keyValue(item[fields[index]]), value));
    }

    // Preserve each dimension's name and requested sort direction.
    static fieldDefinitions(fields) {
        if (!Array.isArray(fields)) {
            throw new TypeError('ResultAggregator fields must be arrays.');
        }
        return fields.map(field => {
            const name = typeof field == 'string' ? field : field && field.field;
            if (!name || typeof name != 'string') {
                throw new TypeError('ResultAggregator fields must have a string name.');
            }
            return {
                field: name,
                header: typeof field == 'object' && field !== null && field.header ? field.header : name,
                descending: typeof field == 'object' && field !== null && field.descending === true
            };
        });
    }

    // Normalize object and array filter forms into exact-value selections.
    static filterDefinitions(filters) {
        if (filters === null || filters === undefined) return [];
        let definitions;
        if (Array.isArray(filters)) {
            definitions = filters;
        } else if (typeof filters == 'object') {
            definitions = Object.keys(filters).map(field => ({ field: field, values: filters[field] }));
        } else {
            throw new TypeError('ResultAggregator filters must be an array or object.');
        }
        return definitions.map(filter => {
            if (!filter || typeof filter.field != 'string' || !filter.field) {
                throw new TypeError('ResultAggregator filters must have a string field name.');
            }
            const hasValues = filter.values !== null && filter.values !== undefined;
            const values = hasValues ? (Array.isArray(filter.values) ? filter.values : [filter.values]) : null;
            return {
                field: filter.field,
                values: values ? values.map(value => this.keyValue(value)) : null,
                valueIDs: values ? new Set(values.map(value => this.keyID([this.keyValue(value)]))) : null,
                condition: this.conditionDefinition(filter.condition)
            };
        });
    }

    // Require every configured field filter to match its selected values.
    static matchesFilters(item, filters) {
        return filters.every(filter => {
            const value = this.keyValue(item[filter.field]);
            return (!filter.valueIDs || filter.valueIDs.has(this.keyID([value]))) &&
                (!filter.condition || this.matchesCondition(value, filter.condition));
        });
    }

    static conditionDefinition(condition) {
        if (!condition) return null;
        const conditions = (condition.conditions || []).slice(0, RESULT_FILTER_CONDITION_LIMIT).filter(item => item && item.operator != null)
            .map(item => ({ operator: item.operator, value: item.value }));
        return conditions.length ? { and: condition.and !== false, conditions: conditions } : null;
    }

    static matchesCondition(value, definition) {
        const matches = definition.conditions.map(condition => this.matchesOperator(value, condition.operator, condition.value));
        return definition.and ? matches.every(Boolean) : matches.some(Boolean);
    }

    static matchesOperator(value, operator, expected) {
        const names = { 0:'equals', 1:'notEquals', 2:'greaterThan', 3:'greaterThanOrEqual', 4:'lessThan', 5:'lessThanOrEqual', 6:'beginsWith', 7:'endsWith', 8:'contains', 9:'notContains', 10:'notBeginsWith', 11:'notEndsWith' };
        const operation = names[operator] || operator;
        const comparisonValue = typeof value == 'number' && expected !== '' && Number.isFinite(Number(expected))
            ? Number(expected) : expected;
        const comparison = this.compareValues(value, comparisonValue);
        const text = String(value == null ? '' : value).toLowerCase();
        const search = String(expected == null ? '' : expected).toLowerCase();
        if (operation == 'equals') return comparison == 0;
        if (operation == 'notEquals') return comparison != 0;
        if (operation == 'greaterThan') return comparison > 0;
        if (operation == 'greaterThanOrEqual') return comparison >= 0;
        if (operation == 'lessThan') return comparison < 0;
        if (operation == 'lessThanOrEqual') return comparison <= 0;
        if (operation == 'beginsWith') return text.startsWith(search);
        if (operation == 'notBeginsWith') return !text.startsWith(search);
        if (operation == 'endsWith') return text.endsWith(search);
        if (operation == 'notEndsWith') return !text.endsWith(search);
        if (operation == 'contains') return text.includes(search);
        if (operation == 'notContains') return !text.includes(search);
        throw new Error(`Unsupported result filter operator: ${operator}`);
    }

    // Normalize row and column total settings without using Wijmo enum values.
    static totalConfiguration(totals) {
        if (totals === null || totals === undefined) totals = {};
        if (typeof totals != 'object' || Array.isArray(totals)) {
            throw new TypeError('ResultAggregator totals must be an object.');
        }
        return {
            rows: this.normalizeTotalMode(totals.rows),
            columns: this.normalizeTotalMode(totals.columns)
        };
    }

    static normalizeTotalMode(mode) {
        if (mode === undefined || mode === null || mode === false || mode == this.ShowTotals.None) {
            return this.ShowTotals.None;
        }
        if (mode == this.ShowTotals.GrandTotals || mode == 'grandTotals') {
            return this.ShowTotals.GrandTotals;
        }
        if (mode === true || mode == this.ShowTotals.Subtotals) {
            return this.ShowTotals.Subtotals;
        }
        throw new Error(`Unsupported result total mode: ${mode}`);
    }

    // Aggregate base cells across every requested row and column prefix.
    static buildTotals(cells, rowDefinitions, columnDefinitions, valueFields, configuration) {
        const rowLevels = this.totalLevels(rowDefinitions.length, configuration.rows);
        const columnLevels = this.totalLevels(columnDefinitions.length, configuration.columns);
        const rowKeys = new Map();
        const columnKeys = new Map();
        const aggregates = new Map();

        cells.forEach(cell => {
            const rowOptions = [{ key: cell.rowKey, level: rowDefinitions.length, isTotal: false }]
                .concat(rowLevels.map(level => ({ key: cell.rowKey.slice(0, level), level: level, isTotal: true })));
            const columnOptions = [{ key: cell.columnKey, level: columnDefinitions.length, isTotal: false }]
                .concat(columnLevels.map(level => ({ key: cell.columnKey.slice(0, level), level: level, isTotal: true })));

            rowOptions.forEach(row => {
                columnOptions.forEach(column => {
                    if (!row.isTotal && !column.isTotal) return;
                    if (row.isTotal) rowKeys.set(this.keyID(row.key), row.key.slice());
                    if (column.isTotal) columnKeys.set(this.keyID(column.key), column.key.slice());
                    const totalID = this.cellID(this.keyID(row.key), this.keyID(column.key));
                    let total = aggregates.get(totalID);
                    if (!total) {
                        total = {
                            rowKey: row.key.slice(),
                            columnKey: column.key.slice(),
                            rowLevel: row.level,
                            columnLevel: column.level,
                            values: {},
                            summaries: {}
                        };
                        valueFields.forEach(valueField => {
                            total.summaries[valueField.field] = this.createSummary();
                        });
                        aggregates.set(totalID, total);
                    }
                    valueFields.forEach(valueField => {
                        this.mergeSummary(total.summaries[valueField.field], cell.summaries[valueField.field]);
                    });
                });
            });
        });

        const sortedRowKeys = Array.from(rowKeys.values()).sort((left, right) =>
            left.length - right.length || this.compareKeys(left, right, rowDefinitions.slice(0, left.length)));
        const sortedColumnKeys = Array.from(columnKeys.values()).sort((left, right) =>
            left.length - right.length || this.compareKeys(left, right, columnDefinitions.slice(0, left.length)));
        const rowOrder = new Map(sortedRowKeys.map((key, index) => [this.keyID(key), index]));
        const columnOrder = new Map(sortedColumnKeys.map((key, index) => [this.keyID(key), index]));
        const totalCells = Array.from(aggregates.values()).map(total => {
            const values = {};
            valueFields.forEach(valueField => {
                values[valueField.field] = this.aggregateSummary(total.summaries[valueField.field], valueField);
            });
            return {
                rowKey: total.rowKey,
                columnKey: total.columnKey,
                rowLevel: total.rowLevel,
                columnLevel: total.columnLevel,
                values: values,
                summaries: total.summaries
            };
        }).sort((left, right) => {
            const leftRowOrder = left.rowLevel == rowDefinitions.length
                ? sortedRowKeys.length
                : rowOrder.get(this.keyID(left.rowKey));
            const rightRowOrder = right.rowLevel == rowDefinitions.length
                ? sortedRowKeys.length
                : rowOrder.get(this.keyID(right.rowKey));
            const rowDifference = leftRowOrder - rightRowOrder || this.compareKeys(left.rowKey, right.rowKey, rowDefinitions);
            if (rowDifference) return rowDifference;
            const leftColumnOrder = left.columnLevel == columnDefinitions.length
                ? sortedColumnKeys.length
                : columnOrder.get(this.keyID(left.columnKey));
            const rightColumnOrder = right.columnLevel == columnDefinitions.length
                ? sortedColumnKeys.length
                : columnOrder.get(this.keyID(right.columnKey));
            return leftColumnOrder - rightColumnOrder || this.compareKeys(left.columnKey, right.columnKey, columnDefinitions);
        });

        return {
            rows: configuration.rows,
            columns: configuration.columns,
            rowKeys: sortedRowKeys,
            columnKeys: sortedColumnKeys,
            cells: totalCells.map(cell => ({
                rowKey: cell.rowKey,
                columnKey: cell.columnKey,
                rowLevel: cell.rowLevel,
                columnLevel: cell.columnLevel,
                values: cell.values
            }))
        };
    }

    static totalLevels(fieldCount, mode) {
        if (mode == this.ShowTotals.None || fieldCount == 0) return [];
        if (mode == this.ShowTotals.GrandTotals) return [0];
        return Array.from({ length: fieldCount }, (value, level) => level);
    }

    // Normalize the active measure and its MUIO-compatible calculation settings.
    static valueFields(fields) {
        if (!Array.isArray(fields)) {
            throw new TypeError('ResultAggregator value fields must be an array.');
        }
        if (fields.length > 1) {
            throw new Error('ResultAggregator supports at most one Value field.');
        }
        return fields.map(field => {
            const definition = typeof field == 'string' ? { field: field } : field;
            if (!definition || typeof definition.field != 'string' || !definition.field) {
                throw new TypeError('ResultAggregator value fields must have a string name.');
            }
            const aggregation = definition.aggregation || 'sum';
            const supported = ['sum', 'count', 'average', 'max', 'min', 'range', 'std', 'variance', 'stdPopulation', 'variancePopulation', 'countAll', 'first', 'last'];
            if (!supported.includes(aggregation)) {
                throw new Error(`Unsupported result aggregation: ${aggregation}`);
            }
            return {
                field: definition.field,
                header: definition.header || definition.field,
                aggregation: aggregation,
                showAs: definition.showAs || 'none',
                weightField: definition.weightField || null,
                format: definition.format || 'n2'
            };
        });
    }

    static createSummary() {
        return { countAll: 0, count: 0, numericCount: 0, sum: 0, sumSquares: 0, min: null, max: null, first: null, last: null };
    }

    static addSummary(summary, rawValue, rawWeight) {
        summary.countAll++;
        if (rawValue === null || rawValue === undefined || rawValue === '') return;
        const numeric = this.numberValue(rawValue);
        summary.count++;
        if (summary.first === null) summary.first = rawValue;
        summary.last = rawValue;
        if (summary.min === null || this.compareValues(rawValue, summary.min) < 0) summary.min = rawValue;
        if (summary.max === null || this.compareValues(rawValue, summary.max) > 0) summary.max = rawValue;
        if (numeric !== null) {
            summary.numericCount++;
            const weight = rawWeight === null ? 1 : rawWeight;
            const weightedValue = numeric * weight;
            summary.sum += weightedValue;
            summary.sumSquares += weightedValue * weightedValue;
        }
    }

    static mergeSummary(target, source) {
        target.countAll += source.countAll;
        target.count += source.count;
        target.numericCount += source.numericCount;
        target.sum += source.sum;
        target.sumSquares += source.sumSquares;
        if (target.first === null) target.first = source.first;
        if (source.last !== null) target.last = source.last;
        if (source.min !== null && (target.min === null || this.compareValues(source.min, target.min) < 0)) target.min = source.min;
        if (source.max !== null && (target.max === null || this.compareValues(source.max, target.max) > 0)) target.max = source.max;
    }

    static aggregateSummary(summary, field) {
        const count = summary.count;
        const numericCount = summary.numericCount;
        if (field.aggregation == 'countAll') return summary.countAll;
        if (field.aggregation == 'count') return count;
        if (!count) return null;
        if (field.aggregation == 'first') return summary.first;
        if (field.aggregation == 'last') return summary.last;
        if (field.aggregation == 'min') return summary.min;
        if (field.aggregation == 'max') return summary.max;
        if (field.aggregation == 'range') return Number(summary.max) - Number(summary.min);
        if (field.aggregation == 'sum') return summary.sum;
        if (field.aggregation == 'average') return numericCount ? summary.sum / numericCount : 0;
        const populationVariance = numericCount > 1
            ? Math.max(0, summary.sumSquares / numericCount - Math.pow(summary.sum / numericCount, 2)) : 0;
        if (field.aggregation == 'variancePopulation') return populationVariance;
        if (field.aggregation == 'stdPopulation') return Math.sqrt(populationVariance);
        const sampleVariance = numericCount > 1 ? populationVariance * numericCount / (numericCount - 1) : 0;
        if (field.aggregation == 'variance') return sampleVariance;
        if (field.aggregation == 'std') return Math.sqrt(sampleVariance);
        return null;
    }

    // Apply Excel-style Show As transformations after the base summaries are complete.
    static applyShowAs(cells, rowKeys, columnKeys, valueFields, totals = { cells: [], rowKeys: [], columnKeys: [] }) {
        const allCells = cells.concat(totals.cells);
        const lookup = new Map(allCells.map(cell => [this.cellID(this.keyID(cell.rowKey), this.keyID(cell.columnKey)), cell]));
        // Compare siblings at the same depth; never mix detail rows and subtotals.
        const groupID = key => key.length + ':' + this.keyID(key.slice(0, -1));
        const groupKeys = keys => keys.reduce((groups, key) => {
            const prefix = groupID(key);
            if (!groups.has(prefix)) groups.set(prefix, []);
            groups.get(prefix).push(key);
            return groups;
        }, new Map());
        const rowGroups = groupKeys(rowKeys.concat(totals.rowKeys));
        const columnGroups = groupKeys(columnKeys.concat(totals.columnKeys));
        const rowDepth = rowKeys.length ? rowKeys[0].length : 0;
        const columnDepth = columnKeys.length ? columnKeys[0].length : 0;
        const rowCalculations = new Set(['differenceRow', 'differenceRowPercent', 'percentPreviousRow', 'runningTotal', 'runningTotalPercent']);
        const columnCalculations = new Set(['differenceColumn', 'differenceColumnPercent', 'percentPreviousColumn']);
        valueFields.forEach(field => {
            if (field.showAs == 'none') return;
            // Snapshot before transforming either detail cells or totals.
            const original = new Map(allCells.map(cell => [cell, cell.values[field.field]]));
            // Denominators use only full-depth keys, excluding subtotal duplication.
            const rowTotal = rowKey => columnKeys.reduce((sum, columnKey) => {
                const cell = lookup.get(this.cellID(this.keyID(rowKey), this.keyID(columnKey)));
                const value = cell ? original.get(cell) : null;
                return sum + (Number.isFinite(value) ? value : 0);
            }, 0);
            const columnTotal = columnKey => rowKeys.reduce((sum, rowKey) => {
                const cell = lookup.get(this.cellID(this.keyID(rowKey), this.keyID(columnKey)));
                const value = cell ? original.get(cell) : null;
                return sum + (Number.isFinite(value) ? value : 0);
            }, 0);
            const grand = cells.reduce((sum, cell) => sum + (Number.isFinite(original.get(cell)) ? original.get(cell) : 0), 0);
            allCells.forEach(cell => {
                const value = original.get(cell);
                const rowGrand = rowDepth > 0 && cell.rowKey.length == 0;
                const columnGrand = columnDepth > 0 && cell.columnKey.length == 0;
                // A grand total has no previous sibling or running-total group.
                if (!Number.isFinite(value) ||
                    (rowGrand && rowCalculations.has(field.showAs)) ||
                    (columnGrand && columnCalculations.has(field.showAs))) {
                    cell.values[field.field] = null;
                    return;
                }
                const groupRows = rowGroups.get(groupID(cell.rowKey)) || [];
                const groupColumns = columnGroups.get(groupID(cell.columnKey)) || [];
                const row = groupRows.findIndex(key => this.keyID(key) == this.keyID(cell.rowKey));
                const column = groupColumns.findIndex(key => this.keyID(key) == this.keyID(cell.columnKey));
                const previousRow = row > 0
                    ? lookup.get(this.cellID(this.keyID(groupRows[row - 1]), this.keyID(cell.columnKey))) : null;
                const previousColumn = column > 0
                    ? lookup.get(this.cellID(this.keyID(cell.rowKey), this.keyID(groupColumns[column - 1]))) : null;
                const previousRowValue = previousRow ? original.get(previousRow) : null;
                const previousColumnValue = previousColumn ? original.get(previousColumn) : null;
                const ratio = denominator => Number.isFinite(value) && denominator ? value / denominator : null;
                if (field.showAs == 'differenceRow') cell.values[field.field] = Number.isFinite(previousRowValue) ? value - previousRowValue : null;
                else if (field.showAs == 'differenceRowPercent') cell.values[field.field] = Number.isFinite(previousRowValue) && previousRowValue ? (value - previousRowValue) / previousRowValue : null;
                else if (field.showAs == 'differenceColumn') cell.values[field.field] = Number.isFinite(previousColumnValue) ? value - previousColumnValue : null;
                else if (field.showAs == 'differenceColumnPercent') cell.values[field.field] = Number.isFinite(previousColumnValue) && previousColumnValue ? (value - previousColumnValue) / previousColumnValue : null;
                else if (field.showAs == 'percentGrand') cell.values[field.field] = ratio(grand);
                else if (field.showAs == 'percentRow') cell.values[field.field] = ratio(rowTotal(cell.rowKey));
                else if (field.showAs == 'percentColumn') cell.values[field.field] = ratio(columnTotal(cell.columnKey));
                else if (field.showAs == 'percentPreviousRow') cell.values[field.field] = previousRow ? ratio(previousRowValue) : 1;
                else if (field.showAs == 'percentPreviousColumn') cell.values[field.field] = previousColumn ? ratio(previousColumnValue) : 1;
                else if (field.showAs == 'runningTotal' || field.showAs == 'runningTotalPercent') {
                    const groupIndex = groupRows.findIndex(key => this.keyID(key) == this.keyID(cell.rowKey));
                    const running = groupRows.slice(0, groupIndex + 1).reduce((sum, rowKey) => {
                        const item = lookup.get(this.cellID(this.keyID(rowKey), this.keyID(cell.columnKey)));
                        const itemValue = item ? original.get(item) : null;
                        return sum + (Number.isFinite(itemValue) ? itemValue : 0);
                    }, 0);
                    const groupTotal = groupRows.reduce((sum, rowKey) => {
                        const item = lookup.get(this.cellID(this.keyID(rowKey), this.keyID(cell.columnKey)));
                        const itemValue = item ? original.get(item) : null;
                        return sum + (Number.isFinite(itemValue) ? itemValue : 0);
                    }, 0);
                    cell.values[field.field] = field.showAs == 'runningTotalPercent'
                        ? (groupTotal ? running / groupTotal : null) : running;
                }
            });
        });
    }

    // Reject layouts that reuse dimensions or measures in conflicting roles.
    static validateLayout(rowFields, columnFields, valueFields) {
        const dimensions = rowFields.concat(columnFields);
        if (new Set(dimensions).size != dimensions.length) {
            throw new Error('A result field cannot be used in both rows and columns.');
        }
        valueFields.forEach(valueField => {
            if (dimensions.includes(valueField.field)) {
                throw new Error('A result value field cannot also be a row or column field.');
            }
        });
    }

    static keyValue(value) {
        return value === undefined ? null : value;
    }

    static numberValue(value) {
        if (value === null || value === undefined || value === '') return null;
        const number = Number(value);
        return Number.isFinite(number) ? number : null;
    }

    // Compare compound keys by value type and configured direction.
    static compareKeys(left, right, definitions) {
        for (let index = 0; index < definitions.length; index++) {
            const comparison = this.compareValues(left[index], right[index]);
            if (comparison) return definitions[index].descending ? -comparison : comparison;
        }
        return 0;
    }

    static compareValues(left, right) {
        if (Object.is(left, right)) return 0;
        if (left === null || left === undefined) return 1;
        if (right === null || right === undefined) return -1;

        const order = { number: 0, string: 1, boolean: 2, bigint: 3, object: 4 };
        const leftType = typeof left;
        const rightType = typeof right;
        if (leftType != rightType) return (order[leftType] ?? 5) - (order[rightType] ?? 5);
        if (leftType == 'number') {
            if (Number.isNaN(left)) return Number.isNaN(right) ? 0 : 1;
            if (Number.isNaN(right)) return -1;
        }
        if (left < right) return -1;
        if (left > right) return 1;

        const leftText = JSON.stringify(left);
        const rightText = JSON.stringify(right);
        return leftText < rightText ? -1 : leftText > rightText ? 1 : 0;
    }

    static keyID(values) {
        return JSON.stringify(values.map(value => [typeof value, value]));
    }

    static cellID(rowID, columnID) {
        return `${rowID}\u0000${columnID}`;
    }
}
