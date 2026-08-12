import { GROUPS, LOCKED_DIMS, decorate } from "./OGParams.Overlay.js";

export class Model {

    constructor (schema, params, selection, refParams) {
        this.selection = selection || {};
        this.isReform = this.selection.run_type == 'reform';

        this.fields = {};
        this.byGroup = {};
        let fields = this.fields;
        let byGroup = this.byGroup;
        $.each(GROUPS, function (id, g) { byGroup[g.id] = []; });

        let self = this;
        $.each(schema || {}, function (name, entry) {
            let f = decorate(name, entry);
            f.hasRange = f.min !== null && f.max !== null && f.max > f.min;
            f.def = self.normalise(f, f.def);
            fields[name] = f;
            if (!byGroup[f.group]){
                byGroup[f.group] = [];
            }
            byGroup[f.group].push(name);
        });

        this.base = {};
        this.cur = {};
        this.otherRefs = {};

        let base = this.base;
        let cur = this.cur;
        $.each(fields, function (name, f) {
            let refVal = self.isReform ? self.pick(refParams, name, f.def) : f.def;
            base[name] = refVal;
            cur[name] = self.pick(params, name, refVal);
        });

        this.pageID = 'OGParameters';
    }

    pick(params, name, fallback){
        if (!params || !(name in params)){
            return fallback;
        }
        return this.unwrap(params[name], this.fields[name]);
    }

    unwrap(v, f){
        if (!f){
            return v;
        }
        if (f.dimension == 'scalar'){
            while ($.isArray(v) && v.length == 1){
                v = v[0];
            }
            return v;
        }
        if (f.dimension == 'by_j'){
            if ($.isArray(v) && v.length == 1 && $.isArray(v[0])){
                return v[0];
            }
            return v;
        }
        return v;
    }

    wrap(name, value){
        let f = this.fields[name];
        if (!f){
            return value;
        }
        if (f.dimension == 'scalar'){
            return value;
        }
        if (f.dimension == 'by_j'){
            return value;
        }
        return value;
    }

    normalise(f, v){
        if (f.dimension == 'scalar'){
            while ($.isArray(v) && v.length == 1){
                v = v[0];
            }
            return v;
        }
        if (f.dimension == 'by_j'){
            if ($.isArray(v) && v.length == 1 && $.isArray(v[0])){
                return v[0];
            }
            return $.isArray(v) ? v : [];
        }
        return v;
    }

    editable(name){
        let f = this.fields[name];
        if (!f || f.readOnly){
            return false;
        }
        if ($.inArray(name, LOCKED_DIMS) >= 0){
            return false;
        }
        return f.dimension == 'scalar' || f.dimension == 'by_j' || f.dimension == 'by_year';
    }

    refValue(name, refName){
        let f = this.fields[name];
        if (!f){
            return null;
        }
        if (!refName || refName == 'auto'){
            return this.base[name];
        }
        if (refName == 'def'){
            return f.def;
        }
        let other = this.otherRefs[refName];
        if (!other){
            return f.def;
        }
        return this.pick(other, name, f.def);
    }

    isChanged(name, refName){
        return !Model.equal(this.cur[name], this.refValue(name, refName));
    }

    changedNames(){
        let out = [];
        let self = this;
        $.each(this.fields, function (name, f) {
            if (!self.editable(name)){
                return;
            }
            if (!Model.equal(self.cur[name], self.base[name])){
                out.push(name);
            }
        });
        return out;
    }

    savePayload(){
        let payload = {};
        let self = this;
        $.each(this.changedNames(), function (id, name) {
            payload[name] = self.wrap(name, self.cur[name]);
        });
        return payload;
    }

    static equal(a, b){
        if ($.isArray(a) || $.isArray(b)){
            if (!$.isArray(a) || !$.isArray(b) || a.length != b.length){
                return false;
            }
            for (let i = 0; i < a.length; i++){
                if (!Model.equal(a[i], b[i])){
                    return false;
                }
            }
            return true;
        }
        if (a === null || a === undefined || b === null || b === undefined){
            return a === b;
        }
        if (typeof a == 'number' || typeof b == 'number'){
            let na = parseFloat(a);
            let nb = parseFloat(b);
            if (!isNaN(na) && !isNaN(nb)){
                return Math.abs(na - nb) < 1e-12;
            }
        }
        return a === b;
    }

    groupsWithFields(){
        let byGroup = this.byGroup;
        return $.map(GROUPS, function (g) {
            return (byGroup[g.id] && byGroup[g.id].length) ? g : null;
        });
    }
}
