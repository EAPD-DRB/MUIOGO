import assert from 'node:assert/strict';
import { test } from 'node:test';
import { NavigationGuard } from '../../WebAPP/Classes/NavigationGuard.Class.js';
import { Message } from '../../WebAPP/Classes/Message.Class.js';
import { OGWorkspace } from '../../WebAPP/Classes/OGWorkspace.Class.js';
import { Ogc } from '../../WebAPP/Classes/Ogc.Class.js';

const listeners = new Map();
globalThis.window = {
    addEventListener: (name, handler) => listeners.set(name, handler),
    removeEventListener: name => listeners.delete(name)
};
const storage = new Map();
Object.defineProperty(globalThis, 'localStorage', { value: {
    getItem: key => storage.get(key),
    removeItem: key => storage.delete(key)
} });

test('failed allowed callbacks restore the guard for clean and discarded changes', async () => {
    Message.confirmUnsavedModelChanges = async () => "Don't save";
    for (const dirty of [false, true]) {
        for (const callback of [() => { throw new Error('failed'); }, () => Promise.reject(new Error('failed'))]) {
            const guard = { hasChanges: () => dirty };
            NavigationGuard.activate(guard);
            await assert.rejects(NavigationGuard.requestLeave(callback), /failed/);
            assert.ok(listeners.has('beforeunload'));
            assert.equal(await NavigationGuard.requestLeave(() => false), false);
            assert.ok(listeners.has('beforeunload'));
            assert.equal(await NavigationGuard.requestLeave(() => true), true);
            assert.equal(listeners.has('beforeunload'), false);
        }
    }
});

test('startup reconciliation keeps local identity on failure and clears only after confirmation', async () => {
    const workspace = JSON.stringify({ country_id: 'ETH' });
    storage.set('osy-ogc-country', workspace);
    storage.set('osy-ogc-selection', 'selection');
    Ogc.setSession = async () => { throw new Error('offline'); };
    assert.equal(await OGWorkspace.reconcileEntry('/OGCore'), false);
    assert.equal(storage.get('osy-ogc-country'), workspace);
    assert.equal(storage.get('osy-ogc-selection'), 'selection');
    let resolve;
    Ogc.setSession = () => new Promise(done => { resolve = done; });
    const pending = OGWorkspace.reconcileEntry('/OGCore');
    assert.equal(storage.get('osy-ogc-country'), workspace);
    resolve({});
    assert.equal(await pending, true);
    assert.equal(storage.has('osy-ogc-country'), false);
    assert.equal(storage.has('osy-ogc-selection'), false);
});

test('startup reconciles every non-workspace route and preserves workspace routes', async () => {
    let calls = 0;
    Ogc.setSession = async () => {calls++;};
    for (const route of ['/OGCases', '/OGParameters', '/OGRuns']) {
        storage.set('osy-ogc-country', JSON.stringify({country_id:'ETH'}));
        assert.equal(OGWorkspace.reconcileEntry(route), null);
    }
    assert.equal(calls, 0);
    for (const route of ['/', '/Config', '/Versions', '/OGCore']) {
        storage.set('osy-ogc-country', JSON.stringify({country_id:'ETH'}));
        assert.equal(await OGWorkspace.reconcileEntry(route), true);
        assert.equal(storage.has('osy-ogc-country'), false);
    }
    assert.equal(calls, 4);
});
