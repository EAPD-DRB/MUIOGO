import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import Pivot from '../../WebAPP/AppResults/Controller/Pivot.js';
import { Base } from '../../WebAPP/Classes/Base.Class.js';
import { Osemosys } from '../../WebAPP/Classes/Osemosys.Class.js';
import { Message } from '../../WebAPP/Classes/Message.Class.js';
import { Html } from '../../WebAPP/Classes/Html.Class.js';
import { DataModelResult } from '../../WebAPP/Classes/DataModelResult.Class.js';
import { ResultAggregator } from '../../WebAPP/Classes/ResultAggregator.Class.js';
import { ResultLayoutState } from '../../WebAPP/Classes/ResultLayoutState.Class.js';

const fixture = JSON.parse(readFileSync(new URL('./fixtures/clews_results.json', import.meta.url)));
const clone = value => structuredClone(value);
const controls = new Map([['#cmbViews', {}]]);
globalThis.document = { querySelector: selector => controls.get(selector) };
globalThis.localStorage = { getItem: () => null };
globalThis.jsonLogic = { apply: rule => rule };
globalThis.$ = {
    each: (object, callback) => {
        for (const [key, value] of Object.entries(object || {})) {
            if (callback(Array.isArray(object) ? Number(key) : key, value) === false) break;
        }
    }
};

function services(t, requests = []) {
    t.mock.method(Osemosys, 'getData', async () => clone(fixture.genData));
    t.mock.method(Osemosys, 'getParamFile', async file => file === 'Variables.json' ? clone(fixture.variables) : {});
    t.mock.method(Osemosys, 'getResultData', async (casename, file) => {
        requests.push({casename, file});
        if (file === 'viewDefinitions.json') return {'osy-views': {}};
        if (file === 'resData.json') return {};
        assert.ok(file in fixture.results, `Unexpected results file: ${file}`);
        return clone(fixture.results[file]);
    });
    t.mock.method(console, 'log', () => {});
}

test('changing a variable clears condition filters before storing its Default view', {timeout: 2000}, async t => {
    services(t);
    for (const name of ['clearMessages', 'loaderStart', 'loaderEnd']) t.mock.method(Message, name, () => {});
    t.mock.method(Html, 'title', () => {});
    const records = DataModelResult.getPivot(clone(fixture.results['RYT.json']), fixture.genData, fixture.variables, 'RYT', 'ANC');
    const state = new ResultLayoutState(Pivot.fieldCatalogue(records));
    Pivot.applyDefaultLayout(state, 'RYT');
    state.setFilter('Year', [2020]);
    state.setConditionFilter('Tech', {conditions: [{operator: 'beginsWith', value: 'SOL'}]});
    const model = {
        casename: 'A', genData: fixture.genData, VARIABLES: fixture.variables,
        VARGROUPS: {NC: {group: 'RYT'}}, VARNAMES: {RYT: {NC: 'New Capacity'}},
        stgDecimalPoints: 'n2', pivotData: records, TriggerUpdate: true
    };
    const app = {state, pivotChart: {}};
    const finished = new Promise((resolve, reject) => {
        t.mock.method(Pivot, 'renderResults', resolve);
        t.mock.method(Message, 'danger', reject);
        t.mock.method(Message, 'dangerOsy', reject);
    });
    Pivot.updateParam('NC', app, model);
    await finished;
    assert.equal(state.configuration().filters.length, 0);
    assert.deepEqual(model.DEFAULTVIEW.conditionFilters, {});
    assert.equal(model.VIEW, 'null');
    assert.equal(controls.get('#cmbViews').value, 'null');
    const result = ResultAggregator.aggregate(model.pivotData, state.configuration());
    assert.equal(result.cells.length, 4);
    assert.equal(result.cells.reduce((sum, cell) => sum + cell.values.Value, 0), 10);
    state.apply(model.DEFAULTVIEW);
    assert.equal(state.configuration().filters.length, 0);
});

test('RYTCM keeps main\'s commodity column when opening a default layout', () => {
    const state = new ResultLayoutState(Pivot.fieldCatalogue([{Case: 'base', Year: 2020, Tech: 'SOLAR', Comm: 'ELEC', Value: 1}]));
    Pivot.applyDefaultLayout(state, 'RYTCM');
    assert.deepEqual(state.columns, ['Comm']);
});

for (const remembered of [true, false]) for (const navigating of [false, true]) {
    test(`case refresh loads the real ${remembered ? 'remembered R/OV' : 'default RYT/ANC'} model (${navigating ? 'changed' : 'stable'} snapshot)`, {timeout: 2000}, async t => {
        const requests = [];
        services(t, requests);
        let releaseSession;
        t.mock.method(Base, 'setSession', () => new Promise(resolve => {releaseSession = resolve;}));
        const finished = new Promise((resolve, reject) => {
            t.mock.method(Pivot, 'initPage', resolve);
            t.mock.method(Message, 'warning', reject);
        });
        const previous = Pivot.lastSnapshot;
        t.after(() => {Pivot.lastSnapshot = previous;});
        Pivot.lastSnapshot = remembered ? {casename: 'A', group: 'R', param: 'OV', view: null} : null;
        Pivot.refreshPage('A');
        if (navigating) Pivot.lastSnapshot = {casename: 'A', group: 'RYT', param: 'NC', view: null};
        releaseSession({});
        const model = await finished;
        assert.equal(model.group, remembered ? 'R' : 'RYT');
        assert.equal(model.param, remembered ? 'OV' : 'ANC');
        assert.equal(model.pivotData.length, remembered ? 1 : 4);
        assert.equal(model.refreshPage, true);
        const resultFiles = requests.filter(request => request.file === 'R.json' || request.file === 'RYT.json');
        assert.deepEqual(resultFiles, [{casename: 'A', file: remembered ? 'R.json' : 'RYT.json'}]);
    });
}
