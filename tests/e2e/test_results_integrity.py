"""Results data alignment checks against the real frontend module."""

from .test_shell_smoke import base_url  # noqa: F401


def test_results_missing_values_keep_table_and_chart_positions(page, base_url):
    page.goto(base_url, wait_until="domcontentloaded")
    result = page.evaluate("""async () => {
        const markup = await fetch('App/View/OGResults.html').then(r => r.text());
        const {default: Results} = await import(new URL('App/Controller/OGResults.js', location.href).href);
        document.querySelector('.osy-content').innerHTML = markup;
        Results.groups = ['Bottom 50%', 'Top 50%'];
        Results.ages = [31, 32, 33];
        Results.base = {c: [[0, 2], [null, 4], [3, 6]], Y: [1, null, 3]};
        Results.reform = {c: [[2, 3], [4, 5], [6, null]], Y: [2, 4, 6]};
        Results.renderExploreTable('c', 'pct');
        const cells = [...document.querySelectorAll('#ogcExploreTable tbody tr:first-child td')].map(c => c.textContent);
        const profile = Results.profileOption('c', 0, 'levels');
        const delta = Results.profileOption('c', 0, 'diff');
        $('#ogcExploreVariable').html('<option>Y</option>');
        $('#ogcExploreMeasure').html('<option>levels</option>');
        Results.refreshExploreViews();
        const views = [...document.querySelector('#ogcExploreView').options].map(o => o.value);
        Results.renderExploreTable('Y', 'levels');
        const vectorRows = [...document.querySelectorAll('#ogcExploreTable tbody tr')].map(r => [...r.cells].map(c => c.textContent));
        Results.activeTableKey = 'macro';
        Results.renderTableRows([{Variable: 'GDP', Baseline: null, Reform: 50}]);
        const serverCells = [...document.querySelectorAll('#ogcResultTable td')].map(c => c.textContent);
        return {cells, profile: profile.series.map(s => s.data), ages: profile.xAxis.data,
            delta: delta.series[0].data, views, vectorRows, serverCells};
    }""")
    assert result['cells'] == ['31', '', '50']
    assert result['serverCells'] == ['GDP', '', '50']
    assert result['ages'] == [31, 32, 33]
    assert result['profile'] == [[0, None, 3], [2, 4, 6]]
    assert result['delta'] == [2, None, 3]
    assert result['views'] == ['table']
    assert result['vectorRows'] == [['1', '1', '2'], ['2', '', '4'], ['3', '3', '6']]


def test_results_profile_choices_require_compatible_data(page, base_url):
    page.goto(base_url, wait_until="domcontentloaded")
    result = page.evaluate("""async () => {
        const markup = await fetch('App/View/OGResults.html').then(r => r.text());
        const {default: Results} = await import(new URL('App/Controller/OGResults.js', location.href).href);
        document.querySelector('.osy-content').innerHTML = markup;
        Results.groups = ['Bottom', 'Top']; Results.ages = [31, 32, 33];
        Results.base = {c: [[1, 2], [3, 4], [5, 6]], n: [[1, 2], [3, 4], [5, 6]], b_s: [[1, 2], [3, 4], [5, 6]]};
        Results.reform = {n: [[1, 2]], b_s: [[2, 3], [4, 5], [6, 7]]};
        Results.renderProfileControls();
        const choices = [...document.querySelector('#ogcProfileVariable').options].map(o => o.value);
        const selected = document.querySelector('#ogcProfileVariable').value;
        Results.charts = {}; Results.reform = {};
        Results.renderProfileControls(); Results.renderProfile();
        return {choices, selected, empty: document.querySelector('#ogcProfileChart').textContent,
            disabled: document.querySelector('#ogcProfileVariable').disabled};
    }""")
    assert result['choices'] == ['b_s']
    assert result['selected'] == 'b_s'
    assert 'unavailable' in result['empty']
    assert result['disabled'] is True


def test_results_saved_pair_library_retry_and_export_title(page, base_url):
    page.goto(base_url, wait_until="domcontentloaded")
    result = page.evaluate("""async () => {
        const markup = await fetch('App/View/OGResults.html').then(r => r.text());
        const {default: Results} = await import(new URL('App/Controller/OGResults.js', location.href).href);
        document.querySelector('.osy-content').innerHTML = markup;
        Results.workspace = {country_id: 'test'};
        Results.selection = {casename: 'Case', base: 'Base', reform: 'Second'};
        Results.saveView();
        const saved = Results.readSaved();
        Results.items = [{case: {casename: 'Case'}, runs: [
            {run_name: 'Base', run_type: 'baseline', status: 'completed'},
            {run_name: 'First', run_type: 'reform', baseline_run: 'Base', status: 'completed'},
            {run_name: 'Second', run_type: 'reform', baseline_run: 'Base', status: 'completed'}]}];
        Results.baselines = [{item:Results.items[0], run:Results.items[0].runs[0]}];
        $('#ogcResultBaseline').html('<option value="0">Base</option>');
        const load = Results.loadComparison; Results.loadComparison = () => {};
        Results.renderReformOptions(saved);
        const restored = $('#ogcResultReform').val();
        Results.renderReformOptions({...saved, reform: 'Deleted'});
        const fallback = $('#ogcResultReform').val();
        Results.loadComparison = load;
        $('#ogcResultReform').val('Second');
        const append = document.head.appendChild;
        let scripts = [];
        document.head.appendChild = function(node){ scripts.push(node); return node; };
        const first = Results.loadECharts(); const second = Results.loadECharts();
        const shared = first === second;
        const failed = first.catch(() => true);
        scripts[0].dispatchEvent(new Event('error')); await failed;
        const retry = Results.loadECharts(); const retryFailure = retry.catch(() => true);
        scripts[1].dispatchEvent(new Event('error')); await retryFailure;
        document.head.appendChild = append;
        await Results.loadECharts();
        Results.charts = {};
        const element = document.querySelector('#ogcExploreChart');
        element.style.width = '500px'; element.style.height = '300px';
        Results.setChart('ogcExploreChart', {animation: false, aria: {description: 'Consumption <baseline> & reform by age for each lifetime income group over the full model horizon'}, legend: {data: ['Baseline']}, xAxis: {data: ['31']}, yAxis: {}, series: [{name: 'Baseline', type: 'bar', data: [1]}]});
        let artifact, filename;
        const click = HTMLAnchorElement.prototype.click;
        HTMLAnchorElement.prototype.click = function(){ artifact = this.href; filename = this.download; };
        Results.exportChart('ogcExploreChart'); HTMLAnchorElement.prototype.click = click;
        const svg = new DOMParser().parseFromString(decodeURIComponent(artifact.split(',').slice(1).join(',')), 'image/svg+xml');
        return {restored, fallback, baseline: $('#ogcResultBaselineName').text(), shared,
            scripts: scripts.length, title: [...svg.querySelectorAll('text')].map(t => t.textContent).join(' '),
            titleLines: [...svg.documentElement.children].filter(n => n.tagName == 'text').length,
            height: Number(svg.documentElement.getAttribute('height')), parseErrors: svg.querySelectorAll('parsererror').length, filename};
    }""")
    assert result['restored'] == 'Second'
    assert result['fallback'] == 'First'
    assert result['baseline'] == 'Base'
    assert result['shared'] is True
    assert result['scripts'] == 2
    assert 'Consumption <baseline> & reform by age for each lifetime income group over the full model horizon' in result['title']
    assert 'Baseline' in result['title']
    assert result['titleLines'] > 1
    assert result['height'] > 300
    assert result['parseErrors'] == 0
    assert result['filename'] == 'ogcore-Base-Second-explore.svg'


def test_results_policy_compares_scalars_without_flattening_arrays(page, base_url):
    page.goto(base_url, wait_until="domcontentloaded")
    result = page.evaluate("""async () => {
        const markup = await fetch('App/View/OGResults.html').then(r => r.text());
        const {default: Results} = await import(new URL('App/Controller/OGResults.js', location.href).href);
        document.querySelector('.osy-content').innerHTML = markup;
        Results.schema = {frisch: {default: 0.4}};
        Results.baseParams = {frisch: [[0.5]], array: [1, 2], text: '<baseline>', missing: 2};
        Results.reformParams = {array: [2, 3], text: '<reform>'};
        Results.renderPolicy();
        return [...document.querySelectorAll('.ogc-policy-item')].map(item => ({name: item.querySelector('code').textContent, value: item.querySelector('span')?.textContent || '', elements: item.querySelectorAll('baseline, reform').length}));
    }""")
    rows = {row['name']: row for row in result}
    assert rows['frisch']['value'] == 'Baseline: 0.5 → Reform: 0.4'
    assert rows['array']['value'] == ''
    assert rows['missing']['value'] == ''
    assert rows['text']['value'] == 'Baseline: <baseline> → Reform: <reform>'
    assert rows['text']['elements'] == 0


def test_results_unavailable_parameters_and_inequality_are_not_zero(page, base_url):
    page.goto(base_url, wait_until='domcontentloaded')
    result = page.evaluate('''async () => {
        document.querySelector('.osy-content').innerHTML = await fetch('/App/View/OGResults.html').then(r => r.text());
        const {default:R} = await import('/App/Controller/OGResults.js');
        R.paramsUnavailable = true; R.schema = {starting_age:{default:20},lambdas:{default:[.5,.5]}};
        R.baseParams = {}; R.reformParams = {}; R.base = {c:[[1,2],[3,4]]}; R.reform = R.base;
        R.renderPolicy(); R.setDimensions();
        R.tables = {ineq:[{'Inequality Measure':'Gini Coefficient',Baseline:null,Reform:.4},
            {'Inequality Measure':'Top 10% Share',Baseline:'',Reform:.2}]};
        R.renderInequality();
        return {policy:$('#ogcPolicyChange').text(),ages:R.ages,groups:R.groups,
            metrics:$('#ogcInequalityMetrics').text(),note:$('#ogcDimensionNote').text()};
    }''')
    assert 'unavailable' in result['policy']
    assert 'No parameter changes' not in result['policy']
    assert result['ages'] == [1, 2]
    assert result['groups'] == ['Group 1', 'Group 2']
    assert '+0.4' not in result['metrics']
    assert '0 →' not in result['metrics']
    assert 'Run parameters could not be loaded' in result['note']


def test_results_baseline_selector_restores_all_named_baselines(page, base_url):
    page.goto(base_url, wait_until='domcontentloaded')
    result = page.evaluate('''async () => {
        document.querySelector('.osy-content').innerHTML = await fetch('/App/View/OGResults.html').then(r => r.text());
        const {default:R} = await import('/App/Controller/OGResults.js');
        const {Ogc} = await import('/Classes/Ogc.Class.js');
        R.workspace = {country_id:'test'}; R.isCurrent = () => true;
        R.loadComparison = () => {};
        Ogc.getRuns = async () => ({runs:[
            {run_type:'baseline',run_name:'baseline',status:'completed'},
            {run_type:'baseline',run_name:'Alternative baseline',status:'completed'},
            {run_type:'reform',run_name:'Tax reform',baseline_run:'baseline',status:'completed'},
            {run_type:'reform',run_name:'Spending reform',baseline_run:'Alternative baseline',status:'completed'}]});
        R.readSaved = () => ({country_id:'test',casename:'Current policy',base:'Alternative baseline',reform:'Spending reform'});
        await R.prepareCases([{country_id:'test',casename:'Current policy'}]);
        const saved = {...R.currentBaseline(R.currentItem())};
        const savedReform = $('#ogcResultReform').val();
        $('#ogcResultBaseline').val('0'); R.renderReformOptions();
        return {labels:[...document.querySelector('#ogcResultBaseline').options].map(o => o.text),
            saved:saved.run_name,savedReform,reforms:[...document.querySelector('#ogcResultReform').options].map(o=>o.text),
            context:[...document.querySelectorAll('.ogc-result-context label')].map(e=>e.textContent)};
    }''')
    assert result == {'labels':['Current policy','Alternative baseline'], 'saved':'Alternative baseline',
                      'savedReform':'Spending reform','reforms':['Tax reform'],'context':['Baseline','Reform']}


def test_results_views_respect_variable_meaning_and_matching_dimensions(page, base_url):
    page.goto(base_url, wait_until='domcontentloaded')
    result = page.evaluate('''async () => {
        document.querySelector('.osy-content').innerHTML = await fetch('/App/View/OGResults.html').then(r => r.text());
        const {default:R} = await import('/App/Controller/OGResults.js');
        R.groups = ['Bottom','Top']; R.ages = [20,21,22];
        R.base = {Y:[1,2],c:[[1,2],[3,4],[5,6]],euler_savings:[[1,2],[3,4],[5,6]],r:.04};
        R.reform = structuredClone(R.base);
        const options = name => {
            $('#ogcExploreVariable').html(`<option>${name}</option>`);
            R.refreshExploreMeasures(); R.refreshExploreViews();
            return {views:[...document.querySelector('#ogcExploreView').options].map(o=>o.value),
                measures:[...document.querySelector('#ogcExploreMeasure').options].map(o=>o.value)};
        };
        const vector=options('Y'), household=options('c'), diagnostic=options('euler_savings'), rate=options('r');
        R.reform.c.pop(); const mismatch=options('c');
        R.baseParams={starting_age:20,lambdas:[.5,.5]};R.reformParams={starting_age:30,lambdas:[.5,.5]};R.schema={};
        R.reform.c=structuredClone(R.base.c);R.setDimensions();const ages=R.ages, shifted=options('c');
        return {vector,household,diagnostic,rate,mismatch,shifted,ages};
    }''')
    assert result['vector']['views'] == ['table']
    assert result['diagnostic']['views'] == ['table']
    assert result['household']['views'] == ['heatmap','profile','table']
    assert result['rate']['measures'] == ['pp','levels']
    assert result['mismatch']['views'] == ['table']
    assert result['shifted']['views'] == ['table']
    assert result['ages'] == [20,21,22]


def test_results_previous_visit_cannot_replace_current_comparison(page, base_url):
    page.goto(base_url, wait_until='domcontentloaded')
    result = page.evaluate('''async () => {
        document.querySelector('.osy-content').innerHTML = await fetch('/App/View/OGResults.html').then(r => r.text());
        const {default:R} = await import('/App/Controller/OGResults.js');
        const {Ogc} = await import('/Classes/Ogc.Class.js');
        history.replaceState(null,'','#/OGResults');
        localStorage.setItem('osy-pageId','OGResults');
        localStorage.setItem('osy-ogc-country',JSON.stringify({country_id:'test',country_name:'Test'}));
        let visit=1, started; const pending=[];
        const firstStarted = new Promise(resolve => started=resolve);
        Ogc.getCases = async () => [{country_id:'test',casename:visit == 1 ? 'Old baseline' : 'Current baseline'}];
        Ogc.getRuns = async () => ({runs:[
            {run_type:'baseline',run_name:'baseline',status:'completed'},
            {run_type:'reform',run_name:'Tax reform',baseline_run:'baseline',status:'completed'}]});
        Ogc.getParams = async () => {throw new Error('Parameters unavailable');};
        Ogc.getParameterSchema = async () => ({});
        Ogc.getIneqTable = async () => [];
        Ogc.getSSVars = async (_,casename) => {
            if (casename == 'Old baseline') return new Promise(resolve => {
                pending.push(resolve); if (pending.length == 2) started();
            });
            return {Y:200};
        };
        R.onLoad(); await firstStarted;
        visit=2;
        const render=R.renderAll;
        const currentLoaded=new Promise(resolve => R.renderAll=()=>{render.call(R);resolve();});
        R.onLoad(); await currentLoaded;
        pending.forEach(resolve=>resolve({Y:100}));
        await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
        return {selection:R.selection,Y:R.base.Y,policy:$('#ogcPolicyChange').text(),
            baseline:$('#ogcResultBaselineName').text()};
    }''')
    assert result['selection']['casename'] == 'Current baseline'
    assert result['Y'] == 200
    assert result['baseline'] == 'Current baseline'
    assert 'unavailable' in result['policy']
