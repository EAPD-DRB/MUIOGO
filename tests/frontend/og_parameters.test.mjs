import assert from 'node:assert/strict';
import { test } from 'node:test';
import { Model } from '../../WebAPP/App/Model/OGParameters.Model.js';
import { OGTableEditor } from '../../WebAPP/App/Controller/OGTableEditor.js';

const elements = new Map();
globalThis.$ = selector => {
    if (!elements.has(selector)) {
        const element = { textValue: '', classes: {} };
        for (const method of ['empty', 'appendTo', 'css', 'attr', 'addClass', 'hide', 'removeClass', 'focus']) {
            element[method] = () => element;
        }
        element.text = value => { element.textValue = value; return element; };
        element.toggleClass = (name, value) => { element.classes[name] = value; return element; };
        elements.set(selector, element);
    }
    return elements.get(selector);
};
Object.assign($, {
    isArray: Array.isArray,
    inArray: (value, array) => array.indexOf(value),
    trim: value => value.trim(),
    each: (object, callback) => Object.entries(object).forEach(([key, value]) => callback(key, value)),
    map: (object, callback) => Object.entries(object).flatMap(([key, value]) => {
        const result = callback(value, key);
        return result == null ? [] : result;
    })
});

const schema = {
    frisch: { shape: 'scalar', default: 1 },
    S: { shape: 'scalar', default: 80 },
    large: { default: null, large: true },
    unsupported: { shape: 'scalar', default: 0 },
    tensor: { default: [[0]], dimensions: [1, 1] }
};

test('saving an edit preserves stored uneditable and unknown values without mutating inputs', () => {
    const params = { S: 60, large: [1, 2], unsupported: 9, unknown: { values: [null, 0] }, frisch: 1.5 };
    const model = new Model(schema, params);
    model.fields.unsupported.dimension = 'unsupported';
    model.cur.frisch = 1.6;
    const payload = model.savePayload();
    assert.deepEqual(payload, { ...params, frisch: 1.6 });
    payload.unknown.values[0] = 7;
    assert.equal(params.unknown.values[0], null);
    assert.equal(params.frisch, 1.5);
});

test('reset removes editable overrides and does not materialize defaults or baseline inheritance', () => {
    for (const run_type of ['baseline', 'reform']) {
        const model = new Model(schema, { S: 60, frisch: 1.5 }, { run_type }, { frisch: 2, unknown: 7 });
        model.cur.frisch = Model.clone(model.base.frisch);
        assert.deepEqual(model.savePayload(), { S: 60 });
        model.cur.tensor = 3;
        assert.deepEqual(model.savePayload(), { S: 60, tensor: [[3]] });
        model.otherRefs.preview = { frisch: 9 };
        model.refValue('frisch', 'preview');
        assert.deepEqual(model.savePayload(), { S: 60, tensor: [[3]] });
    }
});

test('table highlights and status count only cells with usable references', () => {
    globalThis.document = { activeElement: null };
    globalThis.Tabulator = class {
        constructor(selector, options) { this.options = options; }
        on() {}
        destroy() {}
        getData() { return this.options.data; }
    };
    globalThis.window = { Tabulator };
    for (const [reference, expected] of [[null, 0], [7, 0], [undefined, 0], [[[0, null]], 1], [[[0]], 0]]) {
        OGTableEditor.open({ name: 'table', title: 'Table', value: [[0, 0]], reference });
        const table = OGTableEditor.table;
        let modified = 0;
        for (const column of table.options.columns) {
            const row = table.getData()[0];
            const element = { classList: { toggle: (name, value) => {
                if (name === 'ogc-table-modified' && value) modified++;
            } } };
            column.formatter({
                getRow: () => ({ getData: () => row }),
                getField: () => column.field,
                getValue: () => row[column.field],
                getElement: () => element
            });
        }
        assert.equal(modified, expected, String(reference));
        OGTableEditor.refreshStatus();
        assert.equal($('#ogcTableStatus').textValue, expected ? '1 modified value' : 'No modified values');
    }
    OGTableEditor.close();
});

test('large column schedules remain unloaded until requested and keep their storage shape', () => {
    const model = new Model({cit_rate: {
        shape: 'time_x_industry', default: null, large: true,
        dimensions: [400, 1], preview: [[0.1], [0.2]]
    }}, {});
    assert.equal(model.cur.cit_rate, null);
    assert.equal(model.fields.cit_rate.tableEditable, true);
    assert.deepEqual(model.savePayload(), {});
    model.hydrateDefault('cit_rate', [[0.1], [0.2], [0.3]]);
    assert.deepEqual(model.cur.cit_rate, [0.1, 0.2, 0.3]);
    model.cur.cit_rate[1] = 0.25;
    assert.deepEqual(model.savePayload(), {cit_rate: [[0.1], [0.25], [0.3]]});
});
