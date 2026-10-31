import assert from 'node:assert/strict';
import { test } from 'node:test';
import { Osemosys } from '../../WebAPP/Classes/Osemosys.Class.js';
import ViewData from '../../WebAPP/App/Controller/ViewData.js';

globalThis.document = {querySelector: () => null};
globalThis.window = {location: {origin: 'http://localhost'}};
globalThis.$ = {ajax: () => { throw new Error('Unexpected request'); }};

test('legacy getData_ returns the decoded file through getData', async t => {
    const payload = {VC: {SC_0: [{TechId: 'T1', MoId: 1, '2030': 5}]}};
    let requests = 0;
    t.mock.method(globalThis, 'fetch', async (url, options) => {
        requests++;
        assert.equal(url, '../../DataStorage/Example/RYTM.json');
        assert.equal(options.cache, 'no-store');
        return new Response(JSON.stringify(payload));
    });
    assert.deepEqual(await Osemosys.getData_('Example', 'RYTM.json'), payload);
    assert.equal(requests, 1);
});

for (const [name, fetch] of [
    ['HTTP failure', async () => new Response('missing', {status: 404})],
    ['invalid JSON', async () => new Response('invalid')],
    ['network failure', async () => { throw new Error('offline'); }],
]) {
    test(`legacy getData_ preserves getData handling of ${name}`, async t => {
        t.mock.method(globalThis, 'fetch', fetch);
        assert.equal(await Osemosys.getData_('Example', 'RYTM.json'), null);
    });
}

test('annual edit transport includes mode and constraint and preserves zero', async t => {
    let sent;
    t.mock.method(globalThis.$, 'ajax', options => {
        sent = JSON.parse(options.data);
        assert.equal(options.url, 'http://localhost/updateViewData');
        options.success({status_code: 'success'});
    });
    await Osemosys.updateViewData('Example', '2030', 'SC_0', 'RYTM', 'VC',
        'T1', '', undefined, null, 0, '2');
    assert.deepEqual(sent, {
        casename: 'Example', year: '2030', ScId: 'SC_0', groupId: 'RYTM', paramId: 'VC',
        TechId: 'T1', CommId: null, EmisId: null, Timeslice: null,
        MoId: '2', ConId: null, value: 0,
    });
    await Osemosys.updateViewData('Example', '2030', 'SC_1', 'RYTCn', 'CAM',
        'T1', null, null, null, 4, null, 'CN2');
    assert.equal(sent.ConId, 'CN2');
    assert.equal(sent.MoId, null);
});

test('non-yearly edit transport preserves zero and normalizes unused IDs', async t => {
    let sent;
    t.mock.method(globalThis.$, 'ajax', options => {
        sent = JSON.parse(options.data);
        assert.equal(options.url, 'http://localhost/updateTEViewData');
        options.success({status_code: 'success'});
    });
    await Osemosys.updateTEViewData('Example', 'SC_0', 'RE', 'MPEL', undefined, 'E1', 0);
    assert.deepEqual(sent, {
        casename: 'Example', scId: 'SC_0', groupId: 'RE', paramId: 'MPEL',
        techId: null, emisId: 'E1', value: 0,
    });
});

test('UI cache selection separates every index and normalizes jqx mode types', () => {
    const cell = {
        ScId: 'SC_0', groupId: 'RYTM', param: 'VC', TechId: 'T1',
        CommId: null, EmisId: null, TsId: null, MoId: 1, ConId: null,
    };
    assert.equal(ViewData.sameCell(cell, {...cell, MoId: '1', CommId: ''}), true);
    for (const [key, value] of Object.entries(cell)) {
        assert.equal(ViewData.sameCell(cell, {...cell, [key]: value === null ? 'other' : 'different'}), false, key);
    }
    const constraint = {...cell, groupId: 'RYTCn', param: 'CAM', MoId: null, ConId: 'CN1'};
    assert.equal(ViewData.sameCell(constraint, {...constraint}), true);
    assert.equal(ViewData.sameCell(constraint, {...constraint, ConId: 'CN2'}), false);
});
