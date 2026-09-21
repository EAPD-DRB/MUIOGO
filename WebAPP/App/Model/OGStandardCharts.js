const HOUSEHOLDS = {
    c: 'Consumption', n: 'Labor supply', b_sp1: 'Savings', etr: 'Effective tax rate',
    mtrx: 'Marginal labor income tax rate', mtry: 'Marginal capital income tax rate',
    before_tax_income: 'Before-tax income'
};
const LABELS = {Y:'GDP', K:'Capital', L:'Labor', C:'Consumption', D:'Government debt', TR:'Transfers', total_tax_revenue:'Tax revenue'};
const RATES = new Set(['r', 'etr', 'mtrx', 'mtry']);

export const STANDARD_CHARTS = [
    {id:'macro', title:'Macroeconomic changes', variables:['Y','K','L','C'], description:'Percentage changes in aggregate output, capital, labor and consumption over time.'},
    {id:'fiscal', title:'Fiscal changes', variables:['D','TR','total_tax_revenue'], description:'Percentage changes in government debt, transfers and tax revenue over time.'},
    {id:'interest', title:'Real interest rates', variables:['r'], description:'Baseline and reform real interest rates over time.'},
    {id:'wage', title:'Wage rates', variables:['w'], description:'Baseline and reform wages including productivity growth.'},
    {id:'spending_gdp', title:'Government spending to GDP', variables:['G','Y'], description:'Government spending as a percentage of each run’s GDP.'},
    {id:'debt_gdp', title:'Debt to GDP', variables:['D','Y'], description:'Government debt as a percentage of each run’s GDP.'},
    {id:'revenue_gdp', title:'Tax revenue to GDP', variables:['total_tax_revenue','Y'], description:'Tax revenue as a percentage of each run’s GDP.'}
].map(chart => ({...chart, family:'aggregate', requires:'transition'})).concat(
    Object.entries(HOUSEHOLDS).map(([variable, label]) => ({
        id:'ability_' + variable, title:label + ' by income group', variable, variables:[variable],
        family:'ability', requires:'transition',
        description:'Percentage change over the first ten years, weighted using the baseline population.'
    })),
    Object.entries(HOUSEHOLDS).filter(([name]) => name != 'before_tax_income').map(([variable, label]) => ({
        id:'lifecycle_' + variable, title:label + ' by age', variable, variables:[variable],
        family:'lifecycle', requires:'steady',
        description:'Long-run household outcomes, shown separately by income group or as a weighted overall profile.'
    }))
);

const finite = value => typeof value == 'number' && Number.isFinite(value);
const missing = detail => { throw new Error(detail); };
function scalar(value){
    while (Array.isArray(value) && value.length == 1) value = value[0];
    return value;
}
function parameter(run, name){
    const value = scalar(run.params?.[name]);
    if (!finite(value)) missing(`Executed ${name} is required for this chart.`);
    return value;
}
function integer(run, name, minimum = 0){
    const value = parameter(run, name);
    if (!Number.isInteger(value) || value < minimum) missing(`Executed ${name} must be an integer of at least ${minimum}.`);
    return value;
}
function path(values, count, name){
    if (!Array.isArray(values) || values.length < count || values.slice(0,count).some(Array.isArray)){
        missing(`A numeric ${name} path covering ${count} periods is required.`);
    }
    return Array.from({length:count}, (_, index) => finite(values[index]) ? values[index] : null);
}
function percent(base, reform){
    const result = finite(base) && finite(reform) && base !== 0 ? (reform / base - 1) * 100 : null;
    return finite(result) ? result : null;
}
function ratio(value, denominator){
    const result = finite(value) && finite(denominator) && denominator !== 0 ? value / denominator * 100 : null;
    return finite(result) ? result : null;
}
function weights(run){
    const count = integer(run, 'J', 1);
    const raw = run.params?.lambdas;
    const values = Array.isArray(raw) ? raw.map(scalar) : [];
    if (values.length != count || values.some(value => !finite(value) || value < 0)
        || Math.abs(values.reduce((sum,value) => sum + value, 0) - 1) > 0.001){
        missing('Executed income-group weights (lambdas) are required for this chart.');
    }
    return values;
}
export function resultRun(ss, params = {}){
    const values = Object.keys(HOUSEHOLDS).map(name => ss?.[name]).find(value =>
        Array.isArray(value) && Array.isArray(value[0]));
    return {ss, params:{...params,
        S:params.S ?? values?.length, J:params.J ?? values?.[0]?.length}};
}

export function hasProfileWeights(run){
    try { weights(run); return true; } catch { return false; }
}

export function hasPopulationWeights(baseline, reform){
    return hasProfileWeights(baseline) && hasProfileWeights(reform)
        && Array.isArray(baseline.params?.omega) && baseline.params.omega.length >= 10;
}

// Column captions are OG-Core's time_series_table contract; mathematical labels
// are stripped so cosmetic TeX changes do not change the variable mapping.
const TABLE_LABELS = {Y:'GDP', K:'Capital Stock', L:'Labor', D:'Government Debt',
    TR:'Government Transfers', total_tax_revenue:'Total tax revenue',
    G:'Government Consumption Expenditures', r:'Real interest rate', w:'Wage rate'};

export function timeSeriesRuns(rows){
    if (!Array.isArray(rows) || !rows.length) missing('No transition-path table data are available.');
    const years = rows.map(row => row.Year);
    if (years.some((year,index) => !Number.isInteger(year) || year !== years[0] + index)){
        missing('Transition-path years must be consecutive calendar years.');
    }
    const runs = {};
    for (const scenario of ['Baseline','Reform']){
        const paths = {};
        for (const [name,label] of Object.entries(TABLE_LABELS)){
            const keys = Object.keys(rows[0]).filter(key =>
                key.endsWith(': ' + scenario) && key.slice(0,-(': ' + scenario).length)
                    .replace(/\s*\(.*\)$/, '').trim().toLowerCase() === label.toLowerCase());
            if (keys.length > 1) missing(`Ambiguous ${label} columns in the transition table.`);
            if (keys.length) paths[name] = rows.map(row => finite(row[keys[0]]) ? row[keys[0]] : null);
        }
        runs[scenario.toLowerCase()] = {params:{start_year:years[0],T:years.length}, paths, tpi:paths};
    }
    return runs;
}

export function addConsumptionPath(run, raw){
    const count = run.params.T;
    const consumption = path(raw?.C,count,'consumption');
    const output = path(raw?.Y,count,'GDP');
    const grownOutput = path(run.paths.Y,count,'GDP');
    // Consumption and GDP use the same population/productivity growth factor.
    run.paths.C = consumption.map((value,index) => {
        const factor = finite(grownOutput[index]) && finite(output[index]) && output[index] !== 0
            ? grownOutput[index] / output[index] : null;
        const result = finite(value) && finite(factor) ? value * factor : null;
        return finite(result) ? result : null;
    });
    return run;
}

function groupLabels(run){
    if (!hasProfileWeights(run)) return Array.from({length:integer(run,'J',1)},(_,index) => `Group ${index + 1}`);
    const lambdas = weights(run);
    let cumulative = 0;
    const percentage = value => Number((value * 100).toFixed(2));
    return lambdas.map((weight,index) => {
        const start = cumulative;
        cumulative += weight;
        if (index == 0) return `Bottom ${percentage(cumulative)}%`;
        if (index == lambdas.length - 1) return `Top ${percentage(1 - start)}%`;
        return `${percentage(start)}–${percentage(cumulative)}%`;
    });
}
function calendar(baseline, reform, requested){
    const start = integer(baseline, 'start_year');
    if (integer(reform, 'start_year') != start) missing('Baseline and reform must have the same executed start year.');
    const count = requested ?? Math.min(integer(baseline,'T',1),150);
    if (integer(baseline,'T',1) < count || integer(reform,'T',1) < count) missing(`Both runs must cover ${count} transition periods.`);
    return Array.from({length:count}, (_,index) => start + index);
}
function unstationarized(run, variable, count){
    if (run.paths?.[variable]) return path(run.paths[variable], count, variable);
    const raw = path(run.tpi?.[variable], count, variable);
    if (variable == 'r') return raw;
    const productivity = variable == 'L' ? 0 : parameter(run,'g_y');
    const population = variable == 'w' ? null : path(run.params?.g_n, Math.max(count - 1,0), 'population growth (g_n)');
    let growth = 1;
    return raw.map((value,index) => {
        if (index && population){
            growth = finite(growth) && finite(population[index-1]) ? growth * (1 + population[index-1]) : null;
        }
        const result = finite(value) && finite(growth) ? value * growth * Math.exp(productivity * index) : null;
        return finite(result) ? result : null;
    });
}
function matrix(run, variable){
    const rows = integer(run,'S',1), columns = integer(run,'J',1);
    const values = run.ss?.[variable];
    if (!Array.isArray(values) || values.length != rows || values.some(row => !Array.isArray(row) || row.length != columns)){
        missing(`Executed ${variable} data must contain ${rows} ages and ${columns} income groups.`);
    }
    return values;
}
function sumProducts(values, multipliers){
    let sum = 0;
    for (let index=0; index<values.length; index++){
        if (!finite(values[index]) || !finite(multipliers[index])) return null;
        sum += values[index] * multipliers[index];
    }
    return finite(sum) ? sum : null;
}
function lifecycle(chart, baseline, reform, mode){
    if (!['aggregate','baseline','reform','both'].includes(mode)) missing('Unknown lifecycle profile mode.');
    const runs = mode == 'baseline' ? [['Baseline',baseline]] : mode == 'reform' ? [['Reform',reform]] : [['Baseline',baseline],['Reform',reform]];
    const first = runs[0][1];
    const count = integer(first,'S',1);
    const age = run => scalar(run.params?.starting_age);
    const labelledAges = runs.every(([,run]) => finite(age(run)));
    const start = labelledAges ? age(first) : 1;
    if (runs.length > 1 && (integer(reform,'S',1) != count
        || (labelledAges && age(reform) != age(baseline))
        || (finite(scalar(baseline.params?.ending_age)) && finite(scalar(reform.params?.ending_age))
            && scalar(baseline.params.ending_age) != scalar(reform.params.ending_age)))){
        missing('Baseline and reform must have matching executed age dimensions.');
    }
    const series = [];
    for (const [name,run] of runs){
        const values = matrix(run,chart.variable);
        const scale = value => finite(value) ? value * (RATES.has(chart.variable) ? 100 : 1) : null;
        if (mode == 'aggregate'){
            const lambdas = weights(run);
            series.push({name, scenario:name.toLowerCase(), data:values.map(row => scale(sumProducts(row,lambdas)))});
        }else{
            const groups = groupLabels(run);
            for (let group=0; group<integer(run,'J',1); group++){
                series.push({name:`${name}: ${groups[group]}`, scenario:name.toLowerCase(), group, data:values.map(row => scale(row[group]))});
            }
        }
    }
    return {kind:'line', labels:Array.from({length:count},(_,index) => start + index), xLabel:labelledAges ? 'Age' : 'Model age index',
        unit:RATES.has(chart.variable) ? 'Percent' : 'Model units', series, markers:[]};
}
function ability(chart, baseline, reform){
    const years = calendar(baseline,reform,10);
    const ages = integer(baseline,'S',1), groups = integer(baseline,'J',1);
    if (integer(reform,'S',1) != ages || integer(reform,'J',1) != groups) missing('Both runs must have matching age and income-group dimensions.');
    const reformWeights = weights(reform);
    if (scalar(baseline.params?.starting_age) != scalar(reform.params?.starting_age)
        || scalar(baseline.params?.ending_age) != scalar(reform.params?.ending_age)
        || weights(baseline).some((weight,index) => Math.abs(weight - reformWeights[index]) > 1e-10)){
        missing('Income-group changes require matching executed age and income-group definitions.');
    }
    const omega = baseline.params?.omega;
    if (!Array.isArray(omega) || omega.length < 10) missing('Executed baseline population weights (omega) covering ten years are required.');
    const joint = Array.isArray(omega[0]?.[0]);
    const lambdas = weights(baseline);
    const totals = [baseline,reform].map(run => {
        const values = run.tpi?.[chart.variable];
        if (!Array.isArray(values) || values.length < 10) missing(`A ten-year ${chart.variable} age-by-group path is required.`);
        const sums = Array(groups).fill(0);
        for (let year=0; year<10; year++){
            if (!Array.isArray(values[year]) || values[year].length != ages || !Array.isArray(omega[year]) || omega[year].length != ages){
                missing('Population weights and household paths must have matching age dimensions.');
            }
            for (let age=0; age<ages; age++){
                if (!Array.isArray(values[year][age]) || values[year][age].length != groups
                    || (joint && (!Array.isArray(omega[year][age]) || omega[year][age].length != groups))){
                    missing('Population weights and household paths must have matching income-group dimensions.');
                }
                for (let group=0; group<groups; group++){
                    const weight = joint ? omega[year][age][group] : finite(omega[year][age]) ? omega[year][age] * lambdas[group] : null;
                    const value = values[year][age][group];
                    sums[group] = finite(sums[group]) && finite(value) && finite(weight) && weight >= 0 ? sums[group] + value * weight : null;
                }
            }
        }
        return sums;
    });
    return {kind:'bar', labels:groupLabels(baseline), xLabel:'Lifetime-income group',
        unit:'Percent change', series:[{name:`${years[0]}–${years[9]}`,data:totals[0].map((value,index) => percent(value,totals[1][index]))}], markers:[]};
}

// Inputs are executed run data, not schema defaults. paths may contain exact
// unstationarized outputs returned by the existing time-series table endpoint.
export function buildStandardChart(id, {baseline, reform}, {profileMode='aggregate'} = {}){
    const chart = STANDARD_CHARTS.find(item => item.id == id);
    if (!chart) missing('Unknown standard chart.');
    if (!baseline || !reform) missing('Baseline and reform results are required.');
    let result;
    if (chart.family == 'lifecycle') result = lifecycle(chart,baseline,reform,profileMode);
    else if (chart.family == 'ability') result = ability(chart,baseline,reform);
    else {
        const labels = calendar(baseline,reform), count = labels.length;
        const series = [];
        const isRatio = id.endsWith('_gdp');
        if (isRatio){
            for (const [name,run] of [['Baseline',baseline],['Reform',reform]]){
                const numerator = path(run.tpi?.[chart.variables[0]],count,chart.variables[0]);
                const denominator = path(run.tpi?.Y,count,'GDP');
                series.push({name,scenario:name.toLowerCase(),data:numerator.map((value,index) => ratio(value,denominator[index]))});
            }
        }else for (const variable of chart.variables){
            const base = unstationarized(baseline,variable,count), reformValues = unstationarized(reform,variable,count);
            if (id == 'macro' || id == 'fiscal') series.push({name:LABELS[variable],data:base.map((value,index) => percent(value,reformValues[index]))});
            else for (const [name,values] of [['Baseline',base],['Reform',reformValues]]){
                series.push({name,scenario:name.toLowerCase(),data:values.map(value => finite(value) ? value * (RATES.has(variable) ? 100 : 1) : null)});
            }
        }
        const markers = ['tG1','tG2'].map(name => scalar(baseline.params?.[name]))
            .filter(value => finite(value) && Number.isInteger(value) && value >= 0 && value < count).map(value => labels[0] + value);
        result = {kind:'line',labels,xLabel:'Year',unit:isRatio ? 'Percent of GDP' : id == 'interest' ? 'Percent' : id == 'wage' ? 'Model units' : 'Percent change',series,markers};
    }
    return {title:chart.title,...result};
}
