// Result data shaping for the OG-Core Results page: the rows, columns and chart
// options each Explore view and OG-Core table shows, built from the report payload
// (/ogc/getResultsReport) and the runs' raw outputs. Pure functions with no DOM
// or network access: the controller loads data and draws what these return.

import * as V from "./OGResultsView.js";
import { escapeHtml as esc } from "../../Classes/Html.Class.js";

const EXPLORE_PATH_YEARS = 100;
const RATE_ROW = /interest rate/i;

// OG-Core's own analysis tables, in the order they are offered. Tables that build
// for every run come first, so the default never opens on an error.
export const OG_TABLES = [
    {key: 'macro_ss', label: 'Macro (long run)', path: 'getMacroTableSS', needs: 'compare'},
    {key: 'ineq', label: 'Inequality', path: 'getIneqTable'},
    {key: 'gini', label: 'Gini', path: 'getGiniTable'},
    {key: 'wealth', label: 'Wealth moments', path: 'getWealthMomentsTable', baselineOnly: true},
    {key: 'macro', label: 'Macro (10 years)', path: 'getMacroTable', needs: 'transition', options: {num_years: 10, include_SS: true}},
    {key: 'revenue', label: 'Revenue decomposition', path: 'getRevenueDecomposition', needs: 'compare-transition'}
];

// OG-Core table cells can carry LaTeX; keep the words, drop the markup.
export function plainTableText(value){
    while (Array.isArray(value) && value.length == 1) value = value[0];
    if (Array.isArray(value)) return value.map(plainTableText).join(', ');
    if (typeof value != 'string') return value;
    return value
        .replace(/\s*\(\s*\$[^$]+\$\s*\)/g, '')
        .replace(/\$([^$]+)\$/g, (_, expr) => expr.replace(/\\(?:mathrm|text|tilde|hat|bar)\s*\{([^{}]+)\}/g, '$1')
            .replace(/_\{([^{}]+)\}/g, ' $1').replace(/[{}\\^]/g, ''))
        .replace(/\s+/g, ' ').trim();
}

// OG-Core's long-run macro table gives one "% Change (or pp diff)" column that is
// a relative percent change for every row, including interest rates. Rates are
// shown in percentage points everywhere else on this page, so the same
// variable must not read differently here: rate rows are recomputed as a
// percentage-point change and every row states its unit.
export function macroLongRunRows(rows){
    return rows.map(row => {
        let name = plainTableText(row.Variable);
        let base = row.Baseline, reform = row.Reform;
        let rate = RATE_ROW.test(String(name)) && V.finite(base) && V.finite(reform);
        return {
            Variable: row.Variable,
            Baseline: rate ? base * 100 : base,
            Reform: rate ? reform * 100 : reform,
            Change: rate ? (reform - base) * 100 : row['% Change (or pp diff)'],
            Unit: rate ? 'percent; change in percentage points' : 'model units; change in percent'
        };
    });
}

export function singleSummaryRows(report){
    let rows = Object.fromEntries(report.summary.concat(report.macro, report.prices, report.fiscal).map(row => [row.name, row]));
    let out = [];
    let ratio = (name, label) => {
        if (!rows[name] || !rows.Y || !V.finite(rows.Y.baseline) || !rows.Y.baseline) return;
        out.push({short: label, baseline: rows[name].baseline / rows.Y.baseline * 100, value_unit: '% of GDP', negative_baseline: false});
    };
    if (rows.r) out.push(rows.r);
    ratio('C', 'Consumption');
    ratio('I', 'Investment');
    if (rows.K && rows.Y && rows.Y.baseline) out.push({short: 'Capital / output', baseline: rows.K.baseline / rows.Y.baseline, value_unit: 'ratio', negative_baseline: false});
    ['D', 'total_tax_revenue', 'G', 'total_government_outlays'].forEach(name => { if (rows[name]) out.push(rows[name]); });
    return out;
}

export function exploreShape(report, name){
    let entry = report.catalog[name] || {};
    let hasPath = report.analysis == 'transition';
    let pathable = hasPath && entry.dims == 'scalar';
    return {entry, pathable, household: entry.dims == 'age_group', kind: entry.kind};
}

// ── OG-Core tables ───────────────────────────────────────────────────────
export function tableAvailable(report, spec){
    let compare = report.mode == 'compare';
    if (spec.needs == 'compare' && !compare) return 'Needs a reform';
    if (spec.needs == 'transition' && report.analysis != 'transition') return 'Needs transition-path runs';
    if (spec.needs == 'compare-transition' && (!compare || report.analysis != 'transition')) return 'Needs a reform solved with the transition path';
    return '';
}

export function exploreLong(report, ssData, ex){
    let compare = report.mode == 'compare';
    let entry = report.catalog[ex.name];
    let base = ssData.baseline, reform = ssData.reform;
    let period = V.LONG_RUN;
    let kind = entry.kind == 'diagnostic' ? 'level' : entry.kind;
    let showChange = compare && ex.show == 'change' && entry.kind != 'diagnostic';
    let num = (name, run) => run ? V.scalar(run[name]) : null;
    if (entry.dims == 'scalar'){
        let cmp = V.compareValues(kind, num(ex.name, base), num(ex.name, reform), num('Y', base), num('Y', reform));
        let note = compare && V.finite(cmp.change)
            ? `Change: <b>${esc(V.formatChange(cmp.change, cmp.change_unit))}</b>${cmp.negative_baseline ? ' · <span class="ogc-rs-flag">negative baseline</span>' : ''}` : '';
        if (kind == 'level' && !compare) note = 'Model units: compare levels across scenarios rather than across countries.';
        let row = {variable: entry.label, baseline: cmp.baseline, reform: cmp.reform, change: cmp.change, unit: cmp.value_unit, change_unit: cmp.change_unit};
        let columns = [{title: 'Variable', field: 'variable', minWidth: 200},
            {title: compare ? 'Baseline' : 'Value', field: 'baseline', hozAlign: 'right', formatter: c => V.formatValue(c.getValue(), row.unit)}];
        if (compare){
            columns.push({title: 'Reform', field: 'reform', hozAlign: 'right', formatter: c => V.formatValue(c.getValue(), row.unit)});
            columns.push({title: 'Change', field: 'change', hozAlign: 'right', formatter: c => V.formatChange(c.getValue(), row.change_unit)});
        }
        columns.push({title: 'Unit', field: 'unit', formatter: c => V.valueUnitLabel(c.getValue())});
        return {title: `${entry.label}: long run`, period, note,
            chart: V.scenarioBars(entry.label, cmp.baseline, compare ? cmp.reform : null, cmp.value_unit),
            table: {data: [row], columns}};
    }
    if (entry.dims == 'age_group' && report.meta.weights && report.meta.weights.baseline){
        return exploreHousehold(report, ssData, ex, entry, kind, showChange, period);
    }
    if (entry.dims == 'group' && report.meta.group_labels){
        let groups = report.meta.group_labels;
        let bv = (base[ex.name] || []).map(V.scalar);
        let rv = reform ? (reform[ex.name] || []).map(V.scalar) : [];
        let items = groups.map((g, j) => showChange ? V.compareValues(kind, bv[j], rv[j]) : {change: kind == 'rate' ? bv[j] * 100 : bv[j]});
        let unit = showChange ? ((items.find(i => i.change_unit) || {}).change_unit || '%') : (kind == 'rate' ? '%' : 'model units');
        let data = groups.map((g, j) => ({group: g, baseline: bv[j], reform: rv[j], value: items[j].change}));
        return {title: `${entry.label} by lifetime income group`, period,
            chart: V.groupBars(groups, items, unit, entry.label, !showChange),
            table: {data, columns: [{title: 'Income group', field: 'group'}, {title: 'Baseline', field: 'baseline', hozAlign: 'right', formatter: c => V.formatNumber(c.getValue())}]
                .concat(compare ? [{title: 'Reform', field: 'reform', hozAlign: 'right', formatter: c => V.formatNumber(c.getValue())}] : [])
                .concat(showChange ? [{title: 'Change', field: 'value', hozAlign: 'right', formatter: c => V.formatChange(c.getValue(), unit)}] : [])}};
    }
    // any other shape: an indexed table, honestly labelled
    let rows = [];
    let walk = (b, r, path) => {
        if (Array.isArray(b) || Array.isArray(r)){
            let n = Math.max(Array.isArray(b) ? b.length : 0, Array.isArray(r) ? r.length : 0);
            for (let i = 0; i < n; i++) walk(Array.isArray(b) ? b[i] : null, Array.isArray(r) ? r[i] : null, path.concat(i + 1));
            return;
        }
        rows.push({index: path.join(', '), baseline: b, reform: r});
    };
    walk(base[ex.name], reform ? reform[ex.name] : null, []);
    return {title: `${entry.label}: long run`, period,
        note: 'This output has no age or income-group labels, so its values are listed by position.',
        chart: null,
        table: {data: rows, columns: [{title: 'Index', field: 'index'}, {title: 'Baseline', field: 'baseline', hozAlign: 'right', formatter: c => V.formatNumber(c.getValue())}]
            .concat(compare ? [{title: 'Reform', field: 'reform', hozAlign: 'right', formatter: c => V.formatNumber(c.getValue())}] : [])}};
}

export function exploreHousehold(report, ssData, ex, entry, kind, showChange, period){
    let compare = report.mode == 'compare';
    let meta = report.meta;
    let S = meta.S, J = meta.J, ages = meta.ages, groups = meta.group_labels;
    let bm = V.ageGroupMatrix(ssData.baseline[ex.name], S, J);
    let rm = compare ? V.ageGroupMatrix(ssData.reform[ex.name], S, J) : null;
    if (!bm || (compare && !rm)){
        return {title: entry.label, period, note: 'These values do not match the run’s age and income-group dimensions.', chart: null, table: {data: [], columns: []}};
    }
    let scale = kind == 'rate' ? 100 : 1;
    let valueUnit = kind == 'rate' ? '%' : 'model units';
    let bp = V.weightedProfiles(bm, meta.weights.baseline);
    let rp = rm ? V.weightedProfiles(rm, meta.weights.reform || meta.weights.baseline) : null;
    if (ex.breakdown == 'avg'){
        if (showChange){
            let items = ages.map((a, s) => V.compareValues(kind, bp.byAge[s], rp.byAge[s]));
            let unit = (items.find(i => i.change_unit) || {}).change_unit || '%';
            let data = items.map(i => i.change);
            return {title: `Change in ${entry.label.toLowerCase()} by age (population-weighted average)`, period,
                chart: V.lifecycleChart(ages, [{name: 'Change', data, color: V.COLORS.reform}], unit, entry.label),
                table: ageTable(ages, [{title: 'Change', values: data, fmt: v => V.formatChange(v, unit)}])};
        }
        let lines = [{name: compare ? 'Baseline' : entry.short, data: bp.byAge.map(v => v * scale), color: V.COLORS.baseline}];
        if (rp) lines.push({name: 'Reform', data: rp.byAge.map(v => v * scale), color: V.COLORS.reform, dashed: true});
        return {title: `${entry.label} by age (population-weighted average)`, period,
            chart: V.lifecycleChart(ages, lines, valueUnit, entry.label),
            table: ageTable(ages, lines.map(l => ({title: l.name, values: l.data, fmt: v => V.formatValue(v, valueUnit)})))};
    }
    if (ex.breakdown == 'groups'){
        let items = groups.map((g, j) => showChange ? V.compareValues(kind, bp.byGroup[j], rp.byGroup[j]) : {change: bp.byGroup[j] * scale});
        let unit = showChange ? ((items.find(i => i.change_unit) || {}).change_unit || '%') : valueUnit;
        let data = groups.map((g, j) => ({group: g, baseline: bp.byGroup[j] * scale, reform: rp ? rp.byGroup[j] * scale : null, change: showChange ? items[j].change : null}));
        let columns = [{title: 'Income group', field: 'group'}, {title: compare ? 'Baseline' : 'Average', field: 'baseline', hozAlign: 'right', formatter: c => V.formatValue(c.getValue(), valueUnit)}];
        if (compare) columns.push({title: 'Reform', field: 'reform', hozAlign: 'right', formatter: c => V.formatValue(c.getValue(), valueUnit)});
        if (showChange) columns.push({title: 'Change', field: 'change', hozAlign: 'right', formatter: c => V.formatChange(c.getValue(), unit)});
        return {title: showChange ? `Change in ${entry.label.toLowerCase()} by lifetime income group` : `${entry.label} by lifetime income group (${compare ? 'baseline' : 'average'})`, period,
            chart: V.groupBars(groups, items, unit, entry.label, !showChange), table: {data, columns}};
    }
    // age x income grid
    let grid, unit, title;
    if (showChange){
        let cells = bm.map((row, s) => row.map((b, j) => V.compareValues(kind, b, rm[s][j])));
        unit = (cells.flat().find(c => c.change_unit) || {}).change_unit || '%';
        grid = cells.map(row => row.map(c => c.change));
        title = `Change in ${entry.label.toLowerCase()} by age and lifetime income group`;
    }else{
        let source = compare && ex.scenario == 'reform' ? rm : bm;
        grid = source.map(row => row.map(v => v * scale));
        unit = valueUnit;
        title = `${entry.label} by age and lifetime income group${compare ? ` (${ex.scenario})` : ''}`;
    }
    let heat = grid.map(row => row.slice());
    let columns = [{title: 'Age', field: 'age', frozen: true}].concat(groups.map((g, j) => ({title: g, field: 'g' + j, hozAlign: 'right',
        formatter: c => showChange ? V.formatChange(c.getValue(), unit) : V.formatValue(c.getValue(), unit)})));
    let data = ages.map((a, s) => Object.assign({age: a}, Object.fromEntries(groups.map((g, j) => ['g' + j, grid[s][j]]))));
    return {title, period, chart: V.heatmap(ages, groups, heat, unit, showChange, title), table: {data, columns}};
}

export function ageTable(ages, series){
    let data = ages.map((a, s) => Object.assign({age: a}, Object.fromEntries(series.map((item, i) => ['v' + i, item.values[s]]))));
    let columns = [{title: 'Age', field: 'age'}].concat(series.map((item, i) => ({title: item.title, field: 'v' + i, hozAlign: 'right', formatter: c => item.fmt(c.getValue())})));
    return {data, columns};
}

export function explorePath(report, ssData, ex, base, reform){
    let compare = report.mode == 'compare';
    let entry = report.catalog[ex.name];
    let kind = entry.kind == 'diagnostic' ? 'level' : entry.kind;
    let count = Math.min(EXPLORE_PATH_YEARS, report.meta.T || EXPLORE_PATH_YEARS, (base[ex.name] || []).length);
    let years = Array.from({length: count}, (_, t) => report.meta.start_year + t);
    let at = (run, name, t) => run && Array.isArray(run[name]) ? V.scalar(run[name][t]) : null;
    let points = years.map((y, t) => V.compareValues(kind, at(base, ex.name, t), at(reform, ex.name, t), at(base, 'Y', t), at(reform, 'Y', t)));
    let ss = ssData;
    let steady = V.compareValues(kind, V.scalar(ss.baseline[ex.name]), ss.reform ? V.scalar(ss.reform[ex.name]) : null, V.scalar(ss.baseline.Y), ss.reform ? V.scalar(ss.reform.Y) : null);
    let series = {label: entry.label, short: entry.short, kind, value_unit: steady.value_unit, change_unit: steady.change_unit,
        baseline: points.map(p => p.baseline), reform: compare ? points.map(p => p.reform) : null,
        change: compare ? points.map(p => p.change) : null, steady};
    let showChange = compare && ex.show == 'change';
    let window = 10;
    let chart = showChange ? V.pathChart(years, series, window, 'compare') : V.scenarioPathChart(years, series, window, entry.label);
    let period = `Transition path, ${years[0]}–${years[years.length - 1]}`;
    // the table reads horizontally: one row per series, years across
    let rowsSpec = showChange ? [['Change', series.change, v => V.formatChange(v, series.change_unit)]]
        : [['Baseline', series.baseline, v => V.formatValue(v, series.value_unit)]].concat(compare ? [['Reform', series.reform, v => V.formatValue(v, series.value_unit)]] : []);
    let data = rowsSpec.map(([name, values]) => Object.assign({series: name, long: showChange ? steady.change : (name == 'Reform' ? steady.reform : steady.baseline)},
        Object.fromEntries(years.map((y, t) => ['y' + y, values[t]]))));
    let fmt = rowsSpec[0][2];
    let columns = [{title: '', field: 'series', frozen: true, minWidth: 90}]
        .concat(years.map(y => ({title: String(y), field: 'y' + y, hozAlign: 'right', headerSort: false, formatter: c => fmt(c.getValue())})))
        .concat([{title: 'Long run', field: 'long', hozAlign: 'right', headerSort: false, formatter: c => fmt(c.getValue()), cssClass: 'ogc-rs-longcol'}]);
    let note = series.negative_baseline || steady.negative_baseline ? '<span class="ogc-rs-flag">negative baseline</span> The baseline is negative, so the difference is shown instead of a percent change.' : '';
    return {title: `${entry.label} over the transition path`, period, note, chart, table: {data, columns}};
}
