import assert from 'node:assert/strict';
import { test } from 'node:test';

const storage = new Map();
Object.defineProperty(globalThis, 'localStorage', { value: {
    getItem: key => storage.get(key) || null,
    setItem: (key, value) => storage.set(key, value)
} });
const elements = new Map();
globalThis.$ = selector => {
    if (!elements.has(selector)) {
        const element = {};
        element.html = value => { element.content = value; return element; };
        element.text = value => { element.content = value; return element; };
        elements.set(selector, element);
    }
    return elements.get(selector);
};
Object.assign($, {
    isArray: Array.isArray,
    inArray: (value, array) => array.indexOf(value),
    each: (object, callback) => Object.entries(object).forEach(([key, value]) => callback(key, value)),
    map: (object, callback) => Object.entries(object).flatMap(([key, value]) => {
        const result = callback(value, key);
        return result == null ? [] : result;
    })
});
const { default: OGParameters } = await import('../../WebAPP/App/Controller/OGParameters.js');
const { default: OGCases } = await import('../../WebAPP/App/Controller/OGCases.js');
const { default: OGCore } = await import('../../WebAPP/App/Controller/OGCore.js');
const { Model } = await import('../../WebAPP/App/Model/OGParameters.Model.js');

test('parameter context uses the selected country and never a different workspace name', () => {
    storage.set('osy-ogc-country', JSON.stringify({ country_id: 'ETH', country_name: 'Ethiopia' }));
    const model = new Model({}, {}, { country_id: 'ETH', run_name: 'baseline' });
    OGParameters.renderContext(model);
    assert.equal($('#ogcParamsCountryName').content, 'Ethiopia');
    assert.match($('#ogcParamsCountryFlag').content, /et\.svg/);
    model.selection.country_id = 'ZAF';
    OGParameters.renderContext(model);
    assert.equal($('#ogcParamsCountryName').content, 'ZAF');
    assert.match($('#ogcParamsCountryFlag').content, /za\.svg/);
    model.selection.country_id = 'CUSTOM';
    OGParameters.renderContext(model);
    assert.match($('#ogcParamsCountryFlag').content, /fa-flag-o/);
});

test('frequent controls appear once and open, while remaining groups stay reachable and collapsed', () => {
    const model = new Model({
        start_year: { shape: 'scalar', default: 2025, title: 'Start year' },
        cit_rate: { shape: 'scalar', default: 0.2, title: 'Corporate tax' },
        frisch: { shape: 'scalar', default: 1.5, title: 'Frisch elasticity' },
        etr_params: { default: [[0.1]], dimensions: [1, 1] },
        tax_func_type: { shape: 'scalar', default: 'linear', datatype: 'str' }
    });
    OGParameters.renderGroups(model);
    const html = $('#ogcParamsBody').content;
    assert.match(html, /data-group="frequent" open/);
    assert.match(html, /Frequently Used Parameters/);
    assert.equal((html.match(/ open>/g) || []).length, 1);
    for (const name of Object.keys(model.fields)) {
        assert.equal((html.match(new RegExp('data-param="' + name + '"', 'g')) || []).length, 1);
    }
    assert.match(html, /Corporate tax/);
    assert.match(html, /Frisch elasticity/);
    assert.match(html.split('</details>')[0], /data-param="etr_params"/);
    model.cur.tax_func_type = 'DEP';
    OGParameters.renderGroups(model);
    assert.doesNotMatch($('#ogcParamsBody').content.split('</details>')[0], /data-param="etr_params"/);
    assert.match($('#ogcParamsBody').content, /data-param="etr_params"/);
});

test('case action markup retains actions with the orange primary style', () => {
    OGCases.workspace = { country_id: 'ETH', country_name: 'Ethiopia' };
    OGCases.model = { records: { ETH: {} } };
    const html = OGCases.defaultRow() + OGCases.entryRows({
        case: { country_id: 'ETH', casename: 'Test' },
        run: { run_name: 'baseline', run_type: 'baseline' }
    });
    assert.match(html, /data-act="add-reform"/);
    assert.doesNotMatch(OGCases.defaultRow(), /data-act="(?:create-case|new-case)"/);
    for (const action of ['run', 'params', 'run-menu']) {
        assert.match(html, new RegExp('<button class="[^"]*ogc-btn-main[^"]*" data-act="' + action + '"'));
    }
});

test('country action labels distinguish update checks from updates and removal', () => {
    assert.match(OGCore.actionsHtml({ install_state: 'installed' }), /> Check for updates<\/button>/);
    for (const state of ['installed', 'update_available', 'failed']) {
        const html = OGCore.actionsHtml({ install_state: state });
        assert.match(html, /data-act="remove"[^>]*>.* Remove<\/button>/);
        assert.doesNotMatch(html, /> Delete<\/button>/);
    }
    assert.match(OGCore.actionsHtml({ install_state: 'update_available' }), /data-act="update"[^>]*>.* Update<\/button>/);
});
