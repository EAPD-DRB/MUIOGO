import { Ogc } from "../../Classes/Ogc.Class.js";
import { escapeHtml as esc } from "../../Classes/Html.Class.js";
import OGCases, { loadWorkspace, saveSelection } from "./OGCases.js";
import * as V from "../Model/OGResultsView.js";
import * as D from "../Model/OGResultsData.js";

// OG-Core Results. Nothing is drawn until a run is chosen in the picker: "View"
// shows one run, "Compare" shows a reform against its baseline. The report reads
// one labelled, unit-consistent payload (/ogc/getResultsReport); Explore data uses
// the same catalog, units and population weights, so both views always agree.

const ECHARTS_URL = 'References/echarts/echarts-6.1.0.min.js';
const RECENT_KEY = 'osy-ogc-results-recent';
const RECENT_MAX = 5;
// OG-Core builds each analysis table in a fresh worker process, so tables are kept
// for the few most recent selections and returning to one costs nothing.
const TABLE_CACHE_MAX = 5;
const CATEGORY_ORDER = ['Output', 'Prices', 'Government', 'Households', 'Other', 'Diagnostics'];
const HOUSEHOLD_ORDER = ['c', 'n', 'b_sp1', 'before_tax_income', 'labor_income', 'hh_net_taxes', 'etr', 'mtrx', 'mtry'];
let PAGE_ID = 0;

function routePath(){
    let path = String(window.location.hash || '').replace(/^#/, '').split('?')[0] || '/';
    return path.length > 1 ? path.replace(/\/+$/, '') : path;
}

function readRecent(){
    try {
        let list = JSON.parse(localStorage.getItem(RECENT_KEY));
        return Array.isArray(list) ? list : [];
    } catch (e) { return []; }
}



export default class OGResults {

    static onLoad(){
        PAGE_ID++;
        OGResults.pageID = PAGE_ID;
        OGResults.teardown();
        OGResults.workspace = loadWorkspace();
        if (!OGResults.workspace || !OGResults.workspace.country_id){
            window.location.hash = '#/OGCore';
            return;
        }
        OGResults.cases = [];
        OGResults.selection = null;
        OGResults.report = null;
        OGResults.requestID = 0;
        OGResults.hh = {name: null, view: 'avg', scenario: 'baseline', group: 0};
        OGResults.ex = null;
        OGResults.ssData = null;
        OGResults.tpiCache = Object.create(null);
        OGResults.tableCache = new Map();
        OGResults.ogTables = Object.create(null);
        OGResults.activeOgTable = null;
        OGResults.initEvents();
        const pageID = PAGE_ID;
        Promise.all([OGResults.loadECharts(), OGResults.loadTree()])
            .then(() => {
                if (!OGResults.isCurrent(pageID)) return;
                let requested = V.parseSelection(window.location.hash);
                if (requested && OGResults.availability(requested).ok){
                    OGResults.select(requested);
                }else{
                    OGResults.showIntro();
                }
            })
            .catch(error => { if (OGResults.isCurrent(pageID)) OGResults.showError(String(error)); });
    }

    static isCurrent(pageID = OGResults.pageID){
        return pageID == PAGE_ID && localStorage.getItem('osy-pageId') == 'OGResults' && routePath() == '/OGResults';
    }

    static loadECharts(){
        if (window.echarts) return Promise.resolve(window.echarts);
        if (OGResults.echartsPromise) return OGResults.echartsPromise;
        OGResults.echartsPromise = new Promise((resolve, reject) => {
            let script = document.createElement('script');
            script.id = 'ogc-echarts-runtime';
            script.src = ECHARTS_URL;
            script.async = true;
            script.addEventListener('load', () => resolve(window.echarts), {once: true});
            script.addEventListener('error', () => {
                script.remove();
                OGResults.echartsPromise = null;
                reject('Charts could not be loaded.');
            }, {once: true});
            document.head.appendChild(script);
        });
        return OGResults.echartsPromise;
    }

    // ── picker ───────────────────────────────────────────────────────────────
    static loadTree(){
        let country = OGResults.workspace.country_id;
        return Ogc.getCases(country).then(response => {
            let cases = $.isArray(response) ? response : (response.cases || []);
            cases = $.grep(cases, item => item.country_id == country);
            return Promise.all($.map(cases, item => Ogc.getRuns(country, item.casename)
                .then(result => Object.assign({}, item, {runs: result.runs || []}))
                .catch(() => Object.assign({}, item, {runs: []}))));
        }).then(cases => {
            OGResults.cases = cases;
            OGResults.renderTree();
            OGResults.renderRecent();
        });
    }

    static findCase(casename){
        return $.grep(OGResults.cases, c => c.casename == casename)[0] || null;
    }

    static findRun(c, runName){
        return c ? $.grep(c.runs, r => r.run_name == runName)[0] || null : null;
    }

    static runReady(run){
        if (!run) return {ok: false, reason: 'This run no longer exists.'};
        if (run.status != 'completed') return {ok: false, reason: 'Not run yet.'};
        if (run.reusable === false) return {ok: false, reason: run.stale_reason || 'Out of date: run it again.'};
        return {ok: true};
    }

    static availability(sel){
        let c = OGResults.findCase(sel.casename);
        let base = OGResults.findRun(c, sel.base);
        let ready = OGResults.runReady(base);
        if (!ready.ok || !sel.reform) return ready;
        let reform = OGResults.findRun(c, sel.reform);
        if (!reform || reform.baseline_run != sel.base) return {ok: false, reason: 'This reform is not built on that baseline.'};
        return OGResults.runReady(reform);
    }

    static displayName(c, run){
        return OGCases.displayName(c, run);
    }

    static selectionLabel(sel){
        let c = OGResults.findCase(sel.casename);
        let base = OGResults.findRun(c, sel.base);
        let baseName = base ? OGResults.displayName(c, base) : sel.base;
        if (!sel.reform) return {kicker: 'Run', title: baseName, base: baseName};
        let reform = OGResults.findRun(c, sel.reform);
        let reformName = reform ? OGResults.displayName(c, reform) : sel.reform;
        return {kicker: 'Comparison', title: `${baseName} → ${reformName}`, base: baseName, reform: reformName};
    }

    static renderTree(){
        let filter = String($('#ogcRsSearch').val() || '').toLowerCase();
        let html = '';
        let anyReady = false;
        $.each(OGResults.cases, (_, c) => {
            let baselines = $.grep(c.runs, r => r.run_type == 'baseline');
            if (!baselines.length) return;
            let rows = '';
            $.each(baselines, (_, base) => {
                let baseName = OGResults.displayName(c, base);
                let reforms = $.grep(c.runs, r => r.run_type == 'reform' && r.baseline_run == base.run_name);
                let matches = !filter || (c.casename + ' ' + baseName + ' ' + reforms.map(r => r.run_name).join(' ')).toLowerCase().indexOf(filter) >= 0;
                if (!matches) return;
                let ready = OGResults.runReady(base);
                anyReady = anyReady || ready.ok;
                rows += OGResults.treeRow(c, base, null, baseName, ready);
                $.each(reforms, (_, reform) => {
                    let reformReady = OGResults.runReady(reform);
                    let pairReady = ready.ok ? reformReady : {ok: false, reason: 'Its baseline has no current results.'};
                    anyReady = anyReady || reformReady.ok;
                    rows += OGResults.treeRow(c, reform, base, OGResults.displayName(c, reform), reformReady, pairReady);
                });
            });
            if (rows) html += `<div class="ogc-rs-case" role="listitem"><div class="ogc-rs-case-name">${esc(c.casename)}</div>${rows}</div>`;
        });
        if (!html){
            html = filter
                ? '<div class="ogc-rs-tree-empty">No runs match this filter.</div>'
                : '<div class="ogc-rs-tree-empty">No runs yet. Create a case and run it to see results here.<br><a class="btn ogc-btn ogc-btn-sm ogc-btn-soft" href="#/OGCases">Go to Cases</a></div>';
        }else if (!anyReady && !filter){
            html = '<div class="ogc-rs-tree-empty">No completed runs yet.<br><a class="btn ogc-btn ogc-btn-sm ogc-btn-soft" href="#/OGRuns">Go to Run</a></div>' + html;
        }
        $('#ogcRsTree').html(html);
        OGResults.markActive();
    }

    static treeRow(c, run, base, name, ready, pairReady){
        let isReform = !!base;
        let attrs = `data-case="${esc(c.casename)}" data-base="${esc(isReform ? base.run_name : run.run_name)}"`;
        let meta = [];
        if (ready.ok){
            meta.push(run.time_path ? 'Transition path' : 'Steady state');
            if (run.completed_at) meta.push(new Date(run.completed_at).toLocaleDateString());
        }else{
            meta.push(ready.reason);
        }
        let view = `<button type="button" class="btn ogc-btn ogc-btn-sm ogc-btn-row" data-rs-act="view" ${attrs} ${isReform ? `data-view="${esc(run.run_name)}"` : ''} title="View this run on its own"${ready.ok ? '' : ' disabled'}><i class="fa fa-eye" aria-hidden="true"></i><span class="ogc-btn-txt">View</span></button>`;
        let compare = isReform
            ? `<button type="button" class="btn ogc-btn ogc-btn-sm ogc-btn-soft" data-rs-act="compare" ${attrs} data-reform="${esc(run.run_name)}" title="${pairReady.ok ? 'Compare this reform with its baseline' : esc(pairReady.reason)}"${pairReady.ok ? '' : ' disabled'}><i class="fa fa-exchange" aria-hidden="true"></i> Compare</button>`
            : '';
        return `<div class="ogc-rs-run${isReform ? ' ogc-rs-run-reform' : ''}${ready.ok ? '' : ' ogc-rs-run-off'}" data-key="${esc(c.casename + '|' + (isReform ? base.run_name + '|' + run.run_name : run.run_name))}" data-single="${esc(c.casename + '|' + run.run_name)}">
            <div class="ogc-rs-run-text">
                <span class="ogc-tag ogc-tag-${isReform ? 'reform' : 'base'}">${isReform ? 'reform' : 'baseline'}</span>
                <b title="${esc(name)}">${esc(name)}</b>
                <small>${esc(meta.join(' · '))}</small>
            </div>
            <div class="ogc-rs-run-acts">${view}${compare}</div>
        </div>`;
    }

    static markActive(){
        $('.ogc-rs-run').removeClass('ogc-rs-run-on');
        let sel = OGResults.selection;
        if (!sel) return;
        let key = sel.casename + '|' + sel.base + (sel.reform ? '|' + sel.reform : '');
        let attr = sel.reform ? 'data-key' : 'data-single';
        $('.ogc-rs-run').filter(function () { return $(this).attr(attr) == key; }).addClass('ogc-rs-run-on');
    }

    static renderRecent(){
        let country = OGResults.workspace.country_id;
        let items = $.grep(readRecent(), item => item.country_id == country && OGResults.availability(item).ok);
        if (!items.length){
            $('#ogcRsRecent').hide().empty();
            return;
        }
        $('#ogcRsRecent').html(`<div class="ogc-rs-recent-label">Recent</div>` + items.map(item => {
            let label = OGResults.selectionLabel(item);
            return `<button type="button" class="ogc-rs-recent-item" data-rs-act="recent" data-case="${esc(item.casename)}" data-base="${esc(item.base)}" data-reform="${esc(item.reform || '')}" title="${esc(label.title)}"><i class="fa fa-${item.reform ? 'exchange' : 'eye'}" aria-hidden="true"></i> ${esc(label.title)}</button>`;
        }).join('')).show();
    }

    static remember(sel){
        let country = OGResults.workspace.country_id;
        let key = V.selectionKey(country, sel);
        let list = $.grep(readRecent(), item => V.selectionKey(item.country_id, item) != key);
        list.unshift({country_id: country, casename: sel.casename, base: sel.base, reform: sel.reform || null});
        try { localStorage.setItem(RECENT_KEY, JSON.stringify(list.slice(0, RECENT_MAX * 4))); } catch (e) { /* storage full: recents are optional */ }
    }

    // ── selection and loading ────────────────────────────────────────────────
    static select(sel){
        OGResults.selection = {casename: sel.casename, base: sel.base, reform: sel.reform || null, tab: sel.tab || 'report'};
        OGResults.syncUrl();
        OGResults.remember(OGResults.selection);
        OGResults.renderRecent();
        OGResults.markActive();
        OGResults.load();
    }

    // Keep the selection in the address bar without re-routing the page, so a
    // refresh, the back button or a shared link reopens the same view.
    static syncUrl(){
        let hash = V.selectionHash(OGResults.selection);
        if (window.location.hash != hash) history.replaceState(null, '', hash);
    }

    static load(){
        let sel = OGResults.selection;
        let country = OGResults.workspace.country_id;
        let requestID = ++OGResults.requestID;
        const pageID = OGResults.pageID;
        OGResults.disposeCharts();
        OGResults.ssData = null;
        OGResults.tpiCache = Object.create(null);
        OGResults.ogTables = OGResults.tablesFor(sel);
        OGResults.ex = null;
        $('#ogcRsIntro, #ogcRsError, #ogcRsView').hide();
        $('#ogcRsLoading').show();
        let params = run => Ogc.getParams(country, sel.casename, run).then(r => r.params || {}).catch(() => null);
        Promise.all([
            Ogc.getResultsReport(country, sel.casename, sel.base, sel.reform),
            params(sel.base),
            sel.reform ? params(sel.reform) : Promise.resolve(null),
            sel.reform ? Ogc.getParameterSchema(country, sel.casename).catch(() => null) : Promise.resolve(null)
        ]).then(([report, baseParams, reformParams, schema]) => {
            if (!OGResults.isCurrent(pageID) || requestID != OGResults.requestID) return;
            if (!report || report.status_code == 'running'){
                OGResults.showError('This run is still solving. Results appear here when it finishes.');
                return;
            }
            OGResults.report = report;
            OGResults.policy = (sel.reform && baseParams && reformParams && schema)
                ? V.policyChanges(baseParams, reformParams, schema) : null;
            let first = HOUSEHOLD_ORDER.find(name => report.households && report.households[name]);
            OGResults.hh = {name: first || null, view: 'avg', scenario: 'baseline', group: 0};
            OGResults.render();
        }).catch(error => {
            if (!OGResults.isCurrent(pageID) || requestID != OGResults.requestID) return;
            OGResults.showError('These results could not be loaded. ' + String(error && error.message || error));
        });
    }

    static showIntro(){
        OGResults.selection = null;
        OGResults.markActive();
        OGResults.disposeCharts();
        $('#ogcRsLoading, #ogcRsError, #ogcRsView').hide();
        $('#ogcRsIntro').show();
    }

    static showError(text){
        OGResults.disposeCharts();
        $('#ogcRsLoading, #ogcRsIntro, #ogcRsView').hide();
        $('#ogcRsError').html(`<i class="fa fa-exclamation-circle" aria-hidden="true"></i> ${esc(text)}`).show();
    }

    // ── rendering: header and report ─────────────────────────────────────────
    static render(){
        let label = OGResults.selectionLabel(OGResults.selection);
        $('#ogcRsKicker').text(label.kicker);
        $('#ogcRsTitle').text(label.title);
        $('#ogcRsFacts').html(OGResults.factsHtml());
        $('#ogcRsLoading').hide();
        $('#ogcRsView').show();
        OGResults.renderReport();
        OGResults.openTab(OGResults.selection.tab || 'report');
        OGResults.bindResize();
    }

    static factsHtml(){
        let report = OGResults.report;
        let facts = [];
        facts.push(report.analysis == 'transition'
            ? `<span class="ogc-rs-fact" title="Year-by-year transition and the long-run steady state"><i class="fa fa-road" aria-hidden="true"></i> Transition path + long run</span>`
            : `<span class="ogc-rs-fact" title="Only the long-run steady state was solved"><i class="fa fa-anchor" aria-hidden="true"></i> Long run (steady state) only</span>`);
        let c = OGResults.findCase(OGResults.selection.casename);
        let run = OGResults.findRun(c, OGResults.selection.reform || OGResults.selection.base);
        if (run && run.completed_at) facts.push(`<span class="ogc-rs-fact"><i class="fa fa-clock-o" aria-hidden="true"></i> ${esc(new Date(run.completed_at).toLocaleString())}</span>`);
        let diag = [report.diagnostics.baseline, report.diagnostics.reform].filter(Boolean);
        if (diag.length){
            let ok = diag.every(d => d.converged);
            let worst = Math.max(...diag.flatMap(d => Object.values(d.values)));
            facts.push(`<span class="ogc-rs-fact ogc-rs-fact-${ok ? 'ok' : 'warn'}" title="Largest steady-state Euler / resource-constraint error: ${esc(worst.toExponential(1))}"><i class="fa fa-${ok ? 'check-circle' : 'exclamation-triangle'}" aria-hidden="true"></i> ${ok ? 'Solution converged' : 'Check solution accuracy'}</span>`);
        }
        return facts.join('');
    }

    static section(id, title, subtitle, body){
        return `<section class="ogc-rs-section" id="${id}">
            <div class="ogc-rs-section-head"><h2>${esc(title)}</h2>${subtitle ? `<p>${subtitle}</p>` : ''}</div>
            ${body}
        </section>`;
    }

    static card(chartId, period, title, opts = {}){
        return `<article class="ogc-rs-card${opts.wide ? ' ogc-rs-wide' : ''}">
            <header class="ogc-rs-card-head">
                <div><div class="ogc-rs-card-period">${esc(period)}</div><h3>${esc(title)}</h3>${opts.sub ? `<div class="ogc-rs-card-sub">${esc(opts.sub)}</div>` : ''}</div>
                <div class="ogc-rs-card-tools">${opts.tools || ''}${chartId ? OGResults.exportMenu(chartId) : ''}</div>
            </header>
            ${opts.before || ''}
            ${chartId ? `<div class="ogc-rs-chart${opts.tall ? ' ogc-rs-chart-lg' : ''}" id="${chartId}"></div>` : ''}
            ${opts.after || ''}
        </article>`;
    }

    static exportMenu(chartId){
        return `<span class="ogc-action-menu"><button type="button" class="btn ogc-btn ogc-btn-sm ogc-btn-row ogc-btn-more" data-rs-act="menu" aria-haspopup="menu" aria-expanded="false" title="Download"><i class="fa fa-ellipsis-v" aria-hidden="true"></i><span class="ogc-btn-txt">Download</span></button>
            <span class="ogc-case-menu" role="menu" aria-hidden="true">
                <button type="button" role="menuitem" data-rs-act="export" data-chart="${chartId}" data-format="png"><i class="fa fa-file-image-o" aria-hidden="true"></i> Download PNG</button>
                <button type="button" role="menuitem" data-rs-act="export" data-chart="${chartId}" data-format="svg"><i class="fa fa-file-code-o" aria-hidden="true"></i> Download SVG</button>
            </span></span>`;
    }

    static renderReport(){
        let report = OGResults.report;
        let compare = report.mode == 'compare';
        let sections = [];
        let html = '';
        let identical = compare && OGResults.policy && !OGResults.policy.length;
        if (identical){
            html += `<div class="ogc-rs-guard"><i class="fa fa-clone" aria-hidden="true"></i><div>
                <b>This reform has the same parameters as its baseline.</b>
                <p>Every result would be unchanged, so there is nothing to compare yet. Change at least one parameter in the reform, run it, and come back.</p>
                <button type="button" class="btn ogc-btn ogc-btn-main" data-rs-act="edit-reform"><i class="fa fa-pencil" aria-hidden="true"></i> Edit reform parameters</button>
            </div></div>`;
            $('#ogcRsSections').empty();
            $('[data-rs-pane="report"]').html(html);
            return;
        }
        html += OGResults.summaryHtml(); sections.push(['rs-summary', 'Summary']);
        if (compare){ html += OGResults.policyHtml(); sections.push(['rs-policy', 'Policy']); }
        html += OGResults.macroHtml(); sections.push(['rs-macro', 'Macroeconomy']);
        html += OGResults.fiscalHtml(); sections.push(['rs-fiscal', 'Government']);
        html += OGResults.householdsHtml(); sections.push(['rs-households', 'Households']);
        html += OGResults.section('rs-table', report.transition ? 'Main results table' : 'Long-run results table',
            report.transition
                ? `${compare ? 'Changes' : 'Values'} in each of the first ${report.transition.budget_window} years (${esc(V.windowLabel(report.transition.years, report.transition.budget_window))}) and in the long run.`
                : `${V.LONG_RUN}.`,
            `<article class="ogc-rs-card"><header class="ogc-rs-card-head"><div></div><div class="ogc-rs-card-tools"><button type="button" class="btn ogc-btn ogc-btn-sm ogc-btn-soft" data-rs-act="main-csv"><i class="fa fa-download" aria-hidden="true"></i> CSV</button></div></header><div class="ogc-rs-grid" id="ogcRsMainTable"></div></article>`);
        sections.push(['rs-table', 'Table']);
        $('#ogcRsSections').html(sections.map(([id, name]) => `<button type="button" data-rs-act="jump" data-target="${id}">${esc(name)}</button>`).join(''));
        $('[data-rs-pane="report"]').html(html);
        OGResults.drawMacro();
        OGResults.drawFiscal();
        OGResults.drawHouseholds();
        OGResults.drawMainTable();
    }

    static kpiCard(row, compare){
        let flag = row.negative_baseline ? `<span class="ogc-rs-flag" title="The baseline value is negative, so a percent change would mislead.">negative baseline</span>` : '';
        if (compare){
            let tone = V.changeTone(row.change);
            let icon = tone == 'up' ? 'fa-arrow-up' : tone == 'down' ? 'fa-arrow-down' : 'fa-minus';
            let fromTo = row.value_unit == 'model units'
                ? `${V.formatValue(row.baseline, row.value_unit)} → ${V.formatValue(row.reform, row.value_unit)} <span class="ogc-mut">model units</span>`
                : `${V.formatValue(row.baseline, row.value_unit)} → ${V.formatValue(row.reform, row.value_unit)}`;
            return `<article class="ogc-rs-kpi ogc-rs-${tone}">
                <span class="ogc-rs-kpi-label">${esc(row.short)}</span>
                <strong><i class="fa ${icon}" aria-hidden="true"></i> ${esc(V.formatChange(row.change, row.change_unit))}</strong>
                <small>${fromTo}</small>${flag}
            </article>`;
        }
        return `<article class="ogc-rs-kpi">
            <span class="ogc-rs-kpi-label">${esc(row.short)}</span>
            <strong>${esc(V.formatValue(row.baseline, row.value_unit))}</strong>
            <small>${esc(V.valueUnitLabel(row.value_unit))}</small>${flag}
        </article>`;
    }

    static summaryHtml(){
        let report = OGResults.report;
        let compare = report.mode == 'compare';
        let rows = compare ? report.summary : D.singleSummaryRows(OGResults.report);
        let cards = rows.map(row => OGResults.kpiCard(row, compare)).join('');
        let note = '';
        if (compare){
            let tiny = report.summary.every(row => !V.finite(row.change) || Math.abs(row.change) < 0.01);
            if (tiny) note = `<div class="ogc-rs-note"><i class="fa fa-info-circle" aria-hidden="true"></i> Every headline change is smaller than 0.01. The reform barely moves the long-run economy.</div>`;
        }
        let sub = compare
            ? `${V.LONG_RUN} · reform compared with baseline. Quantities in percent, rates in percentage points, government in percentage points of GDP.`
            : `${V.LONG_RUN} · shares of GDP and rates, which read the same in any currency. Levels are in the Explore data view.`;
        return OGResults.section('rs-summary', 'Summary', sub, `<div class="ogc-rs-kpis">${cards}</div>${note}`);
    }

    static policyHtml(){
        let changes = OGResults.policy;
        let body;
        if (!changes){
            body = '<div class="ogc-rs-note">The parameter changes could not be read for this pair.</div>';
        }else{
            let item = change => `<li><div><b>${esc(change.label)}</b> <code>${esc(change.name)}</code></div><span>${esc(V.describeParameter(change.base))} <i class="fa fa-long-arrow-right" aria-hidden="true"></i> <b>${esc(V.describeParameter(change.reform))}</b></span></li>`;
            let shown = changes.slice(0, 6).map(item).join('');
            let rest = changes.slice(6);
            body = `<ul class="ogc-rs-policy">${shown}</ul>` + (rest.length
                ? `<details class="ogc-rs-more"><summary>Show ${rest.length} more</summary><ul class="ogc-rs-policy">${rest.map(item).join('')}</ul></details>` : '');
        }
        let count = changes ? `${changes.length} parameter${changes.length == 1 ? '' : 's'} differ between the baseline and the reform.` : '';
        return OGResults.section('rs-policy', 'Policy changes', count, `<article class="ogc-rs-card">${body}</article>`);
    }

    static macroHtml(){
        let report = OGResults.report;
        let compare = report.mode == 'compare';
        let t = report.transition;
        if (t){
            let names = ['Y', 'C', 'I', 'K', 'L', 'w', 'r'].filter(name => t.series[name]);
            let cards = names.map(name => {
                let s = t.series[name];
                let unit = compare ? s.change_unit : s.value_unit;
                let steady = compare ? s.steady.change : s.steady.baseline;
                let steadyText = compare ? V.formatChange(steady, unit) : V.formatValue(steady, unit);
                return `<article class="ogc-rs-mini">
                    <header><h3>${esc(s.short)}</h3><span title="${esc(V.LONG_RUN)}">Long run <b>${esc(steadyText)}</b></span></header>
                    <div class="ogc-rs-mini-unit">${esc(compare ? V.changeUnitLabel(unit) : V.valueUnitLabel(unit))}</div>
                    <div class="ogc-rs-chart ogc-rs-chart-sm" id="rsPath_${name}"></div>
                </article>`;
            }).join('');
            let sub = `${compare ? 'Change from the baseline' : 'Values'} over the transition path, ${esc(t.years[0])}–${esc(t.years[t.years.length - 1])}. The shaded band is the first ${t.budget_window} years; the dashed line is the long run.`;
            return OGResults.section('rs-macro', 'Macroeconomy', sub, `<div class="ogc-rs-multiples">${cards}</div>`);
        }
        if (!compare){
            return OGResults.section('rs-macro', 'Macroeconomy', `${V.LONG_RUN}. This run was solved for the long run only; run it with the transition path to see year-by-year effects.`,
                OGResults.levelsTable(report.macro.concat(report.prices)));
        }
        let prices = report.prices.map(row => `<li><span>${esc(row.label)}</span><b class="ogc-rs-${V.changeTone(row.change)}">${esc(V.formatChange(row.change, row.change_unit))}</b><small>${esc(V.formatValue(row.baseline, '%'))} → ${esc(V.formatValue(row.reform, '%'))}</small></li>`).join('');
        return OGResults.section('rs-macro', 'Macroeconomy',
            `${V.LONG_RUN}. Solved for the long run only; run both with the transition path to see year-by-year effects.`,
            `<div class="ogc-rs-two">
                ${OGResults.card('rsMacroBars', V.LONG_RUN, 'Long-run change in output, capital, labor and wages', {sub: 'Percent change from the baseline'})}
                ${OGResults.card(null, V.LONG_RUN, 'Long-run change in interest rates', {sub: 'Percentage points', after: `<ul class="ogc-rs-rates">${prices}</ul>`})}
            </div>`);
    }

    static levelsTable(rows){
        let body = rows.map(row => `<tr><td>${esc(row.label)}</td><td class="ogc-num">${esc(V.formatValue(row.baseline, row.value_unit))}</td><td class="ogc-mut">${esc(V.valueUnitLabel(row.value_unit))}</td></tr>`).join('');
        return `<article class="ogc-rs-card"><table class="ogc-table ogc-rs-levels"><thead><tr><th>Variable</th><th class="ogc-num">Long-run value</th><th>Unit</th></tr></thead><tbody>${body}</tbody></table></article>`;
    }

    static fiscalHtml(){
        let report = OGResults.report;
        let compare = report.mode == 'compare';
        let t = report.transition;
        let negatives = report.fiscal.filter(row => row.negative_baseline);
        let negNote = negatives.length
            ? `<div class="ogc-rs-note ogc-rs-note-warn"><i class="fa fa-exclamation-triangle" aria-hidden="true"></i> Negative baseline: ${negatives.map(row => esc(row.label)).join(', ')}. ${negatives.length == 1 ? 'It is' : 'They are'} compared as a share of GDP, not as a percent change.</div>` : '';
        let cards = '';
        if (compare){
            cards += OGResults.card('rsFiscalBars', V.LONG_RUN, 'Long-run change in government finances', {sub: 'Percentage points of GDP', tall: true});
        }else{
            cards += `<article class="ogc-rs-card"><header class="ogc-rs-card-head"><div><div class="ogc-rs-card-period">${esc(V.LONG_RUN)}</div><h3>Government finances as a share of GDP</h3></div></header>${OGResults.levelsTable(report.fiscal).replace(/^<article class="ogc-rs-card">|<\/article>$/g, '')}</article>`;
        }
        if (t && t.series.D){
            cards += OGResults.card('rsDebtPath', `Transition path, ${t.years[0]}–${t.years[t.years.length - 1]}`, 'Government debt over the transition path', {sub: 'Share of GDP (%)'});
        }
        if (t && t.series.total_tax_revenue){
            cards += OGResults.card('rsRevenuePath', `Transition path, ${t.years[0]}–${t.years[t.years.length - 1]}`, 'Tax revenue over the transition path', {sub: 'Share of GDP (%)'});
        }
        let sub = 'Government values are shares of each run’s own GDP, so they compare cleanly even when GDP itself changes.';
        return OGResults.section('rs-fiscal', 'Government', sub, `${negNote}<div class="ogc-rs-two">${cards}</div>`);
    }

    static householdsHtml(){
        let report = OGResults.report;
        if (!report.households || !OGResults.hh.name){
            let reason = report.households_reason || 'Household outcomes are not available for this selection.';
            return OGResults.section('rs-households', 'Households', '', `<div class="ogc-rs-note ogc-rs-note-warn"><i class="fa fa-info-circle" aria-hidden="true"></i> ${esc(reason)}</div>`);
        }
        let sub = `${V.LONG_RUN}. Averages use the run’s own population weights by age and lifetime income group.`;
        return OGResults.section('rs-households', 'Households', sub, `
            <div class="ogc-rs-hh-controls" id="ogcRsHhControls"></div>
            <div class="ogc-rs-two ogc-rs-two-lead">
                ${OGResults.card('rsLifecycle', V.LONG_RUN, '', {tall: true})}
                ${OGResults.card('rsGroups', V.LONG_RUN, '', {tall: true})}
            </div>`);
    }

    // ── charts: report ───────────────────────────────────────────────────────
    static drawMacro(){
        let report = OGResults.report;
        let compare = report.mode == 'compare';
        let t = report.transition;
        if (t){
            $.each(t.series, (name, series) => {
                OGResults.setChart('rsPath_' + name, V.pathChart(t.years, series, t.budget_window, report.mode));
            });
            return;
        }
        if (compare){
            let rows = report.macro.map(row => ({label: row.short, value: row.change, baseline: row.baseline, reform: row.reform, valueUnit: row.value_unit, negative: row.negative_baseline}));
            OGResults.setChart('rsMacroBars', V.divergingBars(rows, '%', 'Long-run percent change in macroeconomic aggregates'));
        }
    }

    static drawFiscal(){
        let report = OGResults.report;
        let t = report.transition;
        if (report.mode == 'compare'){
            let rows = report.fiscal.map(row => ({label: row.short, value: row.change, baseline: row.baseline, reform: row.reform, valueUnit: row.value_unit, negative: row.negative_baseline}));
            OGResults.setChart('rsFiscalBars', V.divergingBars(rows, 'pp of GDP', 'Long-run change in government finances, percentage points of GDP'));
        }
        if (t && t.series.D) OGResults.setChart('rsDebtPath', V.scenarioPathChart(t.years, t.series.D, t.budget_window, 'Government debt as a share of GDP over the transition path'));
        if (t && t.series.total_tax_revenue) OGResults.setChart('rsRevenuePath', V.scenarioPathChart(t.years, t.series.total_tax_revenue, t.budget_window, 'Tax revenue as a share of GDP over the transition path'));
    }

    static drawHouseholds(){
        let report = OGResults.report;
        let hh = OGResults.hh;
        if (!report.households || !hh.name) return;
        let compare = report.mode == 'compare';
        let entry = report.households[hh.name];
        let groups = report.meta.group_labels || [];
        let ages = report.meta.ages || [];
        let unit = entry.value_unit;
        let options = HOUSEHOLD_ORDER.filter(name => report.households[name])
            .map(name => `<option value="${name}"${name == hh.name ? ' selected' : ''}>${esc(report.households[name].short)}</option>`).join('');
        let views = [['avg', 'Population average'], ['groups', 'All income groups'], ['group', 'One income group']];
        let controls = `<label class="ogc-rs-field"><span>Outcome</span><select id="ogcRsHhVar">${options}</select></label>
            <div class="ogc-seg" role="group" aria-label="Household view">${views.map(([key, text]) => `<button type="button" class="btn ogc-btn" data-rs-act="hh-view" data-view="${key}" aria-pressed="${hh.view == key}">${text}</button>`).join('')}</div>`;
        if (hh.view == 'groups' && compare){
            controls += `<div class="ogc-seg" role="group" aria-label="Scenario">${['baseline', 'reform'].map(key => `<button type="button" class="btn ogc-btn" data-rs-act="hh-scenario" data-scenario="${key}" aria-pressed="${hh.scenario == key}">${key == 'baseline' ? 'Baseline' : 'Reform'}</button>`).join('')}</div>`;
        }
        if (hh.view == 'group'){
            controls += `<label class="ogc-rs-field"><span>Income group</span><select id="ogcRsHhGroup">${groups.map((g, j) => `<option value="${j}"${j == hh.group ? ' selected' : ''}>${esc(g)}</option>`).join('')}</select></label>`;
        }
        $('#ogcRsHhControls').html(controls);

        let lines = [];
        let title;
        if (hh.view == 'avg'){
            title = `${entry.label} by age: population-weighted average`;
            lines.push({name: 'Baseline', data: entry.by_age.baseline, color: V.COLORS.baseline});
            if (compare) lines.push({name: 'Reform', data: entry.by_age.reform, color: V.COLORS.reform, dashed: true});
        }else if (hh.view == 'groups'){
            let scenario = compare ? hh.scenario : 'baseline';
            title = `${entry.label} by age for every income group: ${scenario == 'baseline' ? 'baseline' : 'reform'}`;
            entry.by_age_group[scenario].forEach((data, j) => lines.push({name: groups[j], data, color: V.GROUP_COLORS[j % V.GROUP_COLORS.length]}));
        }else{
            let j = Math.min(hh.group, groups.length - 1);
            title = `${entry.label} by age: ${groups[j]} income group`;
            lines.push({name: 'Baseline', data: entry.by_age_group.baseline[j], color: V.COLORS.baseline});
            if (compare) lines.push({name: 'Reform', data: entry.by_age_group.reform[j], color: V.COLORS.reform, dashed: true});
        }
        $('#rsLifecycle').closest('.ogc-rs-card').find('h3').first().text(title);
        OGResults.setChart('rsLifecycle', V.lifecycleChart(ages, lines, unit, title));

        let groupCard = $('#rsGroups').closest('.ogc-rs-card');
        if (compare){
            let changeUnit = (entry.group_change.find(item => item.change_unit) || {}).change_unit || entry.overall.change_unit;
            groupCard.find('h3').first().text(`Change in ${entry.short.toLowerCase()} by lifetime income group`);
            groupCard.find('.ogc-rs-card-sub').remove();
            groupCard.find('h3').after(`<div class="ogc-rs-card-sub">${esc(V.changeUnitLabel(changeUnit))} · population average ${esc(V.formatChange(entry.overall.change, entry.overall.change_unit))}</div>`);
            OGResults.setChart('rsGroups', V.groupBars(groups, entry.group_change, changeUnit, `Change in ${entry.label} by lifetime income group`));
        }else{
            groupCard.find('h3').first().text(`Average ${entry.short.toLowerCase()} by lifetime income group`);
            groupCard.find('.ogc-rs-card-sub').remove();
            groupCard.find('h3').after(`<div class="ogc-rs-card-sub">${esc(V.valueUnitLabel(unit))}</div>`);
            OGResults.setChart('rsGroups', V.groupBars(groups, entry.by_group.baseline.map(v => ({change: v})), unit, `Average ${entry.label} by lifetime income group`, true));
        }
    }

    static drawMainTable(){
        let report = OGResults.report;
        let compare = report.mode == 'compare';
        let t = report.transition;
        let columns, data;
        let cell = unitField => function (c){
            let row = c.getRow().getData();
            let value = c.getValue();
            if (compare){
                let el = c.getElement();
                el.classList.remove('ogc-rs-up', 'ogc-rs-down');
                let tone = V.changeTone(value);
                if (tone != 'flat') el.classList.add('ogc-rs-' + tone);
                return V.formatChange(value, row[unitField]).replace(' of GDP', '');
            }
            return V.formatValue(value, row[unitField]).replace(' of GDP', '');
        };
        if (t){
            let n = Math.min(t.budget_window, t.years.length);
            let years = t.years.slice(0, n);
            data = Object.keys(t.series).map(name => {
                let s = t.series[name];
                let values = compare ? s.change : s.baseline;
                let row = {variable: s.label, unit: compare ? s.change_unit : s.value_unit};
                years.forEach((year, i) => { row['y' + year] = values[i]; });
                row.long = compare ? s.steady.change : s.steady.baseline;
                return row;
            });
            columns = [
                {title: 'Variable', field: 'variable', frozen: true, minWidth: 190, headerSort: false},
                {title: 'Unit', field: 'unit', headerSort: false, formatter: c => compare ? V.changeUnitLabel(c.getValue()).replace(' (percentage points)', ' (pp)') : V.valueUnitLabel(c.getValue())}
            ].concat(years.map(year => ({title: String(year), field: 'y' + year, hozAlign: 'right', headerHozAlign: 'right', headerSort: false, formatter: cell('unit')})))
             .concat([{title: 'Long run', field: 'long', hozAlign: 'right', headerHozAlign: 'right', headerSort: false, formatter: cell('unit'), cssClass: 'ogc-rs-longcol'}]);
        }else{
            let rows = report.macro.concat(report.prices, report.fiscal);
            data = rows.map(row => ({variable: row.label, baseline: row.baseline, reform: row.reform, change: row.change, unit: row.value_unit, change_unit: row.change_unit}));
            columns = [{title: 'Variable', field: 'variable', frozen: true, minWidth: 220},
                {title: compare ? 'Baseline' : 'Long-run value', field: 'baseline', hozAlign: 'right', headerHozAlign: 'right', formatter: c => V.formatValue(c.getValue(), c.getRow().getData().unit)}];
            if (compare){
                columns.push({title: 'Reform', field: 'reform', hozAlign: 'right', headerHozAlign: 'right', formatter: c => V.formatValue(c.getValue(), c.getRow().getData().unit)});
                columns.push({title: 'Change', field: 'change', hozAlign: 'right', headerHozAlign: 'right', formatter: cell('change_unit'), sorter: 'number'});
            }
            columns.push({title: 'Unit', field: 'unit', formatter: c => V.valueUnitLabel(c.getValue())});
        }
        OGResults.setGrid('ogcRsMainTable', {data, columns, layout: 'fitDataStretch'});
    }

    // ── explore data ─────────────────────────────────────────────────────────
    static openTab(tab){
        OGResults.selection.tab = tab;
        OGResults.syncUrl();
        $('[data-rs-tab]').each(function () { $(this).attr('aria-selected', $(this).attr('data-rs-tab') == tab ? 'true' : 'false'); });
        $('[data-rs-pane]').each(function () { $(this).toggle($(this).attr('data-rs-pane') == tab); });
        $('#ogcRsSections').toggle(tab == 'report');
        if (tab == 'explore') OGResults.enterExplore();
        OGResults.resizeCharts();
    }

    static enterExplore(){
        if (!OGResults.ex){
            let first = OGResults.report.catalog.Y ? 'Y' : Object.keys(OGResults.report.catalog)[0];
            OGResults.ex = {name: first, period: 'long', show: OGResults.report.mode == 'compare' ? 'change' : 'levels', breakdown: 'avg', scenario: 'baseline', view: 'chart'};
            OGResults.renderVarList();
            OGResults.renderTablePicker();
        }
        OGResults.loadSS().then(() => OGResults.renderExplore());
    }

    static loadSS(){
        if (OGResults.ssData) return Promise.resolve(OGResults.ssData);
        let sel = OGResults.selection, country = OGResults.workspace.country_id;
        let requestID = OGResults.requestID;
        $('#ogcRsExNote').html('<i class="fa fa-circle-o-notch fa-spin" aria-hidden="true"></i> Loading values…').show();
        return Promise.all([
            Ogc.getSSVars(country, sel.casename, sel.base),
            sel.reform ? Ogc.getSSVars(country, sel.casename, sel.reform) : Promise.resolve(null)
        ]).then(([baseline, reform]) => {
            if (requestID == OGResults.requestID) OGResults.ssData = {baseline, reform};
            return OGResults.ssData;
        });
    }

    static loadPath(name){
        let sel = OGResults.selection, country = OGResults.workspace.country_id;
        let key = name;
        if (OGResults.tpiCache[key]) return OGResults.tpiCache[key];
        let vars = name == 'Y' ? ['Y'] : [name, 'Y'];
        OGResults.tpiCache[key] = Promise.all([
            Ogc.getTPIVars(country, sel.casename, sel.base, vars),
            sel.reform ? Ogc.getTPIVars(country, sel.casename, sel.reform, vars) : Promise.resolve(null)
        ]).catch(error => { delete OGResults.tpiCache[key]; throw error; });
        return OGResults.tpiCache[key];
    }

    static renderVarList(){
        let catalog = OGResults.report.catalog;
        let filter = String($('#ogcRsVarSearch').val() || '').toLowerCase();
        let groups = {};
        $.each(catalog, (name, entry) => {
            if (filter && (entry.label + ' ' + name).toLowerCase().indexOf(filter) < 0) return;
            (groups[entry.category] = groups[entry.category] || []).push([name, entry]);
        });
        let dimsText = {scalar: '', age_group: 'by age & income', group: 'by income group', age: 'by age', vector: 'indexed', matrix: 'indexed'};
        let html = CATEGORY_ORDER.concat(Object.keys(groups).filter(c => CATEGORY_ORDER.indexOf(c) < 0)).map(category => {
            let items = groups[category];
            if (!items) return '';
            items.sort((a, b) => a[1].label.localeCompare(b[1].label));
            return `<div class="ogc-rs-varcat">${esc(category)}</div>` + items.map(([name, entry]) =>
                `<button type="button" role="option" class="ogc-rs-var${name == OGResults.ex.name ? ' ogc-rs-var-on' : ''}" data-rs-act="var" data-name="${esc(name)}" aria-selected="${name == OGResults.ex.name}">
                    <span>${esc(entry.label)}</span><small>${esc(dimsText[entry.dims] || '')}</small></button>`).join('');
        }).join('');
        $('#ogcRsVarList').html(html || '<div class="ogc-rs-tree-empty">No variable matches.</div>');
    }

    static renderToolbar(){
        let ex = OGResults.ex;
        let shape = D.exploreShape(OGResults.report, ex.name);
        let compare = OGResults.report.mode == 'compare';
        let seg = (act, current, options, label) => `<div class="ogc-rs-tool"><span>${label}</span><div class="ogc-seg" role="group" aria-label="${label}">${options.map(([key, text, disabled]) =>
            `<button type="button" class="btn ogc-btn" data-rs-act="${act}" data-value="${key}" aria-pressed="${current == key}"${disabled ? ` disabled title="${esc(disabled)}"` : ''}>${text}</button>`).join('')}</div></div>`;
        let tools = '';
        let pathReason = OGResults.report.analysis != 'transition'
            ? 'This selection was solved for the long run only'
            : (shape.pathable ? '' : 'Year-by-year values are shown for economy-wide variables');
        tools += seg('ex-period', ex.period, [['long', 'Long run'], ['path', 'Over time', pathReason]], 'Period');
        if (compare && shape.kind != 'diagnostic') tools += seg('ex-show', ex.show, [['change', 'Change'], ['levels', 'Baseline & reform']], 'Show');
        if (shape.household && ex.period == 'long'){
            tools += seg('ex-breakdown', ex.breakdown, [['avg', 'By age'], ['groups', 'By income group'], ['grid', 'Age × income']], 'Breakdown');
            if (compare && ex.show == 'levels' && ex.breakdown == 'grid') tools += seg('ex-scenario', ex.scenario, [['baseline', 'Baseline'], ['reform', 'Reform']], 'Scenario');
        }
        tools += seg('ex-view', ex.view, [['chart', '<i class="fa fa-bar-chart" aria-hidden="true"></i> Chart'], ['table', '<i class="fa fa-table" aria-hidden="true"></i> Table']], 'View');
        $('#ogcRsToolbar').html(tools);
    }

    static renderExplore(){
        let ex = OGResults.ex;
        if (!ex || !OGResults.ssData) return;
        let shape = D.exploreShape(OGResults.report, ex.name);
        if (ex.period == 'path' && !shape.pathable) ex.period = 'long';
        OGResults.renderToolbar();
        $('#ogcRsExNote').hide();
        let requestID = OGResults.requestID;
        let done = result => {
            if (requestID != OGResults.requestID || OGResults.ex !== ex) return;
            $('#ogcRsExTitle').text(result.title);
            $('#ogcRsExPeriod').text(result.period);
            if (result.note) $('#ogcRsExNote').html(result.note).show();
            let tableMode = ex.view == 'table' || !result.chart;
            $('#ogcRsExChart').toggle(!tableMode);
            $('#ogcRsExTable').toggle(tableMode);
            $('#ogcRsExTools').html(`${tableMode ? '<button type="button" class="btn ogc-btn ogc-btn-sm ogc-btn-soft" data-rs-act="ex-csv"><i class="fa fa-download" aria-hidden="true"></i> CSV</button>' : OGResults.exportMenu('ogcRsExChart')}`);
            if (tableMode){
                OGResults.disposeChart('ogcRsExChart');
                OGResults.setGrid('ogcRsExTable', {data: result.table.data, columns: result.table.columns, layout: 'fitDataStretch', maxHeight: '520px'});
            }else{
                OGResults.setChart('ogcRsExChart', result.chart);
            }
        };
        if (ex.period == 'path'){
            OGResults.loadPath(ex.name).then(([base, reform]) => done(D.explorePath(OGResults.report, OGResults.ssData, ex, base, reform)))
                .catch(error => { if (requestID == OGResults.requestID) $('#ogcRsExNote').text('Year-by-year values could not be loaded. ' + String(error)).show(); });
        }else{
            done(D.exploreLong(OGResults.report, OGResults.ssData, ex));
        }
    }

    static renderTablePicker(){
        let first = null;
        let html = D.OG_TABLES.map(spec => {
            let reason = D.tableAvailable(OGResults.report, spec);
            if (!reason && !first) first = spec.key;
            let label = spec.baselineOnly && OGResults.report.mode == 'compare' ? `${spec.label} (baseline)` : spec.label;
            return `<button type="button" class="btn ogc-btn" data-rs-act="og-table" data-key="${spec.key}" aria-pressed="false"${reason ? ` disabled title="${esc(reason)}"` : ''}>${esc(label)}</button>`;
        }).join('');
        $('#ogcRsTablePicker').html(html);
        if (first) OGResults.loadOgTable(first);
    }

    static loadOgTable(key){
        let spec = D.OG_TABLES.find(item => item.key == key);
        if (!spec) return;
        OGResults.activeOgTable = key;
        $('[data-rs-act="og-table"]').each(function () { $(this).attr('aria-pressed', $(this).attr('data-key') == key ? 'true' : 'false'); });
        $('[data-rs-act="table-csv"]').prop('disabled', true);
        let render = rows => {
            if (OGResults.activeOgTable != key) return;
            if (key == 'macro_ss' && $.isArray(rows) && rows.length && 'Variable' in rows[0] && 'Baseline' in rows[0]) rows = D.macroLongRunRows(rows);
            if (!$.isArray(rows) || !rows.length){
                OGResults.destroyGrid('ogcRsOgTable');
                $('#ogcRsTableNote').text('OG-Core returned no rows for this table.').show();
                return;
            }
            $('#ogcRsTableNote').hide();
            let fields = Object.keys(rows[0]);
            let data = rows.map(row => Object.fromEntries(fields.map((f, i) => ['c' + i, D.plainTableText(row[f])])));
            let columns = fields.map((f, i) => {
                let numeric = data.every(row => row['c' + i] === null || typeof row['c' + i] == 'number');
                return {title: String(D.plainTableText(f)), field: 'c' + i, frozen: i === 0, hozAlign: numeric ? 'right' : 'left',
                    headerHozAlign: numeric ? 'right' : 'left', formatter: numeric ? (c => V.formatNumber(c.getValue())) : 'plaintext'};
            });
            OGResults.setGrid('ogcRsOgTable', {data, columns, layout: 'fitDataStretch', maxHeight: '560px'});
            $('[data-rs-act="table-csv"]').prop('disabled', false);
        };
        if (OGResults.ogTables[key]){
            render(OGResults.ogTables[key]);
            return;
        }
        $('#ogcRsTableNote').html('<i class="fa fa-circle-o-notch fa-spin" aria-hidden="true"></i> OG-Core is building this table…').show();
        OGResults.destroyGrid('ogcRsOgTable');
        let sel = OGResults.selection;
        let requestID = OGResults.requestID;
        let tables = OGResults.ogTables;
        Ogc.getResultTable(spec.path, OGResults.workspace.country_id, sel.casename, sel.base, spec.baselineOnly ? null : sel.reform, spec.options)
            .then(rows => {
                tables[key] = rows;  // valid for the selection it was asked for, even if the user moved on
                if (requestID == OGResults.requestID) render(rows);
            })
            .catch(error => {
                if (requestID == OGResults.requestID && OGResults.activeOgTable == key) $('#ogcRsTableNote').text('This table could not be built. ' + String(error)).show();
            });
    }

    // ── chart, grid and export plumbing ──────────────────────────────────────
    static setChart(id, option){
        let el = document.getElementById(id);
        if (!el || !window.echarts) return;
        OGResults.charts = OGResults.charts || {};
        let chart = OGResults.charts[id];
        if (!chart || chart.isDisposed() || chart.getDom() !== el){
            if (chart && !chart.isDisposed()) chart.dispose();
            chart = window.echarts.init(el, null, {renderer: 'svg'});
            OGResults.charts[id] = chart;
        }
        chart.setOption(option, true);
    }

    static disposeChart(id){
        let chart = OGResults.charts && OGResults.charts[id];
        if (chart && !chart.isDisposed()) chart.dispose();
        if (OGResults.charts) delete OGResults.charts[id];
    }

    static disposeCharts(){
        $.each(OGResults.charts || {}, (id, chart) => { if (chart && !chart.isDisposed()) chart.dispose(); });
        OGResults.charts = {};
        $.each(OGResults.grids || {}, id => OGResults.destroyGrid(id));
        OGResults.grids = {};
    }

    static resizeCharts(){
        $.each(OGResults.charts || {}, (id, chart) => { if (chart && !chart.isDisposed() && $(chart.getDom()).is(':visible')) chart.resize(); });
    }

    static bindResize(){
        $(window).off('resize.ogresults').on('resize.ogresults', () => {
            clearTimeout(OGResults.resizeTimer);
            OGResults.resizeTimer = setTimeout(() => OGResults.resizeCharts(), 120);
        });
    }

    static setGrid(id, config){
        OGResults.destroyGrid(id);
        let el = document.getElementById(id);
        if (!el || !window.Tabulator) return;
        OGResults.grids = OGResults.grids || {};
        OGResults.grids[id] = new window.Tabulator(el, Object.assign({
            columnDefaults: {headerSortTristate: true, resizable: true},
            placeholder: 'No data'
        }, config));
    }

    static destroyGrid(id){
        let grid = OGResults.grids && OGResults.grids[id];
        if (grid){
            try { grid.destroy(); } catch (e) { /* already detached */ }
            delete OGResults.grids[id];
        }
    }

    static fileStem(){
        let label = OGResults.selectionLabel(OGResults.selection);
        return ('ogcore ' + OGResults.workspace.country_id + ' ' + label.title).replace(/→/g, 'vs').replace(/[^\w.-]+/g, '-').replace(/-+/g, '-').toLowerCase();
    }

    static downloadGrid(id, suffix){
        let grid = OGResults.grids && OGResults.grids[id];
        if (grid) grid.download('csv', `${OGResults.fileStem()}-${suffix}.csv`, {bom: true});
    }

    static exportChart(id, format){
        let chart = OGResults.charts && OGResults.charts[id];
        if (!chart || chart.isDisposed()) return;
        let card = $(chart.getDom()).closest('.ogc-rs-card, .ogc-rs-mini');
        let title = card.find('h3').first().text() || 'Chart';
        let period = card.find('.ogc-rs-card-period').first().text();
        let width = chart.getWidth(), height = chart.getHeight();
        let raw = chart.renderToSVGString ? chart.renderToSVGString() : decodeURIComponent(chart.getDataURL({type: 'svg'}).split(',')[1]);
        let doc = new DOMParser().parseFromString(raw, 'image/svg+xml').documentElement;
        let pad = 58;
        let ns = doc.namespaceURI;
        let group = document.createElementNS(ns, 'g');
        while (doc.firstChild) group.appendChild(doc.firstChild);
        group.setAttribute('transform', `translate(0 ${pad})`);
        let bg = document.createElementNS(ns, 'rect');
        bg.setAttribute('width', width); bg.setAttribute('height', height + pad); bg.setAttribute('fill', '#fff');
        doc.appendChild(bg);
        doc.appendChild(group);
        [[title, 22, 16, '700', '#3a3f51'], [[period, OGResults.selectionLabel(OGResults.selection).title].filter(Boolean).join(' · '), 42, 12, '400', '#6b7188']]
            .forEach(([text, y, size, weight, fill]) => {
                let node = document.createElementNS(ns, 'text');
                node.setAttribute('x', '16'); node.setAttribute('y', y);
                node.setAttribute('font-family', 'Arial, sans-serif'); node.setAttribute('font-size', size);
                node.setAttribute('font-weight', weight); node.setAttribute('fill', fill);
                node.textContent = text;
                doc.appendChild(node);
            });
        doc.setAttribute('width', width); doc.setAttribute('height', height + pad);
        doc.setAttribute('viewBox', `0 0 ${width} ${height + pad}`);
        let svg = new XMLSerializer().serializeToString(doc);
        let name = `${OGResults.fileStem()}-${title.replace(/[^\w]+/g, '-').toLowerCase()}`;
        let save = (href, ext) => {
            let link = document.createElement('a');
            link.download = `${name}.${ext}`;
            link.href = href;
            document.body.appendChild(link);
            link.click();
            link.remove();
        };
        let svgUrl = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
        if (format == 'svg'){
            save(svgUrl, 'svg');
            return;
        }
        let img = new Image();
        img.onload = () => {
            let canvas = document.createElement('canvas');
            canvas.width = width * 2; canvas.height = (height + pad) * 2;
            let ctx = canvas.getContext('2d');
            ctx.scale(2, 2);
            ctx.drawImage(img, 0, 0);
            save(canvas.toDataURL('image/png'), 'png');
        };
        img.src = svgUrl;
    }

    static closeMenus(){
        $('#ogcResultsPage .ogc-action-menu.ogc-menu-open').removeClass('ogc-menu-open')
            .find('[data-rs-act="menu"]').attr('aria-expanded', 'false').end()
            .find('.ogc-case-menu').attr('aria-hidden', 'true');
    }

    static editReform(){
        let sel = OGResults.selection;
        let c = OGResults.findCase(sel.casename);
        let run = OGResults.findRun(c, sel.reform);
        if (!run) return;
        saveSelection({
            casename: sel.casename, run_name: run.run_name, run_type: 'reform', baseline_run: run.baseline_run,
            country_id: OGResults.workspace.country_id, display_name: OGResults.displayName(c, run),
            baseline_display_name: OGCases.baselineDisplayName(c, run.baseline_run)
        });
        window.location.hash = '#/OGParameters';
    }

    // The OG-Core tables already built for a selection, most recently used last.
    static tablesFor(selection){
        let key = V.selectionKey(OGResults.workspace.country_id, selection);
        let tables = OGResults.tableCache.get(key) || Object.create(null);
        OGResults.tableCache.delete(key);
        OGResults.tableCache.set(key, tables);
        while (OGResults.tableCache.size > TABLE_CACHE_MAX) OGResults.tableCache.delete(OGResults.tableCache.keys().next().value);
        return tables;
    }

    static teardown(){
        OGResults.disposeCharts();
        $(window).off('.ogresults');
        $(document).off('.ogresults');
    }

    static initEvents(){
        // Leaving the page unbinds everything bound here, even when it never
        // got past the loading or empty state.
        $(window).on('hashchange.ogresults', () => { if (routePath() != '/OGResults') OGResults.teardown(); });
        $(document).on('click.ogresults', event => {
            if (!$(event.target).closest('#ogcResultsPage .ogc-action-menu').length) OGResults.closeMenus();
        }).on('keydown.ogresults', event => { if (event.key == 'Escape') OGResults.closeMenus(); });
        $('#ogcResultsPage').off('.ogresults')
        .on('input.ogresults', '#ogcRsSearch', () => OGResults.renderTree())
        .on('input.ogresults', '#ogcRsVarSearch', () => OGResults.renderVarList())
        .on('change.ogresults', '#ogcRsHhVar', function () { OGResults.hh.name = $(this).val(); OGResults.drawHouseholds(); })
        .on('change.ogresults', '#ogcRsHhGroup', function () { OGResults.hh.group = Number($(this).val()); OGResults.drawHouseholds(); })
        .on('click.ogresults', '[data-rs-tab]', function () { OGResults.openTab($(this).attr('data-rs-tab')); })
        .on('click.ogresults', '[data-rs-act]', function (event) {
            let el = $(this);
            let act = el.attr('data-rs-act');
            if (el.prop('disabled')) return;
            if (act == 'view'){
                // a reform viewed on its own is addressed as the single run
                OGResults.select({casename: el.attr('data-case'), base: el.attr('data-view') || el.attr('data-base'), reform: null,
                    tab: OGResults.selection && OGResults.selection.tab});
            }
            else if (act == 'compare') OGResults.select({casename: el.attr('data-case'), base: el.attr('data-base'), reform: el.attr('data-reform'), tab: OGResults.selection && OGResults.selection.tab});
            else if (act == 'recent') OGResults.select({casename: el.attr('data-case'), base: el.attr('data-base'), reform: el.attr('data-reform') || null});
            else if (act == 'jump'){
                let target = document.getElementById(el.attr('data-target'));
                if (target) target.scrollIntoView({behavior: 'smooth', block: 'start'});
            }
            else if (act == 'edit-reform') OGResults.editReform();
            else if (act == 'hh-view'){ OGResults.hh.view = el.attr('data-view'); OGResults.drawHouseholds(); }
            else if (act == 'hh-scenario'){ OGResults.hh.scenario = el.attr('data-scenario'); OGResults.drawHouseholds(); }
            else if (act == 'var'){
                OGResults.ex.name = el.attr('data-name');
                $('.ogc-rs-var').removeClass('ogc-rs-var-on').attr('aria-selected', 'false');
                el.addClass('ogc-rs-var-on').attr('aria-selected', 'true');
                OGResults.renderExplore();
            }
            else if (act.indexOf('ex-') === 0 && act != 'ex-csv'){
                let field = {'ex-period': 'period', 'ex-show': 'show', 'ex-breakdown': 'breakdown', 'ex-scenario': 'scenario', 'ex-view': 'view'}[act];
                if (field){ OGResults.ex[field] = el.attr('data-value'); OGResults.renderExplore(); }
            }
            else if (act == 'ex-csv') OGResults.downloadGrid('ogcRsExTable', OGResults.ex.name);
            else if (act == 'main-csv') OGResults.downloadGrid('ogcRsMainTable', 'main-results');
            else if (act == 'og-table') OGResults.loadOgTable(el.attr('data-key'));
            else if (act == 'table-csv') OGResults.downloadGrid('ogcRsOgTable', OGResults.activeOgTable || 'table');
            else if (act == 'menu'){
                event.stopPropagation();
                let menu = el.closest('.ogc-action-menu');
                let open = !menu.hasClass('ogc-menu-open');
                OGResults.closeMenus();
                if (open){
                    menu.addClass('ogc-menu-open');
                    el.attr('aria-expanded', 'true');
                    menu.find('.ogc-case-menu').attr('aria-hidden', 'false');
                }
            }
            else if (act == 'export'){
                OGResults.closeMenus();
                OGResults.exportChart(el.attr('data-chart'), el.attr('data-format'));
            }
        });
    }
}
