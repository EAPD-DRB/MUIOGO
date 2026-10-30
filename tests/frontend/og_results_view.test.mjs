import assert from 'node:assert/strict';
import {test} from 'node:test';
import * as V from '../../WebAPP/App/Model/OGResultsView.js';

const close = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-9, `${actual} != ${expected}`);

test('rates are compared in percentage points, not relative change', () => {
    const out = V.compareValues('rate', 0.07, 0.075);
    close(out.change, 0.5);
    assert.equal(out.change_unit, 'pp');
    assert.equal(V.formatChange(out.change, out.change_unit), '+0.50 pp');
});

test('fiscal values are shares of each run GDP', () => {
    const out = V.compareValues('fiscal', 0.6, 0.66, 2, 2);
    close(out.baseline, 30);
    close(out.change, 3);
    assert.equal(V.formatChange(out.change, out.change_unit), '+3.00 pp of GDP');
});

test('a negative baseline never yields a percent change', () => {
    const out = V.compareValues('level', -10, -5);
    assert.equal(out.negative_baseline, true);
    assert.equal(out.change_unit, 'difference');
    close(out.change, 5);
});

test('small changes keep their precision instead of reading +0.00%', () => {
    assert.equal(V.formatChange(0.0042, '%'), '+0.0042%');
    assert.equal(V.formatChange(-1.234, '%'), '−1.23%');
    assert.equal(V.formatChange(0, '%'), '0.00%');
});

test('weighted profiles match the backend hand calculation', () => {
    const weights = [[0.1, 0.3], [0.15, 0.45]];
    const {byAge, byGroup, overall} = V.weightedProfiles([[1, 3], [5, 7]], weights);
    close(byAge[0], (0.1 * 1 + 0.3 * 3) / 0.4);
    close(byGroup[1], (0.3 * 3 + 0.45 * 7) / 0.75);
    close(overall, 0.1 + 0.9 + 0.75 + 3.15);
});

test('policy changes compare effective values against calibration defaults', () => {
    const schema = {cit_rate: {title: 'Corporate income tax rate', default: [[0.25]]}, frisch: {default: 0.4}};
    const changes = V.policyChanges({}, {cit_rate: [[0.2]], frisch: 0.4}, schema);
    assert.deepEqual(changes.map(c => c.name), ['cit_rate']);
    assert.equal(changes[0].label, 'Corporate income tax rate');
    assert.equal(V.policyChanges({frisch: 0.4}, {}, schema).length, 0);
});

test('the selection round-trips through the URL', () => {
    const sel = {casename: 'Tax case', base: 'Baseline 1', reform: 'Cut & keep', tab: 'explore'};
    const hash = V.selectionHash(sel);
    assert.ok(hash.startsWith('#/OGResults?'));
    assert.deepEqual(V.parseSelection(hash), sel);
    assert.equal(V.parseSelection('#/OGResults'), null);
    assert.equal(V.parseSelection(V.selectionHash({casename: 'c', base: 'b'})).reform, null);
});

test('diverging bars are sorted, sign-coloured and carry no legend', () => {
    const option = V.divergingBars([
        {label: 'Labor', value: -0.15}, {label: 'Capital', value: 1.2}, {label: 'GDP', value: 0.6}
    ], '%', 'test');
    assert.deepEqual(option.yAxis.data, ['Capital', 'GDP', 'Labor']);
    assert.equal(option.legend, undefined);
    assert.equal(option.series[0].data[2].itemStyle.color, V.COLORS.down);
    assert.ok(option.xAxis.min < 0 && option.xAxis.max > 0 && option.xAxis.min == -option.xAxis.max);
});

test('path charts mark the budget window and the long run', () => {
    const years = [2026, 2027, 2028, 2029];
    const series = {label: 'GDP', change: [0.1, 0.2, 0.3, 0.35], baseline: [1, 1, 1, 1], change_unit: '%', value_unit: 'model units',
        steady: {change: 0.4, baseline: 1}};
    const option = V.pathChart(years, series, 2, 'compare');
    assert.deepEqual(option.series[0].markArea.data[0].map(p => p.xAxis), ['2026', '2027']);
    assert.equal(option.series[0].markLine.data[0].yAxis, 0.4);
});

test('the all-groups lifecycle chart labels each line directly', () => {
    const lines = ['0-25%', '25-50%', 'Top 1%'].map((name, j) => ({name, data: [j, j + 1], color: V.GROUP_COLORS[j]}));
    const option = V.lifecycleChart([20, 21], lines, 'model units', 'test');
    assert.equal(option.legend, undefined);
    assert.equal(option.series[2].endLabel.formatter, 'Top 1%');
});
