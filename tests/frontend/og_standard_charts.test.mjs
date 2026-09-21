import assert from 'node:assert/strict';
import {test} from 'node:test';
import {readFileSync} from 'node:fs';
import {STANDARD_CHARTS, buildStandardChart, resultRun, hasProfileWeights, timeSeriesRuns, addConsumptionPath} from '../../WebAPP/App/Model/OGStandardCharts.js';

function fixture(){
    const params = {start_year:2026,T:10,S:2,J:2,starting_age:21,ending_age:23,
        lambdas:[0.25,0.75],omega:Array.from({length:10},()=>[0.25,0.75]),g_n:Array(10).fill(0),g_y:0,tG1:2,tG2:5};
    const tpi = Object.fromEntries(['Y','K','L','C','D','TR','total_tax_revenue','G','r','w'].map(name=>[name,Array(10).fill(name=='r' ? 0.04 : 10)]));
    const ss = {};
    for (const name of ['c','n','b_sp1','etr','mtrx','mtry','before_tax_income']){
        ss[name]=[[1,3],[5,7]];
        tpi[name]=Array.from({length:10},()=>[[1,3],[5,7]]);
    }
    const baseline={params,tpi,ss};
    return {baseline,reform:structuredClone(baseline)};
}
const close = (actual,expected) => assert.ok(Math.abs(actual-expected)<1e-10,`${actual} != ${expected}`);

test('catalog covers each standard family and all presets calculate',()=>{
    const input=fixture();
    assert.equal(STANDARD_CHARTS.length,20);
    for (const chart of STANDARD_CHARTS){
        const result=buildStandardChart(chart.id,input);
        assert.ok(result.series.length);
        assert.ok(result.series.every(series=>series.data.length===result.labels.length));
        assert.ok(chart.description && chart.variables.length);
    }
});

test('aggregate changes undo each run’s distinct population and productivity growth',()=>{
    const input=fixture();
    input.baseline.params.g_n=Array(10).fill(0.1);
    input.reform.params.g_n=Array(10).fill(0.2);
    input.baseline.params.g_y=Math.log(1.02);
    input.reform.params.g_y=Math.log(1.04);
    const macro=buildStandardChart('macro',input);
    assert.deepEqual(macro.labels,[2026,2027,2028,2029,2030,2031,2032,2033,2034,2035]);
    assert.deepEqual(macro.markers,[2028,2031]);
    close(macro.series[0].data[2],((1.2**2*1.04**2)/(1.1**2*1.02**2)-1)*100);
    close(macro.series[2].data[2],((1.2**2)/(1.1**2)-1)*100);
    close(buildStandardChart('fiscal',input).series[0].data[2],macro.series[0].data[2]);
    close(buildStandardChart('wage',input).series[0].data[2],10*1.02**2);
    close(buildStandardChart('interest',input).series[0].data[2],4);
});

test('GDP ratios use each run’s GDP and retain missing and zero-denominator slots',()=>{
    const input=fixture();
    input.baseline.tpi.G=[2,null,3,...Array(7).fill(2)];
    input.baseline.tpi.Y=[10,10,0,...Array(7).fill(10)];
    input.reform.tpi.G=Array(10).fill(8);input.reform.tpi.Y=Array(10).fill(20);
    const result=buildStandardChart('spending_gdp',input);
    assert.deepEqual(result.series[0].data.slice(0,3),[20,null,null]);
    assert.equal(result.series[1].data[0],40);
    assert.equal(result.series[0].data.length,10);
});

test('ability bars weight both runs using baseline omega, sum ten years before percentage',()=>{
    const input=fixture();
    input.reform.params.omega=Array.from({length:10},()=>[0.9,0.1]);
    input.reform.tpi.c=Array.from({length:10},()=>[[3,4],[6,8]]);
    const result=buildStandardChart('ability_c',input);
    close(result.series[0].data[0],((3*.25+6*.75)/(1*.25+5*.75)-1)*100);
    close(result.series[0].data[1],((4*.25+8*.75)/(3*.25+7*.75)-1)*100);
    input.baseline.params.omega=Array.from({length:10},()=>[[.1,.2],[.3,.4]]);
    assert.deepEqual(result.labels,['Bottom 25%','Top 75%']);
    const joint=buildStandardChart('ability_c',input);
    close(joint.series[0].data[1],((4*.2+8*.4)/(3*.2+7*.4)-1)*100);
    input.reform.tpi.c[4][1][0]=null;
    assert.equal(buildStandardChart('ability_c',input).series[0].data[0],null);
});

test('SS aggregate uses each run’s own income weights and no population weights',()=>{
    const input=fixture();input.reform.params.lambdas=[.75,.25];
    input.baseline.params.omega=[];input.reform.params.omega=[];
    const result=buildStandardChart('lifecycle_c',input);
    assert.deepEqual(result.labels,[21,22]);
    assert.deepEqual(result.series.map(series=>series.data),[[2.5,6.5],[1.5,5.5]]);
    const both=buildStandardChart('lifecycle_c',input,{profileMode:'both'});
    assert.deepEqual(both.series.map(series=>series.name),['Baseline: Bottom 25%','Baseline: Top 75%','Reform: Bottom 75%','Reform: Top 25%']);
    input.baseline.ss.c[0][0]=null;
    assert.equal(buildStandardChart('lifecycle_c',input).series[0].data[0],null);
    const grouped=buildStandardChart('lifecycle_c',input,{profileMode:'baseline'});
    assert.deepEqual(grouped.series.map(series=>series.data),[[null,5],[3,7]]);
    assert.equal(buildStandardChart('lifecycle_etr',input).series[0].data[0],250);
});

test('missing executed metadata and mismatched calendars never invent values',()=>{
    const input=fixture();
    input.reform.params.start_year=2027;
    assert.throws(()=>buildStandardChart('macro',input),/same executed start year/);
    input.reform.params.start_year=2026;delete input.baseline.params.g_n;
    assert.throws(()=>buildStandardChart('macro',input),/population growth/);
    input.baseline.paths={Y:Array(10).fill(10),K:Array(10).fill(10),L:Array(10).fill(10),C:Array(10).fill(10)};
    assert.equal(buildStandardChart('macro',input).series[0].data[0],0);
    delete input.baseline.params.lambdas;
    assert.throws(()=>buildStandardChart('lifecycle_c',input),/lambdas/);
    assert.equal(buildStandardChart('lifecycle_c',input,{profileMode:'baseline'}).series.length,2);
    input.baseline.params.T=9;
    assert.throws(()=>buildStandardChart('ability_c',input),/10 transition periods/);
});

test('bounded metadata supports 150-period paths and calculations do not mutate inputs',()=>{
    const input=fixture();
    for (const run of [input.baseline,input.reform]){
        run.params.T=200;run.params.g_n=Array(149).fill(0);
        for (const name of ['Y','K','L','C']) run.tpi[name]=Array(200).fill(2);
    }
    const original=structuredClone(input);
    assert.equal(buildStandardChart('macro',input).labels.length,150);
    assert.deepEqual(input,original);
});

test('paired lifecycle series carry scenario and income-group identity for distinct styling',()=>{
    const both=buildStandardChart('lifecycle_c',fixture(),{profileMode:'both'});
    assert.deepEqual(both.series.map(({scenario,group})=>[scenario,group]),
        [['baseline',0],['baseline',1],['reform',0],['reform',1]]);
});

test('income-group changes reject different age definitions and group boundaries',()=>{
    const input=fixture();
    input.reform.params.starting_age=22;
    assert.throws(()=>buildStandardChart('ability_c',input),/matching executed age and income-group definitions/);
    input.reform.params.starting_age=21;
    input.reform.params.lambdas=[.5,.5];
    assert.throws(()=>buildStandardChart('ability_c',input),/matching executed age and income-group definitions/);
    assert.doesNotThrow(()=>buildStandardChart('lifecycle_c',input));
});


test('existing time-series rows supply calendars and growth-adjusted chart paths',()=>{
    const labels={Y:'GDP ($Y_t$)',K:'Capital Stock ($K_t$)',L:'Labor ($L_t$)',D:'Government Debt ($D_t$)',
        TR:'Government Transfers ($TR_t$)',total_tax_revenue:'Total tax revenue ($REV_t$)',
        G:'Government Consumption Expenditures ($G_t$)',r:'Real interest rate ($r_t$)',w:'Wage rate ($w_t$)'};
    const rows=Array.from({length:3},(_,index)=>{
        const row={Year:2030+index};
        for(const [variable,label] of Object.entries(labels)){
            row[label+': Baseline']=variable==='r'?.04:10*(1.02**index);
            row[label+': Reform']=variable==='r'?.05:12*(1.03**index);
        }
        return row;
    });
    const input=timeSeriesRuns(rows);
    addConsumptionPath(input.baseline,{Y:[10,10,10],C:[6,6,6]});
    addConsumptionPath(input.reform,{Y:[12,12,12],C:[7,7,7]});
    const macro=buildStandardChart('macro',input);
    assert.deepEqual(macro.labels,[2030,2031,2032]);
    close(macro.series[3].data[2],(7*1.03**2/(6*1.02**2)-1)*100);
    assert.deepEqual(buildStandardChart('interest',input).series.map(s=>s.data),[[4,4,4],[5,5,5]]);
    assert.deepEqual(buildStandardChart('debt_gdp',input).series[0].data,[100,100,100]);
    assert.deepEqual(buildStandardChart('wage',input).series[1].data,rows.map(row=>row['Wage rate ($w_t$): Reform']));
    rows[1].Year=2033;
    assert.throws(()=>timeSeriesRuns(rows),/consecutive calendar years/);
});

test('table adapter preserves unavailable values and refuses ambiguous captions',()=>{
    const rows=[{Year:2025,'GDP ($Y_t$): Baseline':null,'GDP ($Y_t$): Reform':0},
        {Year:2026,'GDP ($Y_t$): Baseline':0,'GDP ($Y_t$): Reform':20}];
    const data=timeSeriesRuns(rows);
    addConsumptionPath(data.baseline,{Y:[1,0],C:[4,5]});
    assert.deepEqual(data.baseline.paths.C,[null,null]);
    assert.deepEqual(data.baseline.paths.Y,[null,0]);
    rows[0]['GDP: Baseline']=10;
    assert.throws(()=>timeSeriesRuns(rows),/Ambiguous/);
    assert.throws(()=>timeSeriesRuns([]),/No transition/);
});

test('unweighted lifecycle profiles need no schema or executed metadata endpoint',()=>{
    const ss={c:[[1,2],[3,null],[5,6]]};
    const run=resultRun(ss);
    assert.equal(hasProfileWeights(run),false);
    const data={baseline:run,reform:resultRun(structuredClone(ss))};
    const chart=buildStandardChart('lifecycle_c',data,{profileMode:'both'});
    assert.equal(chart.xLabel,'Model age index');
    assert.deepEqual(chart.labels,[1,2,3]);
    assert.deepEqual(chart.series[1].data,[2,null,6]);
    assert.equal(chart.series[0].name,'Baseline: Group 1');
    assert.throws(()=>buildStandardChart('lifecycle_c',data),/lambdas/);
    data.baseline.params.lambdas=[null,1];
    assert.equal(hasProfileWeights(data.baseline),false);
    assert.doesNotThrow(()=>buildStandardChart('lifecycle_c',data,{profileMode:'both'}));
});


test('existing API table adapter reproduces native OG-Core aggregate plots',()=>{
    const fixture=JSON.parse(readFileSync(new URL('./fixtures/og_time_series.json',import.meta.url)));
    const data=timeSeriesRuns(fixture.rows);
    for(const name of ['baseline','reform']) addConsumptionPath(data[name],fixture.raw[name]);
    for(const [preset,expected] of Object.entries(fixture.expected)){
        const actual=buildStandardChart(preset,data);
        assert.deepEqual(actual.labels,[2030,2031,2032]);
        assert.equal(actual.series.length,expected.length,preset);
        actual.series.forEach((series,index)=>series.data.forEach((value,year)=>close(value,expected[index][year])));
    }
});
