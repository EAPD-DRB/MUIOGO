import assert from 'node:assert/strict';
import { test } from 'node:test';
import { ResultAggregator as A } from '../../WebAPP/Classes/ResultAggregator.Class.js';
import { ResultLayoutState } from '../../WebAPP/Classes/ResultLayoutState.Class.js';

function close(actual, expected) {
    assert.ok(Math.abs(actual - expected) < 1e-12, `${actual} != ${expected}`);
}
function value(result, row, column = []) {
    const cell = [...result.cells, ...result.totals.cells].find(cell =>
        JSON.stringify(cell.rowKey) == JSON.stringify(row) && JSON.stringify(cell.columnKey) == JSON.stringify(column));
    assert.ok(cell, `Missing cell ${JSON.stringify([row, column])}`);
    return cell.values.Value;
}

test('grand-total percentages show 25%, 75%, and 100%', () => {
    const result = A.aggregate([{ Year: 2020, Value: 10 }, { Year: 2021, Value: 30 }], {
        rowFields: ['Year'], columnFields: [], valueFields: [{ field: 'Value', showAs: 'percentGrand' }], totals: { rows: 'grand' }
    });
    close(value(result, [2020]), 0.25);
    close(value(result, [2021]), 0.75);
    close(value(result, []), 1);
});

const items = [];
for (const Case of ['A', 'B']) for (const Year of [2020, 2021]) {
    for (const Group of ['G', 'H']) for (const Tech of ['one', 'two']) {
        items.push({ Case, Year, Group, Tech, Value: (items.length + 1) * 10 });
    }
}
const sum = records => records.reduce((total, item) => total + item.Value, 0);
const matches = (item, fields, key) => key.every((entry, index) => item[fields[index]] === entry);
const rowFields = ['Case', 'Year'];
const columnFields = ['Group', 'Tech'];
for (const showAs of ['percentGrand', 'percentRow', 'percentColumn']) {
    for (const rows of ['none', 'grand', 'subtotals']) for (const columns of ['none', 'grand', 'subtotals']) {
        test(`${showAs} uses raw full-depth denominators with ${rows} row / ${columns} column totals`, () => {
            const result = A.aggregate(items, {
                rowFields, columnFields, valueFields: [{ field: 'Value', showAs }], totals: { rows, columns }
            });
            for (const cell of [...result.cells, ...result.totals.cells]) {
                const numerator = sum(items.filter(item => matches(item, rowFields, cell.rowKey) && matches(item, columnFields, cell.columnKey)));
                const denominator = showAs == 'percentGrand' ? sum(items)
                    : sum(items.filter(item => showAs == 'percentRow'
                        ? matches(item, rowFields, cell.rowKey) : matches(item, columnFields, cell.columnKey)));
                close(cell.values.Value, numerator / denominator);
            }
        });
    }
}

const hierarchy = [
    { Case: 'A', Year: 2020, Value: 10 }, { Case: 'A', Year: 2021, Value: 20 },
    { Case: 'B', Year: 2020, Value: 30 }, { Case: 'B', Year: 2021, Value: 40 }
];
const expected = {
    differenceRow: [null, 10, null, 10, null, 40],
    differenceRowPercent: [null, 1, null, 1 / 3, null, 4 / 3],
    percentPreviousRow: [1, 2, 1, 4 / 3, 1, 7 / 3],
    runningTotal: [10, 30, 30, 70, 30, 100],
    runningTotalPercent: [1 / 3, 1, 3 / 7, 1, 0.3, 1]
};
const keys = [['A', 2020], ['A', 2021], ['B', 2020], ['B', 2021], ['A'], ['B']];
for (const [showAs, values] of Object.entries(expected)) {
    test(`${showAs} keeps detail and subtotal siblings separate`, () => {
        const result = A.aggregate(hierarchy, {
            rowFields, columnFields: [], valueFields: [{ field: 'Value', showAs }], totals: { rows: 'subtotals' }
        });
        keys.forEach((key, index) => values[index] === null
            ? assert.equal(value(result, key), null) : close(value(result, key), values[index]));
        assert.equal(value(result, []), null);
    });
}
for (const [showAs, rowMode] of [['differenceColumn', 'differenceRow'], ['differenceColumnPercent', 'differenceRowPercent'], ['percentPreviousColumn', 'percentPreviousRow']]) {
    test(`${showAs} handles column subtotals and leaves grand totals blank`, () => {
        const result = A.aggregate(hierarchy, {
            rowFields: [], columnFields: rowFields, valueFields: [{ field: 'Value', showAs }], totals: { columns: 'subtotals' }
        });
        keys.forEach((key, index) => expected[rowMode][index] === null
            ? assert.equal(value(result, [], key), null) : close(value(result, [], key), expected[rowMode][index]));
        assert.equal(value(result, [], []), null);
    });
}

test('descending order controls previous rows at detail and subtotal depths', () => {
    const result = A.aggregate(hierarchy, {
        rowFields: [{ field: 'Case', descending: true }, { field: 'Year', descending: true }], columnFields: [],
        valueFields: [{ field: 'Value', showAs: 'differenceRow' }], totals: { rows: 'subtotals' }
    });
    assert.equal(value(result, ['B', 2021]), null);
    close(value(result, ['B', 2020]), -10);
    assert.equal(value(result, ['B']), null);
    close(value(result, ['A']), -40);
});
test('percentage zero denominators and null source values remain blank', () => {
    const result = A.aggregate([{ Year: 2020, Value: null }, { Year: 2021, Value: 0 }], {
        rowFields: ['Year'], valueFields: [{ field: 'Value', showAs: 'percentGrand' }], totals: { rows: 'grand' }
    });
    for (const cell of [...result.cells, ...result.totals.cells]) assert.equal(cell.values.Value, null);
});
test('no-calculation totals preserve aggregation of the underlying records', () => {
    const result = A.aggregate([{ Year: 2020, Value: 10 }, { Year: 2020, Value: 20 }, { Year: 2021, Value: 30 }], {
        rowFields: ['Year'], valueFields: [{ field: 'Value', aggregation: 'average' }], totals: { rows: 'grand' }
    });
    close(value(result, [2020]), 15);
    close(value(result, [2021]), 30);
    close(value(result, []), 20);
});

test('enabling totals preserves detail calculations for every supported Show As and summary', () => {
    const records = [...items, {...items[0], Value: 300}, {...items[0], Value: -20}];
    for (const showAs of ResultLayoutState.ShowAs) for (const aggregation of ['sum', 'average', 'count', 'min', 'max']) {
        const configuration = {rowFields, columnFields, valueFields: [{field: 'Value', showAs, aggregation}]};
        const expected = A.aggregate(records, configuration).cells;
        for (const rows of ['none', 'grand', 'subtotals']) for (const columns of ['none', 'grand', 'subtotals']) {
            assert.deepEqual(A.aggregate(records, {...configuration, totals: {rows, columns}}).cells, expected,
                `${showAs}/${aggregation}/${rows}/${columns}`);
        }
    }
});

test('sparse negative values retain their signs and do not create missing detail cells', () => {
    const result = A.aggregate([{Year: 2020, Tech: 'A', Value: -10}, {Year: 2021, Tech: 'B', Value: -30}], {
        rowFields: ['Year'], columnFields: ['Tech'], valueFields: [{field: 'Value', showAs: 'percentGrand'}],
        totals: {rows: 'grand', columns: 'grand'}
    });
    assert.equal(result.cells.length, 2);
    close(value(result, [2020], ['A']), 0.25);
    close(value(result, [2021], ['B']), 0.75);
    close(value(result, [], []), 1);
});

test('legacy percentage views and their current-format round trip transform totals', () => {
    const fields = [{field: 'Year', header: 'Year'}, {field: 'Value', header: 'Value', isMeasure: true}];
    const state = new ResultLayoutState(fields);
    state.apply({
        fields: [{binding: 'Year', key: 'Year'}, {binding: 'Value', key: 'Value', aggregate: 1, showAs: 5, format: 'p2'}],
        rowFields: {items: ['Year']}, columnFields: {items: []}, valueFields: {items: ['Value']},
        showRowTotals: 1, showColumnTotals: 0
    });
    const restored = new ResultLayoutState(fields);
    restored.apply(JSON.stringify(state.definition()));
    for (const layout of [state, restored]) {
        const result = A.aggregate([{Year: 2020, Value: 10}, {Year: 2021, Value: 30}], layout.configuration());
        close(value(result, [2020]), 0.25);
        close(value(result, [2021]), 0.75);
        close(value(result, []), 1);
        assert.equal(result.valueFields[0].format, 'p2');
    }
});
