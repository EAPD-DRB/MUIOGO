// Pure helpers for the OG-Core Results page: number and unit formatting, the
// comparison rules shared with the backend report (API/Classes/OGCore/OGReport.py),
// parameter-change detection, URL state, and ECharts option builders. No DOM access,
// so the page controller stays thin and these rules are unit-tested in node.

export const COLORS = {
    up: '#e0761b', down: '#3c73a8', flat: '#9aa0ab',
    baseline: '#3a3f51', reform: '#f58220', grid: '#eceef2', axis: '#8a8f9c', text: '#3a3f51',
    window: 'rgba(245,130,32,0.07)'
};
// Lower lifetime-income groups in blues, upper groups in oranges: the order stays
// readable and the colours carry meaning without a legend lookup.
export const GROUP_COLORS = ['#9bbad6', '#6f9cc6', '#4a7fb3', '#2f6396', '#f3b27a', '#e8873a', '#b45a12', '#7a3b0b'];

const EPS = 1e-12;
// Below this a change is solver noise, not an effect: it reads as zero.
export const NOISE = 1e-6;

// ── numbers ─────────────────────────────────────────────────────────────────
export function finite(value){
    return typeof value == 'number' && Number.isFinite(value);
}

export function formatNumber(value, digits = 4){
    if (!finite(value)) return '—';
    const abs = Math.abs(value);
    if (abs === 0) return '0';
    if (abs >= 1e6 || abs < 1e-4) return value.toExponential(2);
    if (abs >= 1000) return value.toLocaleString('en-US', {maximumFractionDigits: 0});
    return Number(value.toPrecision(digits)).toLocaleString('en-US', {maximumFractionDigits: 6});
}

export function formatValue(value, unit){
    if (!finite(value)) return '—';
    if (unit == '%') return `${value.toFixed(2)}%`;
    if (unit == '% of GDP') return `${value.toFixed(1)}% of GDP`;
    return formatNumber(value);
}

// Changes keep enough precision to be honest: a tiny change reads as "+0.0042%",
// never as a misleading "+0.00%".
export function formatChange(change, unit){
    if (!finite(change)) return 'n/a';
    if (Math.abs(change) < NOISE) change = 0;
    const abs = Math.abs(change);
    const sign = change > 0 ? '+' : (change < 0 ? '−' : '');
    let digits;
    if (abs === 0) digits = '0.00';
    else if (abs < 0.01) digits = Number(abs.toPrecision(2)).toString();
    else digits = abs.toFixed(abs >= 100 ? 0 : 2);
    if (unit == '%') return `${sign}${digits}%`;
    if (unit == 'pp') return `${sign}${digits} pp`;
    if (unit == 'pp of GDP') return `${sign}${digits} pp of GDP`;
    if (unit == 'difference') return `${sign}${formatNumber(abs)} (difference)`;
    return `${sign}${digits}`;
}

export function unitSuffix(unit){
    return unit == '%' ? '%' : unit == 'pp' ? ' pp' : unit == 'pp of GDP' ? ' pp' : unit == '% of GDP' ? '%' : '';
}

export function changeTone(change){
    if (!finite(change) || Math.abs(change) < NOISE) return 'flat';
    return change > 0 ? 'up' : 'down';
}

export function changeUnitLabel(unit){
    return {
        '%': 'Percent change', 'pp': 'Percentage-point change',
        'pp of GDP': 'Change in share of GDP (percentage points)', 'difference': 'Difference (model units)'
    }[unit] || 'Change';
}

export function valueUnitLabel(unit){
    return {'%': 'Percent', '% of GDP': 'Share of GDP (%)', 'model units': 'Model units', 'ratio': 'Ratio'}[unit] || '';
}

// ── the comparison rules (mirror OGReport.compare) ──────────────────────────
function share(value, gdp){
    return finite(value) && finite(gdp) && gdp !== 0 ? value / gdp * 100 : null;
}

export function compareValues(kind, base, reform, baseGdp, reformGdp){
    const out = {baseline: null, reform: null, change: null, change_unit: null, value_unit: null, negative_baseline: false};
    const b = finite(base) ? base : null;
    const r = finite(reform) ? reform : null;
    if (kind == 'rate'){
        Object.assign(out, {value_unit: '%', change_unit: 'pp',
            baseline: b === null ? null : b * 100, reform: r === null ? null : r * 100});
        if (b !== null && r !== null) out.change = (r - b) * 100;
        return out;
    }
    if (kind == 'fiscal'){
        Object.assign(out, {value_unit: '% of GDP', change_unit: 'pp of GDP',
            baseline: share(b, baseGdp), reform: share(r, reformGdp), negative_baseline: b !== null && b < 0});
        if (out.baseline !== null && out.reform !== null) out.change = out.reform - out.baseline;
        return out;
    }
    Object.assign(out, {value_unit: 'model units', baseline: b, reform: r});
    if (b === null || r === null) return out;
    if (b > 0){
        out.change = (r / b - 1) * 100;
        out.change_unit = '%';
    }else{
        out.negative_baseline = b < 0;
        out.change = r - b;
        out.change_unit = 'difference';
    }
    return out;
}

// Population-weighted views of an S x J matrix, as OGReport.weighted_profiles.
export function weightedProfiles(matrix, weights){
    const byAge = weights.map((row, s) => {
        const mass = row.reduce((a, w) => a + w, 0);
        return mass ? row.reduce((a, w, j) => a + w * matrix[s][j], 0) / mass : null;
    });
    const byGroup = weights[0].map((_, j) => {
        let mass = 0, total = 0;
        weights.forEach((row, s) => { mass += row[j]; total += row[j] * matrix[s][j]; });
        return mass ? total / mass : null;
    });
    let overall = 0;
    weights.forEach((row, s) => row.forEach((w, j) => { overall += w * matrix[s][j]; }));
    return {byAge, byGroup, overall};
}

export function scalar(value){
    while (Array.isArray(value) && value.length == 1) value = value[0];
    return finite(value) ? value : null;
}

export function ageGroupMatrix(value, S, J){
    if (!Array.isArray(value) || value.length != S) return null;
    if (!value.every(row => Array.isArray(row) && row.length == J && row.every(finite))) return null;
    return value;
}

// ── time frame labels (every number states its period) ──────────────────────
export const LONG_RUN = 'Long run (steady state)';

export function windowLabel(years, window){
    if (!years || !years.length) return '';
    const end = years[Math.min(window, years.length) - 1];
    return `${years[0]}–${end}`;
}

// ── parameter changes between a baseline and a reform ───────────────────────
export function parameterEqual(left, right){
    while (Array.isArray(left) && left.length == 1) left = left[0];
    while (Array.isArray(right) && right.length == 1) right = right[0];
    if (left === right) return true;
    if (typeof left == 'number' && typeof right == 'number') return Math.abs(left - right) <= EPS * Math.max(1, Math.abs(left));
    if (Array.isArray(left) || Array.isArray(right)){
        if (!Array.isArray(left) || !Array.isArray(right) || left.length != right.length) return false;
        return left.every((item, index) => parameterEqual(item, right[index]));
    }
    if (left && right && typeof left == 'object' && typeof right == 'object'){
        const keys = Object.keys(left).sort();
        if (!parameterEqual(keys, Object.keys(right).sort())) return false;
        return keys.every(key => parameterEqual(left[key], right[key]));
    }
    return false;
}

export function policyChanges(baseParams, reformParams, schema){
    const names = new Set([...Object.keys(baseParams || {}), ...Object.keys(reformParams || {})]);
    const changes = [];
    names.forEach(name => {
        const spec = (schema || {})[name] || {};
        const base = name in (baseParams || {}) ? baseParams[name] : spec.default;
        const reform = name in (reformParams || {}) ? reformParams[name] : spec.default;
        if (!parameterEqual(base, reform)){
            const title = String(spec.title || '').trim();
            changes.push({name, label: title || name.replace(/_/g, ' '), base, reform});
        }
    });
    return changes.sort((a, b) => a.label.localeCompare(b.label));
}

export function describeParameter(value){
    while (Array.isArray(value) && value.length == 1) value = value[0];
    if (value === null || value === undefined) return '—';
    if (typeof value == 'number') return formatNumber(value);
    if (typeof value != 'object') return String(value);
    if (Array.isArray(value)){
        const flat = value.flat(Infinity);
        const numbers = flat.filter(finite);
        if (numbers.length == flat.length && numbers.length){
            const first = numbers[0], same = numbers.every(n => n === first);
            return same ? `${formatNumber(first)} (all ${numbers.length})` : `${numbers.length} values, ${formatNumber(Math.min(...numbers))} to ${formatNumber(Math.max(...numbers))}`;
        }
        return `${flat.length} values`;
    }
    return 'table';
}

// ── URL state ────────────────────────────────────────────────────────────────
export function parseSelection(hash){
    const query = String(hash || '').split('?')[1] || '';
    const params = new URLSearchParams(query);
    const casename = params.get('case'), base = params.get('base');
    if (!casename || !base) return null;
    return {casename, base, reform: params.get('reform') || null, tab: params.get('tab') || 'report'};
}

export function selectionHash(selection){
    if (!selection) return '#/OGResults';
    const params = new URLSearchParams({case: selection.casename, base: selection.base});
    if (selection.reform) params.set('reform', selection.reform);
    if (selection.tab && selection.tab != 'report') params.set('tab', selection.tab);
    return '#/OGResults?' + params.toString();
}

export function selectionKey(countryId, selection){
    return [countryId, selection.casename, selection.base, selection.reform || ''].join('␟');
}

// ── chart option builders ────────────────────────────────────────────────────
function base(description){
    return {
        animationDuration: 350,
        aria: {show: true, description: description || ''},
        textStyle: {fontFamily: '"Open Sans", Arial, sans-serif', color: COLORS.text, fontSize: 12},
        tooltip: {backgroundColor: '#20232d', borderWidth: 0, textStyle: {color: '#fff', fontSize: 12}, confine: true}
    };
}

function niceBound(values){
    const max = Math.max(0, ...values.filter(finite).map(Math.abs));
    if (max === 0) return 1;
    return max * 1.25;
}

// Sorted diverging bars: one series coloured by sign, labelled directly, no legend.
export function divergingBars(rows, unit, description){
    const items = rows.filter(row => finite(row.value)).sort((a, b) => b.value - a.value);
    const bound = niceBound(items.map(row => row.value));
    return Object.assign(base(description), {
        grid: {left: 12, right: 56, top: 8, bottom: 24, containLabel: true},
        tooltip: Object.assign(base().tooltip, {trigger: 'item', formatter: p => {
            const row = items[p.dataIndex];
            const detail = finite(row.baseline) ? `<br><span style="opacity:.75">Baseline ${formatValue(row.baseline, row.valueUnit)} → Reform ${formatValue(row.reform, row.valueUnit)}</span>` : '';
            const flag = row.negative ? '<br><span style="color:#f3b27a">Negative baseline</span>' : '';
            return `<b>${row.label}</b><br>${formatChange(row.value, unit)}${detail}${flag}`;
        }}),
        xAxis: {type: 'value', min: -bound, max: bound, splitNumber: 4,
            axisLabel: {color: COLORS.axis, formatter: v => formatAxis(v) + unitSuffix(unit)},
            splitLine: {lineStyle: {color: COLORS.grid}}},
        yAxis: {type: 'category', inverse: true, data: items.map(row => row.label),
            axisTick: {show: false}, axisLine: {show: false}, axisLabel: {color: COLORS.text, fontSize: 12}},
        series: [{
            type: 'bar', barMaxWidth: 18,
            data: items.map(row => ({value: row.value, itemStyle: {color: COLORS[changeTone(row.value)], borderRadius: 2}})),
            label: {show: true, position: 'right', color: COLORS.text, fontSize: 11, fontWeight: 600,
                formatter: p => formatChange(p.value, unit).replace(' of GDP', '')},
            markLine: {silent: true, symbol: 'none', label: {show: false}, lineStyle: {color: '#8a8f9c', width: 1}, data: [{xAxis: 0}]}
        }]
    });
}

export function formatAxis(value){
    const abs = Math.abs(value);
    if (abs === 0) return '0';
    if (abs >= 100) return value.toFixed(0);
    if (abs >= 1) return Number(value.toFixed(1)).toString();
    return Number(value.toPrecision(2)).toString();
}

// One small time-path chart: change (compare) or the level (single), with the
// budget window shaded and the long-run value marked.
export function pathChart(years, series, window, mode){
    const compare = mode == 'compare';
    const values = compare ? series.change : series.baseline;
    const unit = compare ? series.change_unit : series.value_unit;
    const steadyValue = compare ? series.steady.change : series.steady.baseline;
    const windowEnd = years[Math.min(window, years.length) - 1];
    const lines = [{
        type: 'line', name: compare ? 'Change' : 'Baseline', data: values, showSymbol: false, smooth: false,
        lineStyle: {width: 2, color: compare ? COLORS.reform : COLORS.baseline},
        itemStyle: {color: compare ? COLORS.reform : COLORS.baseline},
        markArea: {silent: true, itemStyle: {color: COLORS.window}, data: [[{xAxis: String(years[0])}, {xAxis: String(windowEnd)}]]},
        markLine: finite(steadyValue) ? {silent: true, symbol: 'none', lineStyle: {type: 'dashed', color: '#8a8f9c'},
            label: {formatter: 'Long run', color: COLORS.axis, fontSize: 10, position: 'insideEndTop'}, data: [{yAxis: steadyValue}]} : undefined
    }];
    const option = Object.assign(base(`${series.label} over the transition path`), {
        grid: {left: 6, right: 12, top: 14, bottom: 4, containLabel: true},
        tooltip: Object.assign(base().tooltip, {trigger: 'axis', valueFormatter: v => compare ? formatChange(v, unit) : formatValue(v, unit)}),
        xAxis: {type: 'category', data: years.map(String), boundaryGap: false,
            axisLabel: {color: COLORS.axis, fontSize: 10, interval: index => index % 10 == 0}, axisTick: {show: false},
            axisLine: {lineStyle: {color: '#d5d8de'}}},
        yAxis: {type: 'value', scale: !compare, splitNumber: 3,
            axisLabel: {color: COLORS.axis, fontSize: 10, formatter: v => formatAxis(v) + unitSuffix(unit)},
            splitLine: {lineStyle: {color: COLORS.grid}}},
        series: lines
    });
    if (compare){
        const bound = niceBound(values.concat([steadyValue]));
        option.yAxis.min = -bound;
        option.yAxis.max = bound;
    }
    return option;
}

// Baseline vs reform over the path in levels (used for shares of GDP).
export function scenarioPathChart(years, series, window, description){
    const unit = series.value_unit;
    const windowEnd = years[Math.min(window, years.length) - 1];
    const data = [{name: 'Baseline', data: series.baseline, color: COLORS.baseline, type: 'solid'}];
    if (series.reform) data.push({name: 'Reform', data: series.reform, color: COLORS.reform, type: 'dashed'});
    return Object.assign(base(description), {
        grid: {left: 6, right: 16, top: 30, bottom: 4, containLabel: true},
        legend: {top: 0, right: 0, icon: 'roundRect', itemWidth: 14, itemHeight: 3, textStyle: {color: COLORS.axis}},
        tooltip: Object.assign(base().tooltip, {trigger: 'axis', valueFormatter: v => formatValue(v, unit)}),
        xAxis: {type: 'category', data: years.map(String), boundaryGap: false,
            axisLabel: {color: COLORS.axis, interval: index => index % 5 == 0}, axisTick: {show: false}},
        yAxis: {type: 'value', scale: true, axisLabel: {color: COLORS.axis, formatter: v => formatAxis(v) + unitSuffix(unit)},
            splitLine: {lineStyle: {color: COLORS.grid}}},
        series: data.map((line, index) => ({
            type: 'line', name: line.name, data: line.data, showSymbol: false,
            lineStyle: {width: 2, color: line.color, type: line.type}, itemStyle: {color: line.color},
            markArea: index === 0 ? {silent: true, itemStyle: {color: COLORS.window}, data: [[{xAxis: String(years[0])}, {xAxis: String(windowEnd)}]]} : undefined
        }))
    });
}

// Lifecycle chart: lines over age with direct end labels.
export function lifecycleChart(ages, lines, unit, description){
    return Object.assign(base(description), {
        grid: {left: 8, right: lines.length > 2 ? 86 : 24, top: 34, bottom: 30, containLabel: true},
        legend: lines.length <= 2 ? {top: 0, right: 0, icon: 'roundRect', itemWidth: 14, itemHeight: 3, textStyle: {color: COLORS.axis}} : undefined,
        tooltip: Object.assign(base().tooltip, {trigger: 'axis', valueFormatter: v => formatValue(v, unit),
            axisPointer: {type: 'line'}}),
        xAxis: {type: 'category', data: ages.map(String), boundaryGap: false, name: 'Age', nameLocation: 'middle', nameGap: 24,
            nameTextStyle: {color: COLORS.axis}, axisLabel: {color: COLORS.axis, interval: index => (ages[index] % 10) == 0},
            axisTick: {show: false}},
        yAxis: {type: 'value', scale: unit != '%', axisLabel: {color: COLORS.axis, formatter: v => formatAxis(v) + unitSuffix(unit)},
            splitLine: {lineStyle: {color: COLORS.grid}}},
        series: lines.map(line => ({
            type: 'line', name: line.name, data: line.data, showSymbol: false,
            lineStyle: {width: line.width || 2, color: line.color, type: line.dashed ? 'dashed' : 'solid'},
            itemStyle: {color: line.color},
            endLabel: lines.length > 2 ? {show: true, formatter: line.name, color: line.color, fontSize: 11, fontWeight: 600} : undefined,
            emphasis: {focus: 'series'}
        }))
    });
}

// Change by lifetime-income group: vertical bars in group order. ``neutral``
// draws levels (single run) in one colour, since sign colours would read as change.
export function groupBars(labels, changes, unit, description, neutral = false){
    const text = value => neutral ? formatValue(value, unit) : formatChange(value, unit);
    return Object.assign(base(description), {
        grid: {left: 8, right: 12, top: 26, bottom: 8, containLabel: true},
        tooltip: Object.assign(base().tooltip, {trigger: 'item', formatter: p => {
            const item = changes[p.dataIndex];
            const flag = item.negative_baseline ? '<br><span style="color:#f3b27a">Negative baseline: difference shown</span>' : '';
            return `<b>${labels[p.dataIndex]}</b><br>${neutral ? formatValue(item.change, unit) : formatChange(item.change, item.change_unit || unit)}${flag}`;
        }}),
        xAxis: {type: 'category', data: labels, axisTick: {show: false}, axisLabel: {color: COLORS.text, fontSize: 11, interval: 0},
            name: 'Lifetime income group', nameLocation: 'middle', nameGap: 28, nameTextStyle: {color: COLORS.axis}},
        yAxis: {type: 'value', axisLabel: {color: COLORS.axis, formatter: v => formatAxis(v) + unitSuffix(unit)},
            splitLine: {lineStyle: {color: COLORS.grid}}},
        series: [{
            type: 'bar', barMaxWidth: 34,
            data: changes.map(item => ({value: item.change, itemStyle: {color: neutral ? COLORS.baseline : COLORS[changeTone(item.change)], borderRadius: [2, 2, 0, 0]}})),
            label: {show: true, position: 'top', fontSize: 11, fontWeight: 600, color: COLORS.text,
                formatter: p => text(p.value)},
            markLine: {silent: true, symbol: 'none', label: {show: false}, lineStyle: {color: '#8a8f9c'}, data: [{yAxis: 0}]}
        }]
    });
}

// Baseline vs reform bars (single scalar) for Explore.
export function scenarioBars(label, baseline, reform, unit){
    const data = [{name: 'Baseline', value: baseline, color: COLORS.baseline}];
    if (finite(reform)) data.push({name: 'Reform', value: reform, color: COLORS.reform});
    return Object.assign(base(`${label}: baseline and reform`), {
        grid: {left: 8, right: 16, top: 16, bottom: 8, containLabel: true},
        tooltip: Object.assign(base().tooltip, {trigger: 'item', formatter: p => `<b>${p.name}</b><br>${formatValue(p.value, unit)}`}),
        xAxis: {type: 'category', data: data.map(item => item.name), axisTick: {show: false}},
        yAxis: {type: 'value', axisLabel: {color: COLORS.axis, formatter: v => formatAxis(v) + unitSuffix(unit)},
            splitLine: {lineStyle: {color: COLORS.grid}}},
        series: [{type: 'bar', barMaxWidth: 64,
            data: data.map(item => ({value: item.value, itemStyle: {color: item.color, borderRadius: [2, 2, 0, 0]}})),
            label: {show: true, position: 'top', fontWeight: 600, formatter: p => formatValue(p.value, unit)}}]
    });
}

// Age x group heatmap on a diverging scale centred on zero (change) or a
// sequential scale (levels).
export function heatmap(ages, groups, grid, unit, diverging, description){
    const data = [];
    const values = [];
    grid.forEach((row, s) => row.forEach((value, j) => {
        data.push([s, j, finite(value) ? value : null]);
        if (finite(value)) values.push(value);
    }));
    const min = Math.min(...values), max = Math.max(...values);
    const bound = Math.max(Math.abs(min), Math.abs(max)) || 1;
    return Object.assign(base(description), {
        grid: {left: 8, right: 16, top: 8, bottom: 64, containLabel: true},
        tooltip: Object.assign(base().tooltip, {trigger: 'item', formatter: p => `Age ${ages[p.value[0]]} · ${groups[p.value[1]]}<br><b>${diverging ? formatChange(p.value[2], unit) : formatValue(p.value[2], unit)}</b>`}),
        xAxis: {type: 'category', data: ages.map(String), name: 'Age', nameLocation: 'middle', nameGap: 22,
            axisLabel: {color: COLORS.axis, interval: index => ages[index] % 10 == 0}, axisTick: {show: false}, splitArea: {show: false}},
        yAxis: {type: 'category', data: groups, axisTick: {show: false}, axisLabel: {color: COLORS.text}},
        visualMap: {type: 'continuous', orient: 'horizontal', left: 'center', bottom: 0, itemHeight: 180, calculable: false,
            min: diverging ? -bound : min, max: diverging ? bound : max,
            inRange: {color: diverging ? ['#2f6396', '#f4f5f7', '#e0761b'] : ['#f4f5f7', '#9bbad6', '#2f6396']},
            text: diverging ? ['Higher than baseline', 'Lower than baseline'] : ['High', 'Low'], textStyle: {color: COLORS.axis},
            formatter: v => formatAxis(v) + unitSuffix(unit)},
        series: [{type: 'heatmap', data, progressive: 0, emphasis: {itemStyle: {borderColor: '#20232d', borderWidth: 1}}}]
    });
}
