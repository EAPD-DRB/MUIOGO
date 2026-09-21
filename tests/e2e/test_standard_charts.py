"""Standard-chart views exercise the actual controller and vendored ECharts."""
from .test_shell_smoke import base_url  # noqa: F401


def seed_standard_results(page, base_url):
    page.goto(base_url, wait_until='domcontentloaded')
    page.evaluate('''async () => {
        const html = await fetch('App/View/OGResults.html').then(r => r.text());
        const {default: R} = await import('/App/Controller/OGResults.js');
        document.querySelector('.osy-content').innerHTML = html;
        window.R = R;
        localStorage.setItem('osy-ogc-result-view:ETH', '{}');
        R.workspace = {country_id: 'ETH', country_name: 'Ethiopia'};
        R.selection = {casename: 'Tax policy', base: 'Baseline', reform: 'Reform'};
        R.items = [{case: {casename: 'Tax policy'}, runs: [
            {run_name: 'Baseline', run_type: 'baseline', status: 'completed', time_path: true},
            {run_name: 'Reform', run_type: 'reform', baseline_run: 'Baseline', status: 'completed', time_path: true}
        ]}];
        R.baselines = [{item:R.items[0], run:R.items[0].runs[0]}];
        $('#ogcResultBaseline').html('<option value="0">Baseline</option>');
        $('#ogcResultReform').html('<option>Reform</option>');
        R.charts = {}; R.tables = {}; R.isCurrent = () => true;
        R.base = {Y: 100, c: [[1, 3], [2, 4], [3, 5]]};
        R.reform = {Y: 110, c: [[2, 4], [3, 5], [4, 6]]};
        R.baseParams = {}; R.reformParams = {}; R.schema = {};
        R.groups = ['Bottom 50%', 'Top 50%']; R.ages = [20, 21, 22];
        R.initEvents(); await R.loadECharts();
        $('#ogcResultLoading, #ogcResultEmpty').hide(); $('#ogcResultBody').show();
        const params = {start_year:2025,T:10,S:3,J:2,starting_age:20,ending_age:23,
            lambdas:[0.5,0.5],g_y:0,g_n:Array(10).fill(0),omega:Array.from({length:10},()=>[0.2,0.3,0.5])};
        const tpi = {Y:Array(10).fill(100),K:Array(10).fill(200),L:Array(10).fill(40),C:Array(10).fill(60),
            D:Array(10).fill(50),TR:Array(10).fill(10),G:Array(10).fill(20),total_tax_revenue:Array(10).fill(25),
            r:Array(10).fill(0.04),w:Array(10).fill(1.2),c:Array.from({length:10},()=>[[1,3],[2,4],[3,5]])};
        window.chartData = {baseline:{ss:R.base,tpi,params},reform:{ss:R.reform,
            tpi:{...tpi,Y:Array(10).fill(110),c:Array.from({length:10},()=>[[2,4],[3,5],[4,6]])},params}};
        R.baseParams = params; R.reformParams = params;
        window.originalStandardLoader = R.loadStandardData.bind(R);
        R.loadStandardData = async () => window.chartData;
        R.renderExploreControls(); R.openTab('explore');
    }''')


def test_standard_macro_and_lifecycle_render_with_units(page, base_url):
    seed_standard_results(page, base_url)
    page.select_option('#ogcExplorePreset', 'macro')
    page.wait_for_function("R.charts.ogcExploreChart?.getOption().series.length === 4")
    result = page.evaluate('''() => {
        const o=R.charts.ogcExploreChart.getOption();
        return {x:o.xAxis[0].data,series:o.series.map(s=>s.data),unit:o.yAxis[0].name};
    }''')
    assert result['x'] == list(range(2025, 2035))
    assert all(abs(value - 10) < 1e-8 for value in result['series'][0])
    assert result['unit'] == 'Percent change'
    page.select_option('#ogcExplorePreset', 'lifecycle_c')
    page.wait_for_function("R.charts.ogcExploreChart?.getOption().xAxis[0].data.length === 3")
    result = page.evaluate('''() => {
        const o=R.charts.ogcExploreChart.getOption();
        return {x:o.xAxis[0].data,series:o.series.map(s=>s.data)};
    }''')
    assert result == {'x': [20,21,22], 'series': [[2,3,4],[3,4,5]]}
    page.select_option('#ogcExplorePreset', 'individual')
    assert page.locator('#ogcExploreVariable').is_visible()


def test_standard_ability_preserves_weighted_comparison(page, base_url):
    seed_standard_results(page, base_url)
    page.select_option('#ogcExplorePreset', 'ability_c')
    page.wait_for_function("R.charts.ogcExploreChart?.getOption().series[0].type === 'bar'")
    values = page.evaluate('R.charts.ogcExploreChart.getOption().series[0].data')
    assert abs(values[0] - 100/2.3) < 1e-8
    assert abs(values[1] - 100/4.3) < 1e-8


def test_standard_view_ignores_late_response_after_individual_selected(page, base_url):
    seed_standard_results(page, base_url)
    page.evaluate('() => { R.loadStandardData = () => new Promise(resolve => window.finishStandard = resolve); }')
    page.select_option('#ogcExplorePreset', 'macro')
    page.wait_for_function("typeof window.finishStandard === 'function'")
    page.select_option('#ogcExplorePreset', 'individual')
    title = page.locator('#ogcExploreTitle').inner_text()
    page.evaluate('finishStandard(chartData)')
    page.wait_for_timeout(100)
    assert page.locator('#ogcExploreTitle').inner_text() == title
    assert page.locator('#ogcExploreVariable').is_visible()


def test_standard_transition_choices_require_both_runs_and_save_view(page, base_url):
    seed_standard_results(page, base_url)
    page.evaluate('''() => {
        R.items[0].runs[1].time_path = false;
        R.renderStandardControls();
    }''')
    assert page.evaluate("document.querySelector('#ogcExplorePreset option[value=macro]') === null")
    assert not page.locator('#ogcExplorePreset option[value="lifecycle_c"]').evaluate('(option) => option.disabled')
    page.select_option('#ogcExplorePreset', 'lifecycle_c')
    page.select_option('#ogcStandardProfileMode', 'both')
    page.click('#ogcSaveView')
    saved = page.evaluate('R.readSaved()')
    assert saved['preset'] == 'lifecycle_c'
    assert saved['profileMode'] == 'both'
    page.wait_for_function('R.charts.ogcExploreChart?.getOption().series.length === 4')
    export = page.evaluate('''() => {
        let href;
        const click = HTMLAnchorElement.prototype.click;
        HTMLAnchorElement.prototype.click = function(){href=this.href;};
        R.exportChart('ogcExploreChart');
        HTMLAnchorElement.prototype.click = click;
        return decodeURIComponent(href.slice(href.indexOf(',')+1));
    }''')
    assert 'Consumption by age' in export
    assert 'Baseline: Bottom 50%' in export
    styles = page.evaluate('R.charts.ogcExploreChart.getOption().series.map(s=>({type:s.lineStyle.type,color:s.itemStyle.color}))')
    assert [s['type'] for s in styles] == ['solid','solid','dashed','dashed']
    assert styles[0]['color'] == styles[2]['color']
    assert styles[1]['color'] == styles[3]['color']


def test_standard_loader_uses_existing_endpoints_caches_and_retries(page, base_url):
    seed_standard_results(page, base_url)
    result = page.evaluate('''async () => {
        const {Ogc}=await import('/Classes/Ogc.Class.js');
        const calls=[];
        const rows=Array.from({length:10},(_,index)=>({Year:2025+index,
            'GDP ($Y_t$): Baseline':100,'GDP ($Y_t$): Reform':110,
            'Capital Stock ($K_t$): Baseline':200,'Capital Stock ($K_t$): Reform':200,
            'Labor ($L_t$): Baseline':40,'Labor ($L_t$): Reform':40}));
        Ogc.getResultTable=async (...args)=>{calls.push(args);return rows;};
        Ogc.getTPIVars=async (...args)=>{calls.push(args);return chartData[args[2]=='Baseline'?'baseline':'reform'].tpi;};
        R.standardData={};
        await window.originalStandardLoader({family:'lifecycle'});
        const profileCalls=calls.length;
        const macro={family:'aggregate',id:'macro'};
        await Promise.all([window.originalStandardLoader(macro),window.originalStandardLoader(macro)]);
        await window.originalStandardLoader({family:'aggregate',id:'interest'});
        const count=calls.length;
        R.standardData={};
        Ogc.getResultTable=async()=>{throw new Error('Temporary failure');};
        await window.originalStandardLoader(macro).catch(()=>{});
        Ogc.getResultTable=async()=>rows;
        const retried=await window.originalStandardLoader(macro);
        return {profileCalls,count,table:calls[0],variables:calls.slice(1,3).map(call=>call[3]),
            start:retried.baseline.params.start_year,consumption:retried.reform.paths.C[0]};
    }''')
    assert result == {'profileCalls':0,'count':3,
        'table':['getTimeSeriesTable','ETH','Tax policy','Baseline','Reform',{'stationarized':False}],
        'variables':[['C','Y'],['C','Y']],'start':2025,'consumption':60}


def test_profiles_work_without_metadata_and_offer_only_supported_modes(page, base_url):
    seed_standard_results(page, base_url)
    page.evaluate('''() => {
        R.baseParams={};R.reformParams={};R.loadStandardData=window.originalStandardLoader;
        R.renderStandardControls();
    }''')
    page.select_option('#ogcExplorePreset','lifecycle_c')
    page.wait_for_function("R.charts.ogcExploreChart?.getOption().xAxis[0].name === 'Model age index'")
    result=page.evaluate('''() => {
        const option=R.charts.ogcExploreChart.getOption();
        return {labels:option.xAxis[0].data,names:option.series.map(s=>s.name),
            values:option.series.map(s=>s.data),mode:$('#ogcStandardProfileMode').val(),
            average:$('#ogcStandardProfileMode option[value="aggregate"]').length,
            ability:$('#ogcExplorePreset option[value="ability_c"]').length,
            note:$('#ogcStandardDescription').text()};
    }''')
    assert result['labels']==[1,2,3]
    assert result['names']==['Baseline: Group 1','Baseline: Group 2','Reform: Group 1','Reform: Group 2']
    assert result['values']==[[1,2,3],[3,4,5],[2,3,4],[4,5,6]]
    assert result['mode']=='both'
    assert result['average'] == 0 and result['ability'] == 0
    assert 'not included' not in result['note']


def test_overview_cell_opens_individual_lifecycle_even_after_standard_chart(page, base_url):
    seed_standard_results(page, base_url)
    page.select_option('#ogcExplorePreset', 'lifecycle_c')
    result = page.evaluate("""() => {
        R.renderDistributionControls(); R.renderProfileControls(); R.renderDistribution();
        R.charts.ogcDistributionChart.trigger('click',{value:[0,1,10]});
        return {preset:$('#ogcExplorePreset').val(),variable:$('#ogcExploreVariable').val(),
            group:$('#ogcExploreGroup').val(),view:$('#ogcExploreView').val(),title:$('#ogcExploreTitle').text()};
    }""")
    assert result == {'preset':'individual','variable':'c','group':'1','view':'profile','title':'Household consumption'}
