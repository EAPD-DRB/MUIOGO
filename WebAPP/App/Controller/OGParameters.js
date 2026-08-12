import { Message } from "../../Classes/Message.Class.js";
import { NavigationGuard } from "../../Classes/NavigationGuard.Class.js";
import { Ogc } from "../../Classes/Ogc.Class.js";
import { Model } from "../Model/OGParameters.Model.js";
import { loadSelection, markRunsStale } from "./OGCases.js";
import { GROUPS, TIER } from "../Model/OGParams.Overlay.js";

const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g,
    ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));

const TIER_LABEL = {};
TIER_LABEL[TIER.LEVERS] = 'Policy levers';
TIER_LABEL[TIER.ASSUMPTIONS] = 'Model assumptions';
TIER_LABEL[TIER.REFERENCE] = 'Reference and advanced';

let PAGE_ID = 0;
let previewRef = 'auto';
let dirty = false;

export default class OGParameters {

    static onLoad(){
        PAGE_ID++;
        OGParameters.pageID = PAGE_ID;
        previewRef = 'auto';
        dirty = false;
        OGParameters.load(PAGE_ID);
    }

    static isCurrent(pageID){
        return pageID == PAGE_ID;
    }

    static load(pageID){
        let selection = loadSelection();
        if (!selection || !selection.casename || !selection.run_name){
            OGParameters.showEmpty('No run selected',
                'Open a run from the Cases page to configure its parameters.');
            return;
        }
        let refPromise = (selection.run_type == 'reform' && selection.baseline_run)
            ? Ogc.getParams(selection.casename, selection.baseline_run)
                .then(r => r.params || {})
                .catch(e => null)
            : Promise.resolve({});

        Promise.all([
            Ogc.getParameterSchema(selection.casename),
            Ogc.getParams(selection.casename, selection.run_name),
            Ogc.getRuns(selection.casename),
            refPromise
        ])
        .then(data => {
            if (!OGParameters.isCurrent(pageID)){
                return;
            }
            let [schema, params, runs, refParams] = data;
            if (selection.run_type == 'reform' && refParams === null){
                Message.warning('The baseline for this reform could not be read, so changes are shown against the calibration default.');
                refParams = {};
            }
            OGParameters.model = new Model(schema, params.params || {}, selection, refParams);
            OGParameters.runs = runs.runs || [];
            OGParameters.render(OGParameters.model, pageID);
            OGParameters.initEvents();
        })
        .catch(error => {
            if (!OGParameters.isCurrent(pageID)){
                return;
            }
            OGParameters.showEmpty('The parameters could not be loaded', String(error));
        });
    }

    static showEmpty(title, text){
        $('#ogcParamsCtx').hide();
        $('#ogcParamsEditbar').hide();
        $('#ogcParamsBody').empty();
        $('#ogcParamsEmptyTitle').text(title);
        $('#ogcParamsEmptyText').text(text);
        $('#ogcParamsEmpty').show();
    }

    static render(model, pageID){
        if (!OGParameters.isCurrent(pageID)){
            return;
        }
        $('#ogcParamsEmpty').hide();
        OGParameters.renderContext(model);
        OGParameters.renderGroups(model);
        $('#ogcParamsCtx').show();
        $('#ogcParamsEditbar').show();
        OGParameters.refreshAll();
    }

    static renderContext(model){
        let sel = model.selection;
        let displayName = sel.display_name || sel.run_name;
        let baselineName = sel.baseline_display_name || sel.baseline_run;
        let kindTag = model.isReform
            ? `<span class="ogc-tag ogc-tag-reform">reform</span>`
            : `<span class="ogc-tag ogc-tag-base">baseline</span>`;
        let of = model.isReform && sel.baseline_run
            ? ` <span class="ogc-mut">of</span> <b>${esc(baselineName)}</b>`
            : '';
        $('#ogcParamsTitle').text('Parameters: ' + displayName);
        $('#ogcParamsCtx').html(`
            ${kindTag}
            <span><b>${esc(displayName)}</b>${of}</span>
            <span class="ogc-mut">in ${esc(sel.casename)}</span>
            <span class="ogc-tag ogc-tag-mut">${esc(sel.country_id || '')}</span>
            <span class="ogc-ctx-right">
                <span class="ogc-mut">Compare against</span>
                <select id="ogcCmpRef">${OGParameters.refOptions(model)}</select>
            </span>`);
        $('#ogcResetLabel').text(model.isReform ? 'Reset to baseline' : 'Reset to calibration');
    }

    static refOptions(model){
        let sel = model.selection;
        let own = model.isReform
            ? `<option value="auto">${esc(sel.baseline_run || 'its baseline')} (its baseline)</option>`
            : `<option value="auto">Calibration default</option>`;
        let others = '';
        $.each(OGParameters.runs || [], function (id, r) {
            if (r.run_name == sel.run_name || r.run_name == sel.baseline_run){
                return;
            }
            others += `<option value="${esc(r.run_name)}">${esc(r.run_name)}</option>`;
        });
        let def = model.isReform ? `<option value="def">Calibration default</option>` : '';
        return own + others + def;
    }

    static renderGroups(model){
        let html = '';
        let lastTier = null;
        $.each(model.groupsWithFields(), function (id, g) {
            if (g.tier != lastTier){
                html += `<div class="ogc-tier">${esc(TIER_LABEL[g.tier] || '')}</div>`;
                lastTier = g.tier;
            }
            html += OGParameters.groupHtml(model, g);
        });
        $('#ogcParamsBody').html(html);
    }

    static groupHtml(model, group){
        let names = model.byGroup[group.id] || [];
        let bySub = {};
        let subOrder = [];
        $.each(names, function (id, name) {
            let f = model.fields[name];
            let key = f.subsection || '';
            if (!bySub[key]){
                bySub[key] = [];
                subOrder.push(key);
            }
            bySub[key].push(name);
        });
        let body = '';
        $.each(subOrder, function (id, key) {
            if (key){
                body += `<div class="ogc-subhead">${esc(key)}</div>`;
            }
            $.each(bySub[key], function (fid, name) {
                body += OGParameters.fieldHtml(model, name);
            });
        });
        let open = group.tier == TIER.LEVERS ? ' open' : '';
        return `
            <details class="ogc-acc" data-group="${esc(group.id)}"${open}>
                <summary><i class="fa fa-grp ${esc(group.icon)}"></i> ${esc(group.title)}<span class="ogc-chgbadge"></span></summary>
                <div class="ogc-accbody">
                    <div class="ogc-grid2">${body}</div>
                </div>
            </details>`;
    }

    static labelHtml(f){
        let help = f.description
            ? ` <span class="ogc-help" title="${esc(f.description)}"><i class="fa fa-question-circle"></i></span>`
            : '';
        let code = f.title == f.name ? '' : ` <span class="ogc-mut ogc-mono">(${esc(f.name)})</span>`;
        let ro = f.readOnly
            ? ` <span class="ogc-ro"><i class="fa fa-lock"></i> read-only</span>`
            : '';
        return `<label>${esc(f.title)}${code}${help}${ro}</label>`;
    }

    static hintHtml(f){
        let bits = [];
        if (OGParameters.hasUsefulRange(f)){
            bits.push('range [' + esc(f.min) + ', ' + esc(f.max) + ']');
        }
        return bits.length ? `<div class="ogc-hint">${bits.join(' &middot; ')}</div>` : '';
    }

    static hasUsefulRange(f){
        return f.hasRange && Number.isFinite(f.min) && Number.isFinite(f.max)
            && f.max - f.min <= 1000000;
    }

    static fieldHtml(model, name){
        let f = model.fields[name];
        let wide = f.dimension != 'scalar';
        let inner;
        if (!model.editable(name)){
            inner = OGParameters.readOnlyHtml(model, f);
        }else if (f.dimension == 'by_j'){
            inner = OGParameters.rowHtml(model, f);
        }else if (f.dimension == 'by_year'){
            inner = OGParameters.pathHtml(model, f);
        }else if (f.choices){
            inner = OGParameters.selectHtml(model, f);
        }else if (OGParameters.isBool(f, model.cur[name])){
            inner = OGParameters.boolHtml(model, f);
        }else if (OGParameters.hasUsefulRange(f)){
            inner = OGParameters.sliderHtml(model, f);
        }else{
            inner = OGParameters.numberHtml(model, f);
        }
        return `
            <div class="ogc-field${wide ? ' ogc-wide' : ''}" data-param="${esc(name)}">
                ${OGParameters.labelHtml(f)}
                ${inner}
                <div class="ogc-delta"></div>
                ${OGParameters.hintHtml(f)}
            </div>`;
    }

    static isBool(f, v){
        return typeof v == 'boolean' || typeof f.def == 'boolean';
    }

    static readOnlyHtml(model, f){
        let v = model.cur[f.name];
        let shown;
        if (f.large){
            shown = '\u2014';
        }else if ($.isArray(v)){
            let flat = OGParameters.flatten(v);
            let head = $.map(flat.slice(0, 8), function (x) { return OGParameters.fmt(x); }).join(', ');
            shown = head + (flat.length > 8 ? ', ... (' + flat.length + ' values)' : '');
        }else if (v === null || v === undefined){
            shown = '\u2014';
        }else{
            shown = OGParameters.fmt(v);
        }
        return `<span class="ogc-rovalue">${esc(shown)}</span>`;
    }

    static sliderHtml(model, f){
        let v = model.cur[f.name];
        let step = OGParameters.stepFor(f);
        return `
            <div class="ogc-rangewrap">
                <input type="range" min="${esc(f.min)}" max="${esc(f.max)}" step="${esc(step)}" value="${esc(v)}" data-role="range">
                <input type="number" class="ogc-valnum" min="${esc(f.min)}" max="${esc(f.max)}" step="${esc(step)}" value="${esc(v)}" data-role="num">
            </div>`;
    }

    static numberHtml(model, f){
        let v = model.cur[f.name];
        let attrs = '';
        if (f.min !== null){ attrs += ` min="${esc(f.min)}"`; }
        if (f.max !== null){ attrs += ` max="${esc(f.max)}"`; }
        return `<input type="number" step="${esc(OGParameters.stepFor(f))}"${attrs} value="${esc(v === null || v === undefined ? '' : v)}" data-role="num">`;
    }

    static selectHtml(model, f){
        let v = model.cur[f.name];
        let opts = '';
        $.each(f.choices, function (id, c) {
            opts += `<option value="${esc(c)}"${c == v ? ' selected' : ''}>${esc(c)}</option>`;
        });
        return `<select data-role="choice">${opts}</select>`;
    }

    static boolHtml(model, f){
        let v = model.cur[f.name];
        return `<select data-role="bool">
                    <option value="true"${v ? ' selected' : ''}>Yes</option>
                    <option value="false"${v ? '' : ' selected'}>No</option>
                </select>`;
    }

    static rowHtml(model, f){
        let vals = model.cur[f.name] || [];
        let cells = '';
        $.each(vals, function (i, v) {
            let lab = 'j' + (i + 1);
            let attrs = '';
            if (f.min !== null){ attrs += ` min="${esc(f.min)}"`; }
            if (f.max !== null){ attrs += ` max="${esc(f.max)}"`; }
            cells += `
                <span class="ogc-jcell">
                    <input type="number" step="${esc(OGParameters.stepFor(f))}"${attrs} value="${esc(v)}" data-role="cell" data-index="${i}">
                    <span class="ogc-jlab">${esc(lab)}</span>
                </span>`;
        });
        let sum = f.constraint == 'sum_to_one' ? `<div class="ogc-jsum"></div>` : '';
        return `<div class="ogc-jrow">${cells}</div>${sum}`;
    }

    static pathHtml(model, f){
        let vals = $.isArray(model.cur[f.name]) ? model.cur[f.name] : [];
        let start = parseInt(model.cur.start_year, 10);
        let attrs = '';
        if (f.min !== null){ attrs += ` min="${esc(f.min)}"`; }
        if (f.max !== null){ attrs += ` max="${esc(f.max)}"`; }
        let rows = '';
        $.each(vals, function (i, v) {
            let year = isNaN(start) ? i + 1 : start + i;
            rows += `<span class="ogc-pathcell">
                <span class="ogc-pathyear">${esc(year)}</span>
                <input type="number" step="${esc(OGParameters.stepFor(f))}"${attrs} value="${esc(v)}" data-role="path-cell" data-index="${i}">
                ${i ? '<button type="button" class="ogc-pathremove" data-act="remove-year" title="Remove year"><i class="fa fa-times"></i></button>' : ''}
            </span>`;
        });
        return `<div class="ogc-path">${rows}<button type="button" class="ogc-pathadd" data-act="add-year"><i class="fa fa-plus"></i> Add year</button></div>`;
    }

    static stepFor(f){
        if (f.type == 'year' || f.type == 'count'){
            return 1;
        }
        if (f.min !== null && f.max !== null){
            let span = f.max - f.min;
            if (span <= 2){ return 0.001; }
            if (span <= 20){ return 0.01; }
            if (span <= 1000){ return 1; }
            return 100;
        }
        return 'any';
    }

    static fmt(v){
        if (typeof v == 'boolean'){
            return v ? 'Yes' : 'No';
        }
        if (typeof v != 'number'){
            let n = parseFloat(v);
            if (isNaN(n)){
                return String(v);
            }
            v = n;
        }
        if (Math.abs(v - Math.round(v)) < 1e-12){
            return String(Math.round(v));
        }
        let a = Math.abs(v);
        if (a < 1){ return v.toFixed(4).replace(/0+$/, '').replace(/\.$/, ''); }
        if (a < 100){ return v.toFixed(3).replace(/0+$/, '').replace(/\.$/, ''); }
        return v.toFixed(1);
    }

    static flatten(v){
        if (!$.isArray(v)){
            return [v];
        }
        let out = [];
        $.each(v, function (id, x) {
            out = out.concat(OGParameters.flatten(x));
        });
        return out;
    }

    static fieldEl(name){
        return $('#ogcParamsBody .ogc-field[data-param="' + name + '"]');
    }

    static readWidget(name){
        let model = OGParameters.model;
        let f = model.fields[name];
        let el = OGParameters.fieldEl(name);
        if (f.dimension == 'by_j' || f.dimension == 'by_year'){
            let vals = [];
            let role = f.dimension == 'by_j' ? 'cell' : 'path-cell';
            el.find('[data-role="' + role + '"]').each(function () {
                let n = parseFloat($(this).val());
                vals.push(isNaN(n) ? null : n);
            });
            return vals;
        }
        let choice = el.find('[data-role="choice"]');
        if (choice.length){
            return choice.val();
        }
        let bool = el.find('[data-role="bool"]');
        if (bool.length){
            return bool.val() == 'true';
        }
        let num = el.find('[data-role="num"]');
        if (num.length){
            let raw = $.trim(num.val());
            if (raw === ''){
                return null;
            }
            let n = parseFloat(raw);
            return isNaN(n) ? null : n;
        }
        return model.cur[name];
    }

    static writeWidget(name, value){
        let model = OGParameters.model;
        let f = model.fields[name];
        let el = OGParameters.fieldEl(name);
        if (f.dimension == 'by_j' || f.dimension == 'by_year'){
            let role = f.dimension == 'by_j' ? 'cell' : 'path-cell';
            el.find('[data-role="' + role + '"]').each(function () {
                let i = parseInt($(this).attr('data-index'), 10);
                let v = ($.isArray(value) && value.length > i) ? value[i] : '';
                $(this).val(v === null || v === undefined ? '' : v);
            });
            return;
        }
        let choice = el.find('[data-role="choice"]');
        if (choice.length){
            choice.val(value);
            return;
        }
        let bool = el.find('[data-role="bool"]');
        if (bool.length){
            bool.val(value ? 'true' : 'false');
            return;
        }
        el.find('[data-role="range"]').val(value);
        el.find('[data-role="num"]').val(value === null || value === undefined ? '' : value);
    }

    static onEdit(name){
        OGParameters.model.cur[name] = OGParameters.readWidget(name);
        dirty = true;
        OGParameters.refreshField(name);
        OGParameters.refreshTotals();
    }

    static refreshField(name){
        let model = OGParameters.model;
        let f = model.fields[name];
        let el = OGParameters.fieldEl(name);
        if (!el.length || !model.editable(name)){
            return;
        }
        let cur = model.cur[name];
        let ref = model.refValue(name, previewRef);
        let changed = !Model.equal(cur, ref);
        el.toggleClass('ogc-changed', changed);

        if (f.dimension == 'by_j' || f.dimension == 'by_year'){
            OGParameters.refreshRow(name, f, cur, ref);
        }else{
            let bad = OGParameters.outOfRange(f, cur);
            el.toggleClass('ogc-bad', bad);
            OGParameters.paintTrack(el, f, cur, ref, changed);
        }
        OGParameters.renderDelta(el, name, f, cur, ref, changed);
    }

    static outOfRange(f, v){
        if (typeof v != 'number'){
            return false;
        }
        if (f.min !== null && v < f.min){
            return true;
        }
        return f.max !== null && v > f.max;
    }

    static refreshRow(name, f, cur, ref){
        let el = OGParameters.fieldEl(name);
        let role = f.dimension == 'by_j' ? 'cell' : 'path-cell';
        el.find('[data-role="' + role + '"]').each(function () {
            let i = parseInt($(this).attr('data-index'), 10);
            let v = ($.isArray(cur) && cur.length > i) ? cur[i] : null;
            let r = ($.isArray(ref) && ref.length > i) ? ref[i] : null;
            $(this).toggleClass('ogc-cellbad', OGParameters.outOfRange(f, v));
            $(this).toggleClass('ogc-cellchanged', !Model.equal(v, r));
        });
        if (f.dimension != 'by_j' || f.constraint != 'sum_to_one'){
            return;
        }
        let sum = 0;
        $.each(cur || [], function (id, v) { sum += (typeof v == 'number' ? v : 0); });
        let ok = Math.abs(sum - 1) < 0.0005;
        el.find('.ogc-jsum')
            .text('sum = ' + sum.toFixed(4) + (ok ? ' (ok)' : ' \u2014 must equal 1'))
            .toggleClass('ogc-bad', !ok);
    }

    static paintTrack(el, f, cur, ref, changed){
        let range = el.find('[data-role="range"]');
        if (!range.length){
            return;
        }
        if (!changed || typeof cur != 'number' || typeof ref != 'number' || !f.hasRange){
            range[0].style.setProperty('--ogc-track', 'none');
            return;
        }
        let pct = v => ((v - f.min) / (f.max - f.min)) * 100;
        let lo = Math.max(0, Math.min(pct(ref), pct(cur)));
        let hi = Math.min(100, Math.max(pct(ref), pct(cur)));
        let tick = Math.max(0, Math.min(100, pct(ref)));
        let col = 'rgba(245,130,32,.45)';
        let band = `linear-gradient(90deg,transparent 0 ${lo}%,${col} ${lo}% ${hi}%,transparent ${hi}% 100%)`;
        let mark = `linear-gradient(90deg,transparent 0 calc(${tick}% - 1px),#3a3f51 calc(${tick}% - 1px) calc(${tick}% + 1px),transparent calc(${tick}% + 1px) 100%)`;
        range[0].style.setProperty('--ogc-track', mark + ',' + band);
    }

    static renderDelta(el, name, f, cur, ref, changed){
        let delta = el.find('.ogc-delta');
        if (!changed){
            delta.removeClass('ogc-show').empty();
            return;
        }
        let refLabel = OGParameters.refLabel();
        let html = '';
        if (f.dimension == 'by_j' || f.dimension == 'by_year'){
            let n = 0;
            $.each(cur || [], function (i, v) {
                let r = ($.isArray(ref) && ref.length > i) ? ref[i] : null;
                if (!Model.equal(v, r)){ n++; }
            });
            html = `<span class="ogc-to">${n} of ${(cur || []).length} changed</span>`
                + `<span class="ogc-from">vs ${esc(refLabel)}</span>`;
        }else if (typeof cur == 'number' && typeof ref == 'number'){
            let diff = cur - ref;
            let up = diff > 0;
            let defRef = (!Model.equal(ref, f.def) && !Model.equal(f.def, cur) && typeof f.def == 'number')
                ? `<span class="ogc-from" title="calibration default">def ${esc(OGParameters.fmt(f.def))}</span><span class="ogc-arr">&middot;</span>`
                : '';
            html = defRef
                + `<span class="ogc-from" title="${esc(refLabel)}">${esc(OGParameters.fmt(ref))}</span>`
                + `<span class="ogc-arr">&rarr;</span>`
                + `<span class="ogc-to">${esc(OGParameters.fmt(cur))}</span>`
                + `<span class="ogc-dnum">${up ? '+' : ''}${esc(OGParameters.fmt(diff))}</span>`;
        }else{
            html = `<span class="ogc-from">${esc(OGParameters.fmt(ref))}</span>`
                + `<span class="ogc-arr">&rarr;</span>`
                + `<span class="ogc-to">${esc(OGParameters.fmt(cur))}</span>`;
        }
        html += `<button class="ogc-freset" data-act="reset-field" title="Reset to ${esc(refLabel)}"><i class="fa fa-undo"></i></button>`;
        delta.html(html).addClass('ogc-show');
    }

    static refLabel(){
        let model = OGParameters.model;
        if (previewRef == 'auto'){
            return model.isReform ? (model.selection.baseline_run || 'its baseline') : 'calibration default';
        }
        if (previewRef == 'def'){
            return 'calibration default';
        }
        return previewRef;
    }

    static refreshAll(){
        let model = OGParameters.model;
        $.each(model.fields, function (name, f) {
            OGParameters.refreshField(name);
        });
        OGParameters.refreshTotals();
    }

    static refreshTotals(){
        let total = 0;
        $('#ogcParamsBody .ogc-acc').each(function () {
            let n = $(this).find('.ogc-field.ogc-changed').length;
            total += n;
            $(this).toggleClass('ogc-haschange', n > 0);
            $(this).find('.ogc-chgbadge')
                .text(n + ' changed')
                .css('display', n > 0 ? 'inline-block' : 'none');
        });
        $('#ogcChangeCount').text(total + (total == 1 ? ' change' : ' changes'));
        let preview = previewRef != 'auto' ? ' (preview)' : '';
        $('#ogcChangeVs').text('vs ' + OGParameters.refLabel() + preview);
    }

    static setPreviewRef(value){
        previewRef = value;
        if (value != 'auto' && value != 'def' && !OGParameters.model.otherRefs[value]){
            let pageID = PAGE_ID;
            let casename = OGParameters.model.selection.casename;
            Ogc.getParams(casename, value)
            .then(r => {
                if (!OGParameters.isCurrent(pageID)){
                    return;
                }
                OGParameters.model.otherRefs[value] = r.params || {};
                OGParameters.refreshAll();
            })
            .catch(error => {
                if (!OGParameters.isCurrent(pageID)){
                    return;
                }
                Message.warning('That run\'s parameters could not be read, showing the calibration default instead.');
                OGParameters.model.otherRefs[value] = {};
                OGParameters.refreshAll();
            });
            return;
        }
        OGParameters.refreshAll();
    }

    static resetField(name){
        let model = OGParameters.model;
        let target = model.base[name];
        model.cur[name] = $.isArray(target) ? target.slice() : target;
        OGParameters.writeWidget(name, model.cur[name]);
        dirty = true;
        OGParameters.refreshField(name);
        OGParameters.refreshTotals();
    }

    static resetAll(){
        let model = OGParameters.model;
        $.each(model.changedNames(), function (id, name) {
            let target = model.base[name];
            model.cur[name] = $.isArray(target) ? target.slice() : target;
            OGParameters.writeWidget(name, model.cur[name]);
        });
        dirty = true;
        OGParameters.refreshAll();
    }

    static save(){
        let model = OGParameters.model;
        let bad = [];
        $.each(model.fields, function (name, f) {
            if (!model.editable(name)){
                return;
            }
            if (f.dimension == 'by_j' || f.dimension == 'by_year'){
                $.each(model.cur[name] || [], function (id, v) {
                    if (OGParameters.outOfRange(f, v) && $.inArray(name, bad) < 0){
                        bad.push(name);
                    }
                });
            }else if (OGParameters.outOfRange(f, model.cur[name])){
                bad.push(name);
            }
        });
        if (bad.length){
            Message.warning('Some values are outside the range the model accepts: ' + bad.join(', ') + '.');
            return;
        }
        let sumBad = [];
        $.each(model.fields, function (name, f) {
            if (f.constraint != 'sum_to_one' || !model.editable(name)){
                return;
            }
            let sum = 0;
            $.each(model.cur[name] || [], function (id, v) { sum += (typeof v == 'number' ? v : 0); });
            if (Math.abs(sum - 1) >= 0.0005){
                sumBad.push(name);
            }
        });
        if (sumBad.length){
            Message.warning('These must total 1 before saving: ' + sumBad.join(', ') + '.');
            return;
        }

        let pageID = PAGE_ID;
        let payload = model.savePayload();
        let count = model.changedNames().length;
        Ogc.saveParams(model.selection.casename, model.selection.run_name, payload)
        .then(response => {
            dirty = false;
            if (count){
                let stale = [model.selection.casename + ':' + model.selection.run_name];
                if (!model.isReform){
                    $.each(OGParameters.runs || [], function (id, r) {
                        if (r.run_type == 'reform' && r.baseline_run == model.selection.run_name){
                            stale.push(model.selection.casename + ':' + r.run_name);
                        }
                    });
                }
                markRunsStale(stale);
            }
            Message.smallBoxInfo('OG-Core',
                count ? (count + ' change' + (count == 1 ? '' : 's') + ' saved.') : 'Saved with no changes.',
                3500);
            if (!model.isReform && count){
                let reforms = $.map(OGParameters.runs || [], function (r) {
                    return (r.run_type == 'reform' && r.baseline_run == model.selection.run_name) ? r : null;
                });
                if (reforms.length){
                    Message.warning(reforms.length + ' reform' + (reforms.length == 1 ? '' : 's')
                        + ' built on this baseline will need re-running.');
                }
            }
            if (!OGParameters.isCurrent(pageID)){
                return;
            }
            OGParameters.refreshAll();
        })
        .catch(error => Message.danger(error));
    }

    static initEvents(){
        NavigationGuard.activate({
            hasChanges: () => dirty,
            update: () => OGParameters.save()
        });

        $('#ogcParamsBody').off('input.ogcparams').on('input.ogcparams', 'input[data-role]', function () {
            let name = $(this).closest('.ogc-field').attr('data-param');
            let role = $(this).attr('data-role');
            if (role == 'range'){
                $(this).closest('.ogc-rangewrap').find('[data-role="num"]').val($(this).val());
            }else if (role == 'num'){
                $(this).closest('.ogc-rangewrap').find('[data-role="range"]').val($(this).val());
            }
            OGParameters.onEdit(name);
        });

        $('#ogcParamsBody').off('change.ogcparams').on('change.ogcparams', 'select[data-role]', function () {
            OGParameters.onEdit($(this).closest('.ogc-field').attr('data-param'));
        });

        $('#ogcParamsBody').off('click.ogcparams').on('click.ogcparams', '[data-act]', function (e) {
            e.preventDefault();
            let field = $(this).closest('.ogc-field');
            let name = field.attr('data-param');
            let act = $(this).attr('data-act');
            if (act == 'reset-field'){
                OGParameters.resetField(name);
                return;
            }
            let vals = OGParameters.readWidget(name);
            if (act == 'add-year'){
                vals.push(vals.length ? vals[vals.length - 1] : null);
            }
            if (act == 'remove-year'){
                vals.splice(parseInt($(this).closest('.ogc-pathcell').find('input').attr('data-index'), 10), 1);
            }
            OGParameters.model.cur[name] = vals;
            field.replaceWith(OGParameters.fieldHtml(OGParameters.model, name));
            dirty = true;
            OGParameters.refreshField(name);
            OGParameters.refreshTotals();
        });

        $('#ogcParamsEditbar').off('click.ogcparams').on('click.ogcparams', '[data-act]', function (e) {
            e.preventDefault();
            let act = $(this).attr('data-act');
            if (act == 'reset-all') OGParameters.resetAll();
            if (act == 'save') OGParameters.save();
        });

        $('#ogcParamsEditbar').off('change.ogcparams').on('change.ogcparams', '#ogcOnlyChanged', function () {
            $('#ogcParamsBody').toggleClass('ogc-onlychanged', this.checked);
            OGParameters.refreshAll();
        });

        $('#ogcParamsCtx').off('change.ogcparams').on('change.ogcparams', '#ogcCmpRef', function () {
            OGParameters.setPreviewRef($(this).val());
        });
    }
}
