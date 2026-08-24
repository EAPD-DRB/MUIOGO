import { Ogc } from "../../Classes/Ogc.Class.js";
import { loadWorkspace } from "./OGCases.js";

const ECHARTS_URL = 'References/echarts/echarts-6.1.0.min.js';
const VIEW_KEY = 'osy-ogc-result-view';
const ORANGE = '#f58220';
const SLATE = '#3a3f51';
const BLUE = '#39769f';
const MUTED = '#8a8f9c';
const GRID = '#e8e9ed';

const CATALOG = {
    Y: { label: 'Gross domestic product', short: 'GDP', category: 'Macroeconomy' },
    C: { label: 'Aggregate consumption', short: 'Consumption', category: 'Macroeconomy' },
    K: { label: 'Capital stock', short: 'Capital', category: 'Macroeconomy' },
    L: { label: 'Aggregate labor', short: 'Labor', category: 'Macroeconomy' },
    I: { label: 'Investment', short: 'Investment', category: 'Macroeconomy' },
    I_total: { label: 'Total investment', category: 'Macroeconomy' },
    w: { label: 'Wage rate', short: 'Wage', category: 'Prices and returns' },
    r: { label: 'Real interest rate', short: 'Real interest', category: 'Prices and returns', rate: true },
    r_gov: { label: 'Government interest rate', category: 'Prices and returns', rate: true },
    r_p: { label: 'Household portfolio return', category: 'Prices and returns', rate: true },
    D: { label: 'Government debt', category: 'Public finance' },
    G: { label: 'Government consumption', category: 'Public finance' },
    TR: { label: 'Government transfers', category: 'Public finance' },
    total_tax_revenue: { label: 'Total tax revenue', short: 'Tax revenue', category: 'Public finance' },
    business_tax_revenue: { label: 'Business tax revenue', category: 'Public finance' },
    iit_payroll_tax_revenue: { label: 'Income and payroll tax revenue', category: 'Public finance' },
    iit_revenue: { label: 'Individual income tax revenue', category: 'Public finance' },
    payroll_tax_revenue: { label: 'Payroll tax revenue', category: 'Public finance' },
    bequest_tax_revenue: { label: 'Bequest tax revenue', category: 'Public finance' },
    wealth_tax_revenue: { label: 'Wealth tax revenue', category: 'Public finance' },
    cons_tax_revenue: { label: 'Consumption tax revenue', category: 'Public finance' },
    total_government_outlays: { label: 'Total government outlays', category: 'Public finance' },
    total_primary_government_outlays: { label: 'Primary government outlays', category: 'Public finance' },
    debt_service: { label: 'Debt service', category: 'Public finance' },
    new_borrowing: { label: 'New borrowing', category: 'Public finance', differenceOnly: true },
    c: { label: 'Household consumption', short: 'Consumption', category: 'Households' },
    n: { label: 'Household labor supply', short: 'Labor supply', category: 'Households' },
    b_s: { label: 'Household wealth', short: 'Wealth', category: 'Households' },
    b_sp1: { label: 'Savings carried to next age', short: 'Savings', category: 'Households' },
    before_tax_income: { label: 'Before-tax household income', short: 'Before-tax income', category: 'Households' },
    hh_net_taxes: { label: 'Household net taxes', category: 'Households', differenceOnly: true },
    etr: { label: 'Effective tax rate', category: 'Households', rate: true },
    mtrx: { label: 'Marginal tax rate on labor income', category: 'Households', rate: true },
    mtry: { label: 'Marginal tax rate on capital income', category: 'Households', rate: true },
    euler_savings: { label: 'Savings Euler error', category: 'Model diagnostics' },
    euler_labor_leisure: { label: 'Labor-leisure Euler error', category: 'Model diagnostics' },
    resource_constraint_error: { label: 'Resource constraint error', category: 'Model diagnostics' }
};

const PROFILE_VARS = ['c', 'n', 'b_s', 'before_tax_income'];
const DISTRIBUTION_VARS = ['c', 'n', 'b_s', 'before_tax_income'];
const FISCAL_VARS = [
    'total_tax_revenue', 'business_tax_revenue', 'iit_revenue',
    'cons_tax_revenue', 'G', 'total_primary_government_outlays'
];
let PAGE_ID = 0;

const esc = value => String(value == null ? '' : value).replace(/[&<>"']/g,
    ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));

function humanize(name){
    return String(name || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function info(name){
    if (CATALOG[name]) return CATALOG[name];
    let category = 'Other outputs';
    if (/tax|revenue|debt|borrowing|government|pension|\bG\b/.test(name)) category = 'Public finance';
    else if (/error|euler|constraint/.test(name)) category = 'Model diagnostics';
    else if (/^p_|^r$|^r_|^w$/.test(name)) category = 'Prices and returns';
    else if (/^c$|^n$|income|wealth|benefit|\bbq\b|\btr\b|\bubi\b/.test(name)) category = 'Households';
    else if (/^Y|^K|^L|^I|^C|^B/.test(name)) category = 'Macroeconomy';
    return { label: humanize(name), category: category };
}

function firstNumber(value){
    if (typeof value == 'number' && isFinite(value)) return value;
    if ($.isArray(value)){
        for (let i = 0; i < value.length; i++){
            let found = firstNumber(value[i]);
            if (found !== null) return found;
        }
    }
    return null;
}

function rank(value){
    let r = 0, current = value;
    while ($.isArray(current)){
        r++;
        current = current.length ? current[0] : null;
    }
    return r;
}

function dimensions(value){
    let dims = [], current = value;
    while ($.isArray(current)){
        dims.push(current.length);
        current = current.length ? current[0] : null;
    }
    return dims;
}

function routePath(){
    let path = String(window.location.hash || '').replace(/^#/, '').split('?')[0] || '/';
    return path.length > 1 ? path.replace(/\/+$/, '') : path;
}

function rawMatrix(value){
    let candidate = value;
    if (rank(candidate) == 3 && candidate.length == 1) candidate = candidate[0];
    return $.isArray(candidate) && candidate.length && $.isArray(candidate[0]) ? candidate : null;
}

function parameterArray(value){
    let candidate = value;
    while ($.isArray(candidate) && candidate.length == 1 && $.isArray(candidate[0])) candidate = candidate[0];
    return $.isArray(candidate) ? candidate : null;
}

function validWeights(value, count){
    let weights = parameterArray(value);
    if (!weights || !weights.length || (count && weights.length != count)) return null;
    let total = 0;
    for (let index = 0; index < weights.length; index++){
        let weight = Number(weights[index]);
        if (!isFinite(weight) || weight < 0) return null;
        total += weight;
    }
    return Math.abs(total - 1) < 0.001 ? weights : null;
}

function compatibleMatrices(base, reform){
    if (!base || !reform || base.length != reform.length) return false;
    for (let row = 0; row < base.length; row++){
        if (!$.isArray(base[row]) || !$.isArray(reform[row]) || base[row].length != reform[row].length) return false;
    }
    return true;
}

function ageGroupMatrix(value){
    let candidate = value;
    if (rank(candidate) == 3 && candidate.length == 1) candidate = candidate[0];
    if (!$.isArray(candidate) || !candidate.length || !$.isArray(candidate[0])) return null;
    let groupCount = OGResults.groups && OGResults.groups.length;
    if (groupCount && candidate[0].length == groupCount) return candidate;
    if (groupCount && candidate.length == groupCount){
        return candidate[0].map((_, col) => candidate.map(row => row[col]));
    }
    return null;
}

function shape(value){
    let dims = dimensions(value);
    if (!dims.length || (dims.length == 1 && dims[0] == 1)) return { kind: 'scalar', dims: [] };
    let matrix = ageGroupMatrix(value);
    if (matrix && OGResults.ages && matrix.length == OGResults.ages.length){
        return { kind: 'age_group', dims: [matrix.length, matrix[0].length] };
    }
    if (dims.length == 1 && OGResults.groups && dims[0] == OGResults.groups.length) return { kind: 'group', dims: dims };
    if (dims.length == 1) return { kind: 'vector', dims: dims };
    return { kind: 'matrix', dims: dims };
}

function pct(base, reform){
    if (typeof base != 'number' || typeof reform != 'number' || !isFinite(base) || !isFinite(reform) || Math.abs(base) < 1e-12) return null;
    return (reform / base - 1) * 100;
}

function diff(base, reform){
    if (typeof base != 'number' || typeof reform != 'number' || !isFinite(base) || !isFinite(reform)) return null;
    return reform - base;
}

function level(name, value){
    if (typeof value != 'number' || !isFinite(value)) return null;
    return info(name).rate ? value * 100 : value;
}

function measureValue(name, base, reform, measure){
    if (measure == 'levels') return level(name, reform);
    if (measure == 'pp'){
        let value = diff(base, reform);
        return value === null ? null : value * 100;
    }
    return measure == 'diff' ? diff(base, reform) : pct(base, reform);
}

function measureLabel(name, measure){
    if (measure == 'levels') return info(name).rate ? 'Rates (%)' : 'Levels';
    if (measure == 'pp') return 'Percentage-point difference';
    if (measure == 'diff') return 'Difference';
    return 'Percent change';
}

function measureSuffix(name, measure){
    if (measure == 'pct') return '%';
    if (measure == 'pp') return ' pp';
    if (measure == 'levels' && info(name).rate) return '%';
    return '';
}

function signed(value, suffix){
    if (value === null || value === undefined || !isFinite(value)) return 'n/a';
    return (value > 0 ? '+' : '') + value.toFixed(Math.abs(value) >= 10 ? 1 : 2) + (suffix || '');
}

function fmt(value){
    if (value === null || value === undefined || !isFinite(value)) return '—';
    let abs = Math.abs(value);
    if (abs && (abs >= 100000 || abs < 0.0001)) return value.toExponential(3);
    if (abs >= 1000) return value.toLocaleString(undefined, {maximumFractionDigits: 1});
    return value.toLocaleString(undefined, {maximumFractionDigits: abs >= 10 ? 2 : 4});
}

function plainMath(value){
    return String(value || '')
        .replace(/\\(?:tilde|hat|bar|vec)\s*\{([^{}]+)\}/g, '$1')
        .replace(/\\(?:mathrm|text)\s*\{([^{}]+)\}/g, '$1')
        .replace(/_\{([^{}]+)\}/g, ' ($1)')
        .replace(/\^\{([^{}]+)\}/g, '^$1')
        .replace(/_([A-Za-z0-9]+)/g, ' ($1)')
        .replace(/\\([A-Za-z]+)/g, '$1')
        .replace(/[{}]/g, '')
        .replace(/\s*,\s*/g, ', ')
        .replace(/\s+/g, ' ')
        .trim();
}

function resultTableText(value){
    let source = String(value == null ? '' : value);
    let cleaned = source
        .replace(/\s*\(\s*\$[^$]+\$\s*\)/g, '')
        .replace(/\s*,?\s*\$[^$]+\$\s*$/g, '')
        .replace(/\$([^$]+)\$/g, (_, expression) => plainMath(expression))
        .replace(/\s+,/g, ',')
        .replace(/\s+/g, ' ')
        .trim();
    return cleaned || plainMath(source.replace(/\$/g, ''));
}

function resultTableCell(value){
    while ($.isArray(value) && value.length == 1) value = value[0];
    if ($.isArray(value)) return $.map(value, resultTableCell).join(', ');
    return typeof value == 'string' ? resultTableText(value) : value;
}

function parameterEqual(left, right){
    while ($.isArray(left) && left.length == 1) left = left[0];
    while ($.isArray(right) && right.length == 1) right = right[0];
    if (left === right) return true;
    if (typeof left == 'number' && typeof right == 'number' && isNaN(left) && isNaN(right)) return true;
    if ($.isArray(left) || $.isArray(right)){
        if (!$.isArray(left) || !$.isArray(right) || left.length != right.length) return false;
        for (let index = 0; index < left.length; index++){
            if (!parameterEqual(left[index], right[index])) return false;
        }
        return true;
    }
    let leftObject = left && typeof left == 'object';
    let rightObject = right && typeof right == 'object';
    if (leftObject || rightObject){
        if (!leftObject || !rightObject) return false;
        let leftKeys = Object.keys(left).sort();
        let rightKeys = Object.keys(right).sort();
        if (!parameterEqual(leftKeys, rightKeys)) return false;
        for (let index = 0; index < leftKeys.length; index++){
            let key = leftKeys[index];
            if (!parameterEqual(left[key], right[key])) return false;
        }
        return true;
    }
    return false;
}

function robustHeatScale(values){
    let absolute = $.map(values, value => value === null || !isFinite(value) ? null : Math.abs(value)).sort((a, b) => a - b);
    if (!absolute.length) return { bound: 0.01, max: 0.01, clipped: false, cappedPercent: 0 };
    let max = absolute[absolute.length - 1];
    let bound = absolute[Math.floor((absolute.length - 1) * 0.95)];
    bound = Math.max(0.01, bound);
    let capped = $.grep(absolute, value => value > bound).length;
    return { bound: bound, max: max, clipped: capped > 0, cappedPercent: Math.round(capped / absolute.length * 100) };
}

function indexedPairs(base, reform, path, rows){
    let baseArray = $.isArray(base), reformArray = $.isArray(reform);
    if (baseArray || reformArray){
        let length = Math.max(baseArray ? base.length : 0, reformArray ? reform.length : 0);
        for (let index = 0; index < length; index++){
            indexedPairs(baseArray ? base[index] : null, reformArray ? reform[index] : null, path.concat(index + 1), rows);
        }
        return;
    }
    rows.push({ dimension: path.join(', '), baseline: base, reform: reform });
}

function axisLabel(value){
    if (value === 0) return '0';
    if (Math.abs(value) >= 10) return value.toFixed(0);
    return value.toFixed(1);
}

function chartBase(description){
    return {
        animationDuration: 450,
        aria: { show: true, description: description || '' },
        textStyle: { fontFamily: 'Open Sans, Arial, sans-serif', color: SLATE },
        tooltip: { trigger: 'axis', backgroundColor: '#20232d', borderWidth: 0, textStyle: { color: '#fff', fontSize: 12 } },
        grid: { left: 22, right: 28, top: 20, bottom: 30, containLabel: true }
    };
}

function comparisonBar(labels, values, description){
    let max = Math.max(0.5, ...values.filter(v => v !== null).map(v => Math.abs(v))) * 1.18;
    return $.extend(true, chartBase(description), {
        grid: { left: 40, right: 52, top: 10, bottom: 26, containLabel: true },
        xAxis: {
            type: 'value', min: -max, max: max,
            axisLine: { lineStyle: { color: '#ccd0d8' } }, axisTick: { show: false },
            splitLine: { lineStyle: { color: GRID } }, axisLabel: { color: MUTED, formatter: v => axisLabel(v) + '%' }
        },
        yAxis: { type: 'category', data: labels, inverse: true, axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: SLATE, fontWeight: 600 } },
        series: [{
            type: 'bar', data: values.map(v => {
                let placeInside = v < 0 && Math.abs(v) / max > 0.18;
                return {
                    value: v,
                    itemStyle: { color: v >= 0 ? ORANGE : BLUE },
                    label: {
                        position: v >= 0 ? 'right' : (placeInside ? 'insideLeft' : 'left'),
                        color: placeInside ? '#fff' : SLATE,
                        distance: 7
                    }
                };
            }),
            barMaxWidth: 17,
            label: { show: true, position: 'outside', color: SLATE, fontWeight: 700, formatter: p => signed(p.value, '%') },
            markLine: { silent: true, symbol: 'none', lineStyle: { color: '#9ba1ad', width: 1.2 }, label: { show: false }, data: [{ xAxis: 0 }] }
        }]
    });
}

export default class OGResults {
    static onLoad(){
        PAGE_ID++;
        OGResults.pageID = PAGE_ID;
        OGResults.disposeCharts();
        $(window).off('.ogresults');
        $(document).off('.ogresults');
        OGResults.workspace = loadWorkspace();
        OGResults.items = [];
        OGResults.tableCache = Object.create(null);
        OGResults.tables = Object.create(null);
        OGResults.activeTable = null;
        OGResults.charts = {};
        OGResults.requestID = 0;
        OGResults.tableRequestID = 0;
        if (!OGResults.workspace || !OGResults.workspace.country_id){
            window.location.hash = '#/OGCore';
            return;
        }
        OGResults.initEvents();
        Promise.all([OGResults.loadECharts(), Ogc.getCases(OGResults.workspace.country_id)])
            .then(values => OGResults.prepareCases(values[1]))
            .catch(error => OGResults.showEmpty('Unable to load results', String(error)));
    }

    static isCurrent(){
        return OGResults.pageID == PAGE_ID && localStorage.getItem('osy-pageId') == 'OGResults' && routePath() == '/OGResults';
    }

    static loadECharts(){
        if (window.echarts) return Promise.resolve(window.echarts);
        return new Promise((resolve, reject) => {
            let script = document.getElementById('ogc-echarts-runtime');
            if (script) script.remove();
            script = document.createElement('script');
            script.id = 'ogc-echarts-runtime';
            script.src = ECHARTS_URL;
            script.async = true;
            script.addEventListener('load', () => resolve(window.echarts), {once: true});
            script.addEventListener('error', () => {
                script.remove();
                reject('Charts could not be loaded.');
            }, {once: true});
            document.head.appendChild(script);
        });
    }

    static prepareCases(response){
        let cases = $.isArray(response) ? response : (response.cases || []);
        cases = $.grep(cases, item => item.country_id == OGResults.workspace.country_id);
        if (!cases.length){
            OGResults.showEmpty(
                'No cases in this workspace',
                'Create a case, then complete a baseline and reform run.',
                { href: '#/OGCases', label: 'Go to Cases' }
            );
            return;
        }
        return Promise.all($.map(cases, item => Ogc.getRuns(OGResults.workspace.country_id, item.casename)
            .then(result => ({ case: item, runs: result.runs || [] }))
            .catch(() => ({ case: item, runs: [] })))).then(items => {
                if (!OGResults.isCurrent()) return;
                OGResults.items = items;
                let viable = $.grep(items, item => {
                    let complete = $.grep(item.runs, run => run.status == 'completed');
                    let bases = $.grep(complete, run => run.run_type == 'baseline');
                    return $.grep(bases, base => OGResults.compatibleReforms(item, base.run_name).length).length;
                });
                if (!viable.length){
                    OGResults.showEmpty(
                        'No completed comparison',
                        'Complete a baseline and reform run.',
                        { href: '#/OGRuns', label: 'Go to Run' }
                    );
                    return;
                }
                $('#ogcResultCase').html($.map(viable, item => `<option value="${esc(item.case.casename)}">${esc(item.case.casename)}</option>`).join(''));
                OGResults.renderReformOptions(null);
            });
    }

    static currentItem(){
        let name = $('#ogcResultCase').val();
        return $.grep(OGResults.items, item => item.case.casename == name)[0] || null;
    }

    static currentBaseline(item){
        if (!item) return null;
        let complete = $.grep(item.runs, run => run.status == 'completed');
        let bases = $.grep(complete, run => run.run_type == 'baseline' && OGResults.compatibleReforms(item, run.run_name).length);
        return bases[0] || null;
    }

    static compatibleReforms(item, baseName){
        let complete = $.grep(item.runs, run => run.status == 'completed');
        let bases = $.grep(complete, run => run.run_type == 'baseline');
        return $.grep(complete, run => run.run_type == 'reform' &&
            (run.baseline_run == baseName || (!run.baseline_run && bases.length == 1)));
    }

    static renderReformOptions(saved){
        let item = OGResults.currentItem();
        let baseline = OGResults.currentBaseline(item);
        let baseName = baseline && baseline.run_name;
        let reforms = item ? OGResults.compatibleReforms(item, baseName) : [];
        $('#ogcResultReform').html($.map(reforms, run => `<option value="${esc(run.run_name)}">${esc(run.run_name)}</option>`).join(''));
        if (saved && saved.country_id == OGResults.workspace.country_id && saved.casename == (item && item.case.casename) && saved.base == baseName && $.grep(reforms, run => run.run_name == saved.reform).length){
            $('#ogcResultReform').val(saved.reform);
        }
        OGResults.loadComparison();
    }

    static loadComparison(){
        let item = OGResults.currentItem();
        let casename = item && item.case.casename;
        let baseline = OGResults.currentBaseline(item);
        let baseRun = baseline && baseline.run_name;
        let reformRun = $('#ogcResultReform').val();
        if (!casename || !baseRun || !reformRun){
            OGResults.showEmpty(
                'No completed comparison',
                'Complete a baseline and reform run.',
                { href: '#/OGRuns', label: 'Go to Run' }
            );
            return;
        }
        $('#ogcResultEmpty, #ogcResultBody').hide();
        $('#ogcResultLoading').show();
        OGResults.tables = Object.create(null);
        OGResults.activeTable = null;
        OGResults.tableRequestID++;
        $('#ogcTableExport').prop('disabled', true);
        $('#ogcResultTable').empty();
        $('#ogcTableStatus').text('Loading table…').show();
        let requestedAt = ++OGResults.requestID;
        Promise.all([
            Ogc.getSSVars(OGResults.workspace.country_id, casename, baseRun),
            Ogc.getSSVars(OGResults.workspace.country_id, casename, reformRun),
            Ogc.getParams(OGResults.workspace.country_id, casename, baseRun).catch(() => ({params:{}})),
            Ogc.getParams(OGResults.workspace.country_id, casename, reformRun).catch(() => ({params:{}})),
            Ogc.getParameterSchema(OGResults.workspace.country_id, casename)
                .then(schema => ({ schema: schema || {}, unavailable: false }))
                .catch(() => ({ schema: {}, unavailable: true }))
        ]).then(values => {
            if (!OGResults.isCurrent() || requestedAt != OGResults.requestID) return;
            OGResults.base = values[0];
            OGResults.reform = values[1];
            OGResults.baseParams = values[2].params || {};
            OGResults.reformParams = values[3].params || {};
            OGResults.schema = values[4].schema;
            OGResults.schemaUnavailable = values[4].unavailable;
            OGResults.selection = { casename: casename, base: baseRun, reform: reformRun };
            OGResults.useTableCache(OGResults.selection);
            OGResults.setDimensions();
            OGResults.renderAll();
            $('#ogcResultLoading').hide();
            $('#ogcResultBody').show();
            OGResults.loadInequalitySummary(requestedAt);
            if ($('.ogc-result-tabs button.active').data('result-tab') == 'tables'){
                OGResults.loadTable($('.ogc-table-pills button.active').data('table') || 'macro');
            }
        }).catch(error => {
            if (!OGResults.isCurrent() || requestedAt != OGResults.requestID) return;
            OGResults.showEmpty('Unable to load selected results', String(error));
        });
    }

    static loadInequalitySummary(comparisonRequestID){
        if (Object.prototype.hasOwnProperty.call(OGResults.tables, 'ineq')){
            OGResults.renderInequality();
            return;
        }
        let selectionKey = JSON.stringify(OGResults.selection);
        let s = OGResults.selection;
        Ogc.getIneqTable(OGResults.workspace.country_id, s.casename, s.base, s.reform).then(rows => {
            if (!OGResults.isCurrent() || comparisonRequestID != OGResults.requestID || selectionKey != JSON.stringify(OGResults.selection)) return;
            OGResults.tables.ineq = rows || [];
            OGResults.renderInequality();
        }).catch(() => {});
    }

    static setDimensions(){
        let baseParams = OGResults.baseParams || {};
        let schema = OGResults.schema || {};
        let sourceMatrix = null;
        $.each(DISTRIBUTION_VARS, (_, name) => {
            if (!sourceMatrix) sourceMatrix = rawMatrix(OGResults.base[name]);
        });
        let groupCount = sourceMatrix && sourceMatrix[0].length;
        let runLambdas = validWeights(baseParams.lambdas, groupCount);
        let schemaLambdas = validWeights(schema.lambdas && schema.lambdas.default, groupCount);
        let lambdas = runLambdas || schemaLambdas;
        if (!groupCount && lambdas) groupCount = lambdas.length;
        groupCount = groupCount || 0;
        let notes = [];
        if (lambdas){
            let cumulative = 0;
            OGResults.groups = $.map(lambdas, (weight, index) => {
                let start = Math.round(cumulative * 100);
                cumulative += Number(weight);
                let end = Math.round(cumulative * 100);
                if (index === 0) return `Bottom ${end}%`;
                if (index == lambdas.length - 1) return `Top ${100 - start}%`;
                return `${start}–${end}%`;
            });
        }else{
            OGResults.groups = $.map(Array(groupCount), (_, index) => `Group ${index + 1}`);
            if (groupCount) notes.push('Income-group metadata is unavailable, so generic group labels are shown.');
        }
        let runStartAge = firstNumber(baseParams.starting_age);
        let schemaStartAge = firstNumber(schema.starting_age && schema.starting_age.default);
        let startAge = runStartAge === null ? schemaStartAge : runStartAge;
        let matrix = sourceMatrix || [];
        OGResults.ages = $.map(matrix, (_, index) => startAge === null ? index + 1 : startAge + index + 1);
        if (matrix.length && startAge === null) notes.push('Starting-age metadata is unavailable, so model age indices are shown.');
        if (OGResults.schemaUnavailable) notes.unshift('Parameter metadata could not be loaded.');
        $('#ogcDimensionNote').text(notes.join(' ')).prop('hidden', !notes.length);
    }

    static useTableCache(selection){
        let key = JSON.stringify(selection);
        OGResults.tableCache = OGResults.tableCache || Object.create(null);
        if (!Object.prototype.hasOwnProperty.call(OGResults.tableCache, key)){
            OGResults.tableCache[key] = Object.create(null);
        }
        OGResults.tables = OGResults.tableCache[key];
    }

    static renderAll(){
        OGResults.disposeCharts();
        OGResults.renderMeta();
        OGResults.renderPolicy();
        OGResults.renderKpis();
        OGResults.renderInequality();
        OGResults.renderMacro();
        OGResults.renderFiscal();
        OGResults.renderDistributionControls();
        OGResults.renderDistribution();
        OGResults.renderProfileControls();
        OGResults.renderProfile();
        OGResults.renderExploreControls();
        OGResults.renderExplore();
        OGResults.bindResize();
    }

    static renderMeta(){
        let item = OGResults.currentItem();
        let reform = $.grep(item.runs, run => run.run_name == OGResults.selection.reform)[0] || {};
        let complete = reform.completed_at ? new Date(reform.completed_at).toLocaleDateString() : '';
        $('#ogcResultMeta').html(complete
            ? `<span class="ogc-result-meta-label">Reform run</span><time datetime="${esc(reform.completed_at)}">${esc(complete)}</time>`
            : '');
    }

    static renderPolicy(){
        let names = Object.create(null);
        $.each(OGResults.baseParams, name => { names[name] = true; });
        $.each(OGResults.reformParams, name => { names[name] = true; });
        let changes = [];
        $.each(names, name => {
            let schema = OGResults.schema[name] || {};
            let defaultValue = schema.default;
            let baseValue = name in OGResults.baseParams ? OGResults.baseParams[name] : defaultValue;
            let reformValue = name in OGResults.reformParams ? OGResults.reformParams[name] : defaultValue;
            if (!parameterEqual(baseValue, reformValue)){
                let title = String(schema.title || '').trim();
                changes.push({ name: name, label: title || humanize(name) });
            }
        });
        changes.sort((left, right) => left.label.localeCompare(right.label));
        if (!changes.length){
            $('#ogcPolicyChange').html('<span class="ogc-mut">No parameter changes.</span>');
            return;
        }
        let itemHtml = item => `<div class="ogc-policy-item"><b>${esc(item.label)}</b><code>${esc(item.name)}</code></div>`;
        let primary = $.map(changes.slice(0, 4), itemHtml).join('');
        let remaining = changes.slice(4);
        let extra = remaining.length
            ? `<button class="ogc-policy-toggle" type="button" data-count="${remaining.length}">Show ${remaining.length} more</button><div class="ogc-policy-extra" hidden>${$.map(remaining, itemHtml).join('')}</div>`
            : '';
        let count = `<div class="ogc-policy-count">${changes.length} parameter${changes.length == 1 ? '' : 's'} changed</div>`;
        $('#ogcPolicyChange').html(count + primary + extra);
    }

    static renderKpis(){
        let specs = [
            ['Y', 'GDP', '%'], ['C', 'Consumption', '%'], ['L', 'Labor', '%'],
            ['total_tax_revenue', 'Tax revenue', '%'], ['r', 'Real interest rate', 'pp']
        ];
        $('#ogcResultKpis').html($.map(specs, spec => {
            let b = firstNumber(OGResults.base[spec[0]]), r = firstNumber(OGResults.reform[spec[0]]);
            let delta = diff(b, r);
            let change = spec[2] == 'pp' ? (delta === null ? null : delta * 100) : pct(b, r);
            let baseline = spec[2] == 'pp' ? level(spec[0], b) : b;
            let reform = spec[2] == 'pp' ? level(spec[0], r) : r;
            let unit = spec[2] == 'pp' ? '%' : '';
            return `<article class="ogc-result-kpi"><span>${esc(spec[1])}</span><strong>${esc(signed(change, spec[2] == 'pp' ? ' percentage points' : '%'))}</strong><small><span>Baseline ${esc(fmt(baseline))}${unit}</span><span>Reform ${esc(fmt(reform))}${unit}</span></small></article>`;
        }).join(''));
    }

    static renderInequality(){
        let rows = OGResults.tables.ineq || [];
        let specs = [
            ['Gini Coefficient', 'Consumption Gini', 'diff'],
            ['90/10 Ratio', '90/10 ratio', 'diff'],
            ['Top 10% Share', 'Top 10% share', 'pp']
        ];
        let metrics = $.map(specs, spec => {
            let row = $.grep(rows, item => item['Inequality Measure'] == spec[0])[0];
            if (!row) return null;
            let baseline = Number(row.Baseline), reform = Number(row.Reform);
            let delta = diff(baseline, reform);
            let change = spec[2] == 'pp' && delta !== null ? delta * 100 : delta;
            let baselineLabel = spec[2] == 'pp' ? `${fmt(baseline * 100)}%` : fmt(baseline);
            let reformLabel = spec[2] == 'pp' ? `${fmt(reform * 100)}%` : fmt(reform);
            return `<div class="ogc-inequality-metric"><span>${esc(spec[1])}</span><strong>${esc(signed(change, spec[2] == 'pp' ? ' percentage points' : ''))}</strong><small>${esc(baselineLabel)} → ${esc(reformLabel)}</small></div>`;
        });
        $('#ogcInequalityMetrics').html(metrics.join(''));
        $('#ogcInequalitySummary').toggle(metrics.length > 0);
    }

    static renderMacro(){
        let specs = [['Y','GDP'], ['C','Consumption'], ['I','Investment'], ['K','Capital'], ['L','Labor'], ['w','Wage']];
        let labels = [], values = [];
        $.each(specs, (_, spec) => {
            labels.push(spec[1]);
            values.push(pct(firstNumber(OGResults.base[spec[0]]), firstNumber(OGResults.reform[spec[0]])));
        });
        OGResults.setChart('ogcMacroChart', comparisonBar(labels, values, 'Percent change in macroeconomic outcomes from the selected baseline to reform.'));
    }

    static renderFiscal(){
        let rows = $.map(FISCAL_VARS, name => ({
            label: info(name).label,
            value: pct(firstNumber(OGResults.base[name]), firstNumber(OGResults.reform[name]))
        })).filter(row => row.value !== null);
        OGResults.setChart('ogcFiscalChart', comparisonBar($.map(rows, r => r.label), $.map(rows, r => r.value), 'Ranked percent changes in fiscal outcomes from baseline to reform.'));
    }

    static matrixTransform(name, measure){
        let base = ageGroupMatrix(OGResults.base[name]);
        let reform = ageGroupMatrix(OGResults.reform[name]);
        if (!compatibleMatrices(base, reform)) return null;
        return base.map((row, i) => row.map((value, j) =>
            measureValue(name, value, reform[i] && reform[i][j], measure)));
    }

    static heatOption(name, measure){
        let matrix = OGResults.matrixTransform(name, measure);
        if (!matrix) return chartBase('No compatible matrix data.');
        let values = [], transformed = [];
        $.each(matrix, (i, row) => $.each(row, (j, value) => {
            if (value !== null && isFinite(value)){
                values.push([i, j, value]);
                transformed.push(value);
            }
        }));
        let scale = robustHeatScale(transformed);
        let bound = scale.bound;
        let unit = measureSuffix(name, measure);
        let option = $.extend(true, chartBase(`${info(name).label}: ${measureLabel(name, measure).toLowerCase()} by age and lifetime-income group.`), {
            grid: { left: 58, right: 26, top: 12, bottom: 68, containLabel: true },
            tooltip: {
                position: 'top', trigger: 'item',
                formatter: p => `<b>Age ${esc(OGResults.ages[p.value[0]] || p.value[0] + 1)}</b><br>${esc(OGResults.groups[p.value[1]] || 'Group ' + (p.value[1] + 1))}<br><b>${esc(signed(p.value[2], unit))}</b>`
            },
            xAxis: { type: 'category', data: OGResults.ages, name: 'Age', nameLocation: 'middle', nameGap: 28, axisTick: { show: false }, axisLine: { lineStyle: { color: '#ccd0d8' } }, axisLabel: { color: MUTED, interval: 9 } },
            yAxis: { type: 'category', data: OGResults.groups, axisTick: { show: false }, axisLine: { show: false }, axisLabel: { color: SLATE } },
            visualMap: { min: -bound, max: bound, calculable: false, orient: 'horizontal', left: 'center', bottom: 3, precision: 2, text: ['Increase', 'Decrease'], textStyle: { color: MUTED }, inRange: { color: ['#39769f', '#d9e4ea', '#f7f7f5', '#f9d8b8', '#d9680b'] } },
            series: [{ type: 'heatmap', data: values, progressive: 1000, emphasis: { itemStyle: { borderColor: SLATE, borderWidth: 1 } }, itemStyle: { borderColor: '#fff', borderWidth: 0.35 } }]
        });
        option.ogcScale = scale;
        return option;
    }

    static renderDistributionControls(){
        let available = $.grep(DISTRIBUTION_VARS, name => shape(OGResults.base[name]).kind == 'age_group' && name in OGResults.reform);
        $('#ogcDistributionVariable').html($.map(available, name => `<option value="${esc(name)}">${esc(info(name).short || info(name).label)}</option>`).join(''));
        $('#ogcDistributionVariable').val($.grep(available, name => name == 'c').length ? 'c' : available[0]);
    }

    static renderDistribution(){
        let name = $('#ogcDistributionVariable').val() || 'c';
        let measure = $('#ogcDistributionMeasure').val() || 'pct';
        $('#ogcDistributionTitle').text(`${info(name).label} by age and lifetime income`);
        $('#ogcDistributionChart').attr('aria-label', `${info(name).label}, ${measureLabel(name, measure).toLowerCase()}, by age and lifetime-income group`);
        let option = OGResults.heatOption(name, measure);
        let scale = option.ogcScale;
        delete option.ogcScale;
        $('#ogcDistributionScale').text(scale
            ? `Color scale ±${fmt(scale.bound)}${measureSuffix(name, measure)}${scale.clipped ? ` · ${scale.cappedPercent}% outside scale` : ''}`
            : '');
        OGResults.setChart('ogcDistributionChart', option);
        let chart = OGResults.charts.ogcDistributionChart;
        chart.off('click');
        chart.on('click', params => {
            if (!params.value) return;
            OGResults.openTab('explore');
            $('#ogcExploreVariable').val(name);
            OGResults.refreshExploreMeasures(measure);
            $('#ogcExploreGroup').val(params.value[1]);
            OGResults.refreshExploreViews('profile');
            OGResults.renderExplore();
        });
    }

    static renderProfileControls(){
        $('#ogcProfileVariable').html($.map(PROFILE_VARS, name => `<option value="${esc(name)}">${esc(info(name).short || info(name).label)}</option>`).join(''));
        $('#ogcProfileGroup, #ogcExploreGroup').html($.map(OGResults.groups, (label, index) => `<option value="${index}">${esc(label)}</option>`).join(''));
        $('#ogcProfileGroup').val(Math.min(3, OGResults.groups.length - 1));
    }

    static profileOption(name, group, measure){
        let base = ageGroupMatrix(OGResults.base[name]) || [];
        let reform = ageGroupMatrix(OGResults.reform[name]) || [];
        let baseValues = $.map(base, row => row[group]);
        let reformValues = $.map(reform, row => row[group]);
        let series = [];
        if (measure == 'levels'){
            baseValues = $.map(baseValues, value => level(name, value));
            reformValues = $.map(reformValues, value => level(name, value));
            series = [
                { name: 'Baseline', type: 'line', data: baseValues, showSymbol: false, lineStyle: { width: 2.5, color: SLATE }, itemStyle: { color: SLATE } },
                { name: 'Reform', type: 'line', data: reformValues, showSymbol: false, lineStyle: { width: 2.5, color: ORANGE }, itemStyle: { color: ORANGE } }
            ];
        }else{
            let data = baseValues.map((value, i) => measureValue(name, value, reformValues[i], measure));
            series = [{ name: measureLabel(name, measure), type: 'line', data: data, showSymbol: false, lineStyle: { width: 2.5, color: ORANGE }, areaStyle: { color: 'rgba(245,130,32,.08)' }, itemStyle: { color: ORANGE }, markLine: { silent: true, symbol: 'none', data: [{ yAxis: 0 }], label: { show: false }, lineStyle: { color: '#9ba1ad' } } }];
        }
        return $.extend(true, chartBase(`${info(name).label} by age for ${OGResults.groups[group] || 'the selected income group'}.`), {
            color: [SLATE, ORANGE],
            legend: { show: measure == 'levels', top: 0, right: 10, icon: 'roundRect', textStyle: { color: MUTED } },
            grid: { left: 28, right: 28, top: measure == 'levels' ? 40 : 18, bottom: 40, containLabel: true },
            tooltip: { trigger: 'axis', valueFormatter: v => fmt(v) + measureSuffix(name, measure) },
            xAxis: { type: 'category', data: OGResults.ages, name: 'Age', nameLocation: 'middle', nameGap: 28, boundaryGap: false, axisTick: { show: false }, axisLine: { lineStyle: { color: '#ccd0d8' } }, axisLabel: { color: MUTED, interval: 9 } },
            yAxis: { type: 'value', name: measureLabel(name, measure), nameTextStyle: { color: MUTED }, axisLine: { show: false }, axisTick: { show: false }, splitLine: { lineStyle: { color: GRID } }, axisLabel: { color: MUTED, formatter: value => axisLabel(value) + measureSuffix(name, measure) } },
            series: series
        });
    }

    static renderProfile(){
        let name = $('#ogcProfileVariable').val() || 'c';
        let group = Number($('#ogcProfileGroup').val() || 0);
        let measure = $('#ogcProfileMeasure').val() || 'levels';
        OGResults.setChart('ogcProfileChart', OGResults.profileOption(name, group, measure));
    }

    static renderExploreControls(){
        let names = Object.keys(CATALOG).filter(name => name in (OGResults.base || {}) && name in (OGResults.reform || {}));
        names.sort((a, b) => (info(a).category + info(a).label).localeCompare(info(b).category + info(b).label));
        let last = null, html = '';
        $.each(names, (_, name) => {
            let meta = info(name);
            if (meta.category != last){
                if (last !== null) html += '</optgroup>';
                html += `<optgroup label="${esc(meta.category)}">`;
                last = meta.category;
            }
            html += `<option value="${esc(name)}">${esc(meta.label)} (${esc(name)})</option>`;
        });
        if (last !== null) html += '</optgroup>';
        $('#ogcExploreVariable').html(html);
        let saved = OGResults.readSaved();
        if (saved && saved.country_id == OGResults.workspace.country_id && saved.variable && saved.variable in CATALOG && saved.variable in OGResults.base){
            $('#ogcExploreVariable').val(saved.variable);
            $('#ogcExploreGroup').val(saved.group || 0);
        }else{
            $('#ogcExploreVariable').val('Y');
        }
        OGResults.refreshExploreMeasures(saved && saved.measure);
        OGResults.refreshExploreViews(saved && saved.view);
    }

    static refreshExploreMeasures(preferred){
        let name = $('#ogcExploreVariable').val();
        let meta = info(name);
        let options;
        if (meta.rate){
            options = [['pp', 'Percentage-point difference'], ['levels', 'Rates (%)']];
        }else if (meta.differenceOnly || meta.category == 'Model diagnostics'){
            options = [['diff', 'Difference'], ['levels', 'Levels']];
        }else{
            options = [['pct', 'Percent change'], ['diff', 'Difference'], ['levels', 'Levels']];
        }
        $('#ogcExploreMeasure').html($.map(options, option => `<option value="${option[0]}">${esc(option[1])}</option>`).join(''));
        if ($.grep(options, option => option[0] == preferred).length) $('#ogcExploreMeasure').val(preferred);
    }

    static refreshExploreViews(preferred){
        let name = $('#ogcExploreVariable').val();
        let measure = $('#ogcExploreMeasure').val();
        let spec = shape(OGResults.base[name]);
        let views = [];
        if (spec.kind == 'scalar') views = [['comparison','Comparison bars'], ['table','Table']];
        else if (spec.kind == 'age_group'){
            if (measure != 'levels') views.push(['heatmap','Age × income heatmap']);
            views.push(['profile','Lifecycle profile'], ['table','Table']);
        }else if (spec.kind == 'group') views = [['comparison','Income-group bars'], ['table','Table']];
        else if (spec.kind == 'vector') views = [['comparison','Comparison chart'], ['table','Table']];
        else views = [['table','Table']];
        let current = preferred || $('#ogcExploreView').val();
        $('#ogcExploreView').html($.map(views, view => `<option value="${view[0]}">${esc(view[1])}</option>`).join(''));
        if ($.grep(views, view => view[0] == current).length) $('#ogcExploreView').val(current);
        $('.ogc-explore-group').toggle(spec.kind == 'age_group' && $('#ogcExploreView').val() == 'profile');
        let shapeLabel = spec.kind == 'age_group' ? 'Age × income group' : humanize(spec.kind);
        let dimensionLabel = spec.kind == 'age_group' && spec.dims.length == 2
            ? `${spec.dims[0]} ages × ${spec.dims[1]} income groups`
            : (spec.dims.length ? spec.dims.join(' × ') : 'Single value');
        $('#ogcExploreShape').html(`<span>Dimensions</span><strong>${esc(shapeLabel)}</strong><small>${esc(dimensionLabel)}</small>`);
    }

    static renderExplore(){
        let name = $('#ogcExploreVariable').val();
        let measure = $('#ogcExploreMeasure').val();
        let view = $('#ogcExploreView').val();
        let group = Number($('#ogcExploreGroup').val() || 0);
        let meta = info(name);
        let spec = shape(OGResults.base[name]);
        $('#ogcExploreCategory').text(meta.category);
        $('#ogcExploreTitle').text(meta.label);
        $('#ogcExploreUnit').text(measureLabel(name, measure));
        $('#ogcExploreChart').attr('aria-label', `${meta.label}, ${measureLabel(name, measure).toLowerCase()}, ${view}`);
        $('.ogc-explore-group').toggle(spec.kind == 'age_group' && view == 'profile');
        $('#ogcExploreChart').removeClass('ogc-explore-scalar ogc-explore-category ogc-explore-dense')
            .addClass(spec.kind == 'scalar' ? 'ogc-explore-scalar' : (spec.kind == 'group' || spec.kind == 'vector' ? 'ogc-explore-category' : 'ogc-explore-dense'));
        $('#ogcExploreTable').hide();
        $('#ogcExploreChart').show();
        $('.ogc-explore-output .ogc-chart-export').show();
        if (view == 'table'){
            $('#ogcExploreChart').hide();
            $('.ogc-explore-output .ogc-chart-export').hide();
            OGResults.renderExploreTable(name, measure);
            return;
        }
        let option;
        if (view == 'heatmap'){
            option = OGResults.heatOption(name, measure);
            let scale = option.ogcScale;
            if (scale){
                $('#ogcExploreUnit').text(`${measureLabel(name, measure)} · Color scale ±${fmt(scale.bound)}${measureSuffix(name, measure)}${scale.clipped ? ` · ${scale.cappedPercent}% outside scale` : ''}`);
            }
            delete option.ogcScale;
        }
        else if (view == 'profile') option = OGResults.profileOption(name, group, measure);
        else option = OGResults.comparisonOption(name, measure);
        OGResults.setChart('ogcExploreChart', option);
    }

    static comparisonOption(name, measure){
        let base = OGResults.base[name], reform = OGResults.reform[name];
        let spec = shape(base), labels = [], baseValues = [], reformValues = [];
        if (spec.kind == 'scalar'){
            labels = [info(name).short || info(name).label];
            baseValues = [firstNumber(base)]; reformValues = [firstNumber(reform)];
        }else{
            let b = rank(base) > 1 ? (ageGroupMatrix(base) || []).map(firstNumber) : base;
            let r = rank(reform) > 1 ? (ageGroupMatrix(reform) || []).map(firstNumber) : reform;
            baseValues = $.map(b || [], firstNumber); reformValues = $.map(r || [], firstNumber);
            labels = spec.kind == 'group' ? OGResults.groups.slice(0, baseValues.length) : $.map(baseValues, (_, i) => String(i + 1));
        }
        let series;
        if (measure == 'levels'){
            baseValues = $.map(baseValues, value => level(name, value));
            reformValues = $.map(reformValues, value => level(name, value));
            series = [
                { name: 'Baseline', type: 'bar', data: baseValues, itemStyle: { color: SLATE }, barMaxWidth: 28 },
                { name: 'Reform', type: 'bar', data: reformValues, itemStyle: { color: ORANGE }, barMaxWidth: 28 }
            ];
        }else{
            let values = baseValues.map((value, i) => measureValue(name, value, reformValues[i], measure));
            series = [{ name: measureLabel(name, measure), type: 'bar', data: values.map(v => ({value:v, itemStyle:{color:v >= 0 ? ORANGE : BLUE}})), barMaxWidth: 28, label: { show: values.length <= 12, position: 'top', color: SLATE, formatter: p => signed(p.value, measureSuffix(name, measure)) }, markLine: { silent: true, symbol: 'none', data: [{yAxis:0}], lineStyle:{color:'#9ba1ad'}, label:{show:false} } }];
        }
        return $.extend(true, chartBase(`${metaLabel(name)} comparison.`), {
            tooltip: { trigger: 'axis', valueFormatter: value => fmt(value) + measureSuffix(name, measure) },
            legend: { show: measure == 'levels', top: 0, right: 10, textStyle: {color:MUTED} },
            grid: { left: 24, right: 26, top: measure == 'levels' ? 40 : 24, bottom: labels.length > 10 ? 70 : 34, containLabel: true },
            xAxis: { type: 'category', data: labels, axisTick:{show:false}, axisLine:{lineStyle:{color:'#ccd0d8'}}, axisLabel:{color:MUTED, rotate:labels.length > 10 ? 35 : 0} },
            yAxis: { type: 'value', axisTick:{show:false}, axisLine:{show:false}, splitLine:{lineStyle:{color:GRID}}, axisLabel:{color:MUTED, formatter:v => axisLabel(v) + measureSuffix(name, measure)} },
            series: series
        });
    }

    static renderExploreTable(name, measure){
        let spec = shape(OGResults.base[name]);
        let headers = [], rows = [];
        if (spec.kind == 'age_group'){
            let b = ageGroupMatrix(OGResults.base[name]), r = ageGroupMatrix(OGResults.reform[name]);
            if (!compatibleMatrices(b, r)){
                $('#ogcExploreTable').html('<div class="ogc-table-status">Comparable baseline and reform matrix data are unavailable.</div>').show();
                return;
            }
            if (measure == 'levels'){
                headers = ['Age'];
                $.each(OGResults.groups, (_, label) => headers.push('Baseline: ' + label, 'Reform: ' + label));
                rows = b.map((row, i) => [OGResults.ages[i]].concat(...row.map((value, j) => [level(name, value), level(name, r[i][j])])));
            }else{
                headers = ['Age'].concat(OGResults.groups);
                let transformed = OGResults.matrixTransform(name, measure);
                rows = transformed.map((row, i) => [OGResults.ages[i]].concat(row));
            }
        }else if (spec.kind == 'matrix'){
            let pairs = [];
            indexedPairs(OGResults.base[name], OGResults.reform[name], [], pairs);
            if (measure == 'levels'){
                headers = ['Index', 'Baseline', 'Reform'];
                rows = pairs.map(item => [item.dimension, level(name, item.baseline), level(name, item.reform)]);
            }else{
                headers = ['Index', 'Baseline', 'Reform', measureLabel(name, measure)];
                rows = pairs.map(item => [item.dimension, level(name, item.baseline), level(name, item.reform), measureValue(name, item.baseline, item.reform, measure)]);
            }
        }else{
            let b = $.isArray(OGResults.base[name]) ? OGResults.base[name] : [OGResults.base[name]];
            let r = $.isArray(OGResults.reform[name]) ? OGResults.reform[name] : [OGResults.reform[name]];
            b = $.map(b, firstNumber); r = $.map(r, firstNumber);
            if (measure == 'levels'){
                headers = ['Dimension', 'Baseline', 'Reform'];
                rows = b.map((value, i) => [spec.kind == 'group' ? OGResults.groups[i] : (i + 1), level(name, value), level(name, r[i])]);
            }else{
                headers = ['Dimension', 'Baseline', 'Reform', measureLabel(name, measure)];
                rows = b.map((value, i) => [spec.kind == 'group' ? OGResults.groups[i] : (i + 1), level(name, value), level(name, r[i]), measureValue(name, value, r[i], measure)]);
            }
        }
        $('#ogcExploreTable').html(OGResults.tableHtml(headers, rows)).show();
    }

    static tableHtml(headers, rows, label){
        rows = $.map(rows, row => [$.map(row, resultTableCell)]);
        let numeric = $.map(headers, (_, index) => {
            let values = $.map(rows, row => row[index] === null || row[index] === undefined || row[index] === '' ? null : row[index]);
            return values.length > 0 && $.grep(values, value => typeof value != 'number').length == 0;
        });
        return `<table class="ogc-table ogc-analysis-table" aria-label="${esc(label || 'Results table')}"><thead><tr>${$.map(headers, (header, index) => `<th scope="col"${numeric[index] ? ' class="ogc-num"' : ''}>${esc(header)}</th>`).join('')}</tr></thead><tbody>${$.map(rows, row => `<tr>${$.map(row, (cell, index) => `<td${numeric[index] ? ' class="ogc-num"' : ''}>${esc(typeof cell == 'number' ? fmt(cell) : cell)}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
    }

    static tableLabel(key){
        return {
            macro: 'Macroeconomic results',
            ineq: 'Inequality measures',
            gini: 'Gini detail',
            wealth: 'Wealth moments'
        }[key] || 'Results table';
    }

    static displayTableHeader(header){
        if (OGResults.activeTableKey == 'wealth' && header == 'Model') return 'Baseline';
        return {
            'Steady-State Variable': 'Outcome',
            'Inequality Measure': 'Measure',
            'Gini Type': 'Gini type',
            '% Change': 'Change (%)',
            '% Change (or pp diff)': 'Change (% or percentage points)'
        }[header] || header;
    }

    static loadTable(key){
        $('.ogc-table-pills button').removeClass('active').attr('aria-selected', 'false')
            .filter(`[data-table="${key}"]`).addClass('active').attr('aria-selected', 'true');
        OGResults.activeTableKey = key;
        OGResults.activeTable = null;
        let requestedAt = ++OGResults.tableRequestID;
        $('#ogcTableExport').prop('disabled', true);
        if (Object.prototype.hasOwnProperty.call(OGResults.tables, key)){
            OGResults.renderTableRows(OGResults.tables[key]);
            return;
        }
        $('#ogcTableStatus').html('<i class="fa fa-circle-o-notch fa-spin" aria-hidden="true"></i> Loading table…').show();
        $('#ogcResultTable').empty();
        let s = OGResults.selection;
        let selectionKey = JSON.stringify(s);
        let request = key == 'macro' ? Ogc.getMacroTableSS(OGResults.workspace.country_id, s.casename, s.base, s.reform)
            : key == 'ineq' ? Ogc.getIneqTable(OGResults.workspace.country_id, s.casename, s.base, s.reform)
            : key == 'gini' ? Ogc.getGiniTable(OGResults.workspace.country_id, s.casename, s.base, s.reform)
            : Ogc.getWealthMomentsTable(OGResults.workspace.country_id, s.casename, s.base);
        request.then(rows => {
            if (!OGResults.isCurrent() || requestedAt != OGResults.tableRequestID || selectionKey != JSON.stringify(OGResults.selection)) return;
            OGResults.tables[key] = rows;
            OGResults.renderTableRows(rows);
        }).catch(error => {
            if (requestedAt == OGResults.tableRequestID && selectionKey == JSON.stringify(OGResults.selection)){
                $('#ogcTableStatus').text(`Unable to load table. ${String(error)}`).show();
            }
        });
    }

    static renderTableRows(rows){
        if (!$.isArray(rows) || !rows.length){
            $('#ogcTableStatus').text('No data available.').show();
            return;
        }
        let headers = Object.keys(rows[0]);
        let preferred = [
            'Variable', 'Steady-State Variable', 'Inequality Measure', 'Gini Type',
            'Moment', 'Baseline', 'Reform', 'Model', '% Change', '% Change (or pp diff)'
        ];
        headers.sort((a, b) => {
            let ai = preferred.indexOf(a), bi = preferred.indexOf(b);
            return (ai < 0 ? 999 : ai) - (bi < 0 ? 999 : bi);
        });
        let body = rows.map(row => headers.map(header => resultTableCell(row[header])));
        let displayHeaders = headers.map(header => OGResults.displayTableHeader(header));
        let tableLabel = OGResults.tableLabel(OGResults.activeTableKey);
        OGResults.activeTable = { headers: displayHeaders, rows: body };
        $('#ogcTableStatus').hide();
        $('#ogcResultTable').html(OGResults.tableHtml(displayHeaders, body, tableLabel));
        $('#ogcTableExport').prop('disabled', false);
    }

    static setChart(id, option){
        let el = document.getElementById(id);
        if (!el || !window.echarts) return;
        let chart = OGResults.charts[id];
        if (!chart || chart.isDisposed()){
            chart = window.echarts.init(el, null, {renderer: 'svg'});
            OGResults.charts[id] = chart;
        }
        chart.setOption(option, true);
        chart.resize();
    }

    static disposeCharts(){
        $.each(OGResults.charts || {}, (_, chart) => { if (chart && !chart.isDisposed()) chart.dispose(); });
        OGResults.charts = {};
    }

    static bindResize(){
        $(window).off('resize.ogresults').on('resize.ogresults', () => {
            $.each(OGResults.charts, (_, chart) => { if (chart && !chart.isDisposed()) chart.resize(); });
        });
    }

    static teardown(){
        OGResults.disposeCharts();
        $(window).off('.ogresults');
        $(document).off('.ogresults');
    }

    static openTab(name){
        $('.ogc-result-tabs button').removeClass('active').attr('aria-selected', 'false');
        $(`.ogc-result-tabs button[data-result-tab="${name}"]`).addClass('active').attr('aria-selected', 'true');
        $('.ogc-result-pane').removeClass('active');
        $(`.ogc-result-pane[data-result-pane="${name}"]`).addClass('active');
        setTimeout(() => $.each(OGResults.charts, (_, chart) => { if (chart && !chart.isDisposed()) chart.resize(); }), 20);
        if (name == 'tables') OGResults.loadTable($('.ogc-table-pills button.active').data('table') || 'macro');
    }

    static readSaved(){
        try {
            let countryID = OGResults.workspace.country_id;
            let saved = JSON.parse(localStorage.getItem(`${VIEW_KEY}:${countryID}`)) || null;
            if (saved) return saved;
            let legacy = JSON.parse(localStorage.getItem(VIEW_KEY)) || null;
            return legacy && legacy.country_id == countryID ? legacy : null;
        } catch (error) { return null; }
    }

    static saveView(){
        let saved = {
            country_id: OGResults.workspace.country_id,
            variable: $('#ogcExploreVariable').val(), measure: $('#ogcExploreMeasure').val(),
            view: $('#ogcExploreView').val(), group: $('#ogcExploreGroup').val()
        };
        localStorage.setItem(`${VIEW_KEY}:${OGResults.workspace.country_id}`, JSON.stringify(saved));
        $('#ogcSavedNote').text('Default view saved');
    }

    static exportChart(id){
        let chart = OGResults.charts[id];
        if (!chart || chart.isDisposed()) return;
        let link = document.createElement('a');
        let chartName = String(id || 'chart').replace(/^ogc|Chart$/g, '').replace(/([a-z])([A-Z])/g, '$1-$2').toLowerCase();
        link.download = `ogcore-${OGResults.selection.casename}-${OGResults.selection.reform}-${chartName}.svg`;
        link.href = chart.getDataURL({type:'svg', pixelRatio:2, backgroundColor:'#ffffff'});
        link.click();
    }

    static exportTable(){
        if (!OGResults.activeTable) return;
        let quote = value => `"${String(value == null ? '' : value).replace(/"/g, '""')}"`;
        let lines = [OGResults.activeTable.headers].concat(OGResults.activeTable.rows)
            .map(row => $.map(row, quote).join(','));
        let blob = new Blob(['\ufeff' + lines.join('\r\n')], {type:'text/csv;charset=utf-8'});
        let link = document.createElement('a');
        link.download = `ogcore-${OGResults.selection.casename}-${OGResults.selection.reform}-${OGResults.activeTableKey || 'table'}.csv`;
        link.href = URL.createObjectURL(blob);
        link.click();
        setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    }

    static showEmpty(title, text, action){
        $('#ogcResultLoading, #ogcResultBody').hide();
        $('#ogcResultEmptyTitle').text(title);
        $('#ogcResultEmptyText').text(text);
        let link = $('#ogcResultEmptyAction');
        if (action){
            link.attr('href', action.href).text(action.label).show();
        }else{
            link.hide();
        }
        $('#ogcResultEmpty').show();
    }

    static initEvents(){
        $(document).off('.ogresults');
        $(window).off('hashchange.ogresults').on('hashchange.ogresults', () => {
            if (routePath() == '/OGResults') return;
            OGResults.teardown();
        });
        $(document).on('click.ogresults', '.ogc-result-tabs button', function(){ OGResults.openTab($(this).data('result-tab')); });
        $(document).on('change.ogresults', '#ogcResultCase', () => OGResults.renderReformOptions(null));
        $(document).on('change.ogresults', '#ogcResultReform', () => OGResults.loadComparison());
        $(document).on('change.ogresults', '#ogcDistributionVariable, #ogcDistributionMeasure', () => OGResults.renderDistribution());
        $(document).on('change.ogresults', '#ogcProfileVariable, #ogcProfileGroup, #ogcProfileMeasure', () => OGResults.renderProfile());
        $(document).on('change.ogresults', '#ogcExploreVariable', () => { OGResults.refreshExploreMeasures(); OGResults.refreshExploreViews(); OGResults.renderExplore(); });
        $(document).on('change.ogresults', '#ogcExploreMeasure', () => { OGResults.refreshExploreViews(); OGResults.renderExplore(); });
        $(document).on('change.ogresults', '#ogcExploreView', () => { OGResults.refreshExploreViews(); OGResults.renderExplore(); });
        $(document).on('change.ogresults', '#ogcExploreGroup', () => OGResults.renderExplore());
        $(document).on('click.ogresults', '.ogc-table-pills button', function(){ OGResults.loadTable($(this).data('table')); });
        $(document).on('click.ogresults', '.ogc-policy-toggle', function(){
            let extra = $('.ogc-policy-extra');
            let opening = extra.prop('hidden');
            extra.prop('hidden', !opening);
            $(this).text(opening ? 'Show less' : `Show ${$(this).data('count')} more`);
        });
        $(document).on('click.ogresults', '#ogcSaveView', () => OGResults.saveView());
        $(document).on('click.ogresults', '#ogcResetView', () => {
            localStorage.removeItem(`${VIEW_KEY}:${OGResults.workspace.country_id}`);
            localStorage.removeItem(VIEW_KEY); $('#ogcExploreVariable').val('Y'); $('#ogcExploreMeasure').val('pct');
            OGResults.refreshExploreMeasures('pct'); OGResults.refreshExploreViews('comparison'); OGResults.renderExplore(); $('#ogcSavedNote').text('Defaults restored');
        });
        $(document).on('click.ogresults', '.ogc-chart-export[data-export-chart]', function(){ OGResults.exportChart($(this).data('export-chart')); });
        $(document).on('click.ogresults', '#ogcTableExport', () => OGResults.exportTable());
    }
}

function metaLabel(name){ return info(name).label; }
