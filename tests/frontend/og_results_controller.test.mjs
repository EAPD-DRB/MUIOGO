import assert from 'node:assert/strict';
import {test} from 'node:test';

// Minimal DOM/jQuery stand-ins: the Results controller builds HTML strings and
// chart options, which is what these tests inspect.
const storage = new Map();
globalThis.localStorage = {getItem: k => storage.get(k) || null, setItem: (k, v) => storage.set(k, v), removeItem: k => storage.delete(k)};
globalThis.document = {getElementById: () => ({})};
globalThis.window = {location: {hash: '#/OGResults'}};
globalThis.history = {replaceState: (a, b, hash) => { window.location.hash = hash; }};
const nodes = new Map();
const node = () => {
    const self = {content: ''};
    for (const name of ['show', 'hide', 'toggle', 'closest', 'find', 'first', 'after', 'remove', 'attr', 'each', 'removeClass', 'addClass', 'filter', 'prop']) self[name] = () => self;
    self.html = value => { if (value === undefined) return self.content; self.content = value; return self; };
    self.text = value => { self.content = value; return self; };
    self.empty = () => { self.content = ''; return self; };
    self.val = () => '';
    return self;
};
globalThis.$ = selector => {
    if (typeof selector != 'string') return node();
    if (!nodes.has(selector)) nodes.set(selector, node());
    return nodes.get(selector);
};
Object.assign($, {
    isArray: Array.isArray,
    each: (object, callback) => Object.entries(object || {}).forEach(([k, v]) => callback(Array.isArray(object) ? Number(k) : k, v)),
    grep: (array, fn) => array.filter(fn),
    map: (object, callback) => Object.entries(object).flatMap(([k, v]) => { const r = callback(v, k); return r == null ? [] : r; })
});

const {default: OGResults} = await import('../../WebAPP/App/Controller/OGResults.js');
const D = await import('../../WebAPP/App/Model/OGResultsData.js');
const charts = {};
OGResults.setChart = (id, option) => { charts[id] = option; };
OGResults.setGrid = () => {};
OGResults.workspace = {country_id: 'PHL'};
OGResults.cases = [{casename: 'Tax', country_id: 'PHL', runs: [
    {run_name: 'base', run_type: 'baseline', status: 'completed', reusable: true, time_path: true},
    {run_name: 'cut', run_type: 'reform', baseline_run: 'base', status: 'completed', reusable: true, time_path: true},
    {run_name: 'draft', run_type: 'reform', baseline_run: 'base', status: 'pending'}
]}];

const cmp = (baseline, reform, change, change_unit, value_unit, extra = {}) => Object.assign({baseline, reform, change, change_unit, value_unit, negative_baseline: false}, extra);
function report(mode = 'compare'){
    const compare = mode == 'compare';
    const row = (name, label, kind, c) => Object.assign({name, label, short: label, kind}, c);
    const years = Array.from({length: 12}, (_, t) => 2026 + t);
    const path = (label, kind, unit, valueUnit) => ({label, short: label, kind, value_unit: valueUnit, change_unit: unit,
        baseline: years.map(() => 1), reform: compare ? years.map(() => 1.01) : null, change: compare ? years.map(() => 1) : null,
        negative_baseline: false, steady: cmp(1, compare ? 1.01 : null, compare ? 1 : null, unit, valueUnit)});
    const hh = {label: 'Household consumption', short: 'Consumption', kind: 'level', value_unit: 'model units',
        by_age: {baseline: [1, 2, 3], reform: compare ? [1.1, 2.2, 3.3] : undefined},
        by_age_group: {baseline: [[1, 2, 3], [2, 3, 4]], reform: compare ? [[1.1, 2.2, 3.3], [2.2, 3.3, 4.4]] : undefined},
        by_group: {baseline: [2, 3], reform: compare ? [2.2, 3.3] : undefined},
        group_change: compare ? [cmp(2, 2.2, 10, '%', 'model units'), cmp(3, 3.3, 10, '%', 'model units')] : undefined,
        overall: cmp(2.5, compare ? 2.75 : null, compare ? 10 : null, compare ? '%' : null, 'model units')};
    return {
        mode, analysis: 'transition',
        meta: {complete: true, start_year: 2026, T: 12, S: 3, J: 2, ages: [20, 21, 22], group_labels: ['0-60%', 'Top 40%'],
            weights: {baseline: [[0.2, 0.1], [0.2, 0.1], [0.3, 0.1]], reform: compare ? [[0.2, 0.1], [0.2, 0.1], [0.3, 0.1]] : null}},
        catalog: {Y: {label: 'Gross domestic product', short: 'GDP', category: 'Output', kind: 'level', dims: 'scalar'},
            c: {label: 'Household consumption', short: 'Consumption', category: 'Households', kind: 'level', dims: 'age_group'}},
        summary: [row('Y', 'GDP', 'level', cmp(2, compare ? 2.02 : null, compare ? 1 : null, '%', 'model units')),
            row('r', 'Interest rate', 'rate', cmp(7, compare ? 7.5 : null, compare ? 0.5 : null, 'pp', '%')),
            row('G', 'Govt. consumption', 'fiscal', cmp(-5, compare ? -4 : null, compare ? 1 : null, 'pp of GDP', '% of GDP', {negative_baseline: true}))],
        macro: [row('Y', 'GDP', 'level', cmp(2, 2.02, 1, '%', 'model units'))],
        prices: [row('r', 'Interest rate', 'rate', cmp(7, 7.5, 0.5, 'pp', '%'))],
        fiscal: [row('G', 'Govt. consumption', 'fiscal', cmp(-5, -4, 1, 'pp of GDP', '% of GDP', {negative_baseline: true}))],
        diagnostics: {baseline: {converged: true, values: {euler_savings: 1e-13}}, reform: compare ? {converged: true, values: {euler_savings: 1e-13}} : null},
        transition: {years, budget_window: 10, series: {Y: path('GDP', 'level', '%', 'model units'), r: path('Interest rate', 'rate', 'pp', '%'),
            D: path('Debt', 'fiscal', 'pp of GDP', '% of GDP')}},
        households: {c: hh}, households_reason: null
    };
}

function show(rep, policy){
    OGResults.selection = {casename: 'Tax', base: 'base', reform: rep.mode == 'compare' ? 'cut' : null, tab: 'report'};
    OGResults.report = rep;
    OGResults.policy = policy;
    OGResults.hh = {name: 'c', view: 'avg', scenario: 'baseline', group: 0};
    OGResults.renderReport();
    return $('[data-rs-pane="report"]').content;
}

test('picker offers Compare only for a ready reform and hides unfinished ones behind a reason', () => {
    OGResults.renderTree();
    const tree = $('#ogcRsTree').content;
    assert.equal((tree.match(/data-rs-act="compare"[^>]*data-reform="cut"(?![^>]*disabled)/g) || []).length, 1);
    assert.match(tree, /data-reform="draft"[^>]*disabled/);
    assert.match(tree, /Not run yet/);
});

test('every report card states its time frame', () => {
    const html = show(report(), [{name: 'cit_rate', label: 'CIT rate', base: 0.25, reform: 0.2}]);
    const periods = [...html.matchAll(/ogc-rs-card-period">([^<]*)/g)].map(m => m[1]);
    assert.ok(periods.length > 0);
    assert.ok(periods.every(p => /Long run \(steady state\)|Transition path, 2026/.test(p)), periods.join(' | '));
    assert.match(html, /Long run \(steady state\) · reform compared with baseline/);
});

test('rates read in percentage points and negative fiscal baselines are flagged', () => {
    const html = show(report(), [{name: 'x', label: 'x', base: 1, reform: 2}]);
    assert.match(html, /\+0\.50 pp</);
    assert.match(html, /negative baseline/);
    assert.match(html, /Negative baseline: Govt\. consumption/);
});

test('an unchanged reform shows the guard instead of empty charts', () => {
    const html = show(report(), []);
    assert.match(html, /same parameters as its baseline/);
    assert.doesNotMatch(html, /ogc-rs-kpis/);
});

test('lifecycle defaults to the population average and never silently picks one group', () => {
    show(report(), [{name: 'x', label: 'x', base: 1, reform: 2}]);
    const lines = charts.rsLifecycle.series.map(s => s.name);
    assert.deepEqual(lines, ['Baseline', 'Reform']);
});

test('the all-groups view shows one scenario at a time with metadata labels', () => {
    show(report(), [{name: 'x', label: 'x', base: 1, reform: 2}]);
    OGResults.hh.view = 'groups';
    OGResults.hh.scenario = 'reform';
    OGResults.drawHouseholds();
    assert.deepEqual(charts.rsLifecycle.series.map(s => s.name), ['0-60%', 'Top 40%']);
    assert.deepEqual(charts.rsLifecycle.series[0].data, [1.1, 2.2, 3.3]);
    assert.deepEqual(charts.rsGroups.xAxis.data, ['0-60%', 'Top 40%']);
});

test('Explore uses the same group labels, ages and weights as the report', () => {
    OGResults.selection = {casename: 'Tax', base: 'base', reform: 'cut'};
    OGResults.report = report();
    OGResults.ssData = {baseline: {c: [[1, 2], [2, 3], [3, 4]]}, reform: {c: [[1.1, 2.2], [2.2, 3.3], [3.3, 4.4]]}};
    const groups = D.exploreLong(OGResults.report, OGResults.ssData, {name: 'c', period: 'long', show: 'change', breakdown: 'groups', view: 'chart'});
    assert.deepEqual(groups.chart.xAxis.data, ['0-60%', 'Top 40%']);
    groups.chart.series[0].data.forEach(item => assert.ok(Math.abs(item.value - 10) < 1e-9));
    const byAge = D.exploreLong(OGResults.report, OGResults.ssData, {name: 'c', period: 'long', show: 'levels', breakdown: 'avg', view: 'chart'});
    assert.deepEqual(byAge.chart.xAxis.data, ['20', '21', '22']);
    assert.equal(byAge.period, 'Long run (steady state)');
});

test('a single run shows ratios and levels without change arrows', () => {
    const html = show(report('single'), null);
    assert.doesNotMatch(html, /fa-arrow-up|fa-arrow-down/);
    assert.match(html, /7\.00%/);
});

test('OG-Core long-run table shows interest rates in percentage points, not relative change', () => {
    const rows = D.macroLongRunRows([
        {'% Change (or pp diff)': 0.2625, Baseline: 0.0708, Reform: 0.0710, Variable: 'Real interest rate ($r_t$)'},
        {'% Change (or pp diff)': 0.626, Baseline: 2.8766, Reform: 2.8946, Variable: 'GDP ($Y_t$)'}
    ]);
    const rate = rows[0], gdp = rows[1];
    assert.ok(Math.abs(rate.Change - 0.02) < 1e-9);
    assert.ok(Math.abs(rate.Baseline - 7.08) < 1e-9);
    assert.match(rate.Unit, /percentage points/);
    assert.equal(gdp.Change, 0.626);
    assert.match(gdp.Unit, /percent/);
});
