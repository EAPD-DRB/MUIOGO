import { Message } from "../../Classes/Message.Class.js";
import { Ogc } from "../../Classes/Ogc.Class.js";
import { OGWorkspace } from "../../Classes/OGWorkspace.Class.js";
import { escapeHtml as esc } from "../../Classes/Html.Class.js";
import { Model } from "../Model/OGCases.Model.js";

const FLAG_ISO2 = { ETH: 'et', ZAF: 'za', IDN: 'id', PHL: 'ph', USA: 'us', UK: 'gb', THA: 'th', BRA: 'br' };

//async work from an older page visit must not repaint the new page
let PAGE_ID = 0;

//the case and run the parameters page opens, handed over through localStorage so
//a reload of the parameters page keeps its context
const SEL_KEY = 'osy-ogc-selection';
const RUN_SEL_KEY = 'osy-ogc-run-selection';
const LAYOUT_KEY = 'osy-ogc-cases-layout';

export function loadWorkspace(){
    return OGWorkspace.current();
}

export function runKey(countryId, casename, runName){
    return countryId + ':' + casename + ':' + runName;
}

export function saveSelection(sel){
    if (sel){
        localStorage.setItem(SEL_KEY, JSON.stringify(sel));
    }else{
        localStorage.removeItem(SEL_KEY);
    }
}

export function loadSelection(){
    try { return JSON.parse(localStorage.getItem(SEL_KEY)) || null; }
    catch (e) { return null; }
}

export default class OGCases {

    static onLoad(){
        OGCases.workspace = loadWorkspace();
        if (!OGCases.workspace || !OGCases.workspace.country_id){
            window.location.hash = '#/OGCore';
            return;
        }
        PAGE_ID++;
        OGCases.pageID = PAGE_ID;
        OGCases.layout = localStorage.getItem(LAYOUT_KEY) || 'grouped';
        OGCases.query = '';
        let prepared = OGWorkspace.takePrepared(OGCases.workspace.country_id);
        if (prepared){
            OGCases.model = new Model(
                prepared.cases, prepared.runsByCase, prepared.installed,
                OGCases.workspace.country_id
            );
            OGCases.render(OGCases.model, PAGE_ID);
            if (prepared.failedRuns && prepared.failedRuns.length){
                Message.warning('Runs could not be loaded for: ' + prepared.failedRuns.join(', ') + '.');
            }
            OGCases.initEvents();
            return;
        }
        OGCases.refresh(true, PAGE_ID);
    }

    static isCurrent(pageID){
        return pageID == PAGE_ID && localStorage.getItem('osy-pageId') == 'OGCases';
    }

    // Load the backend case containers and present their configurations as cases.
    static refresh(initEvents, pageID){
        Promise.all([
            Ogc.getCases(OGCases.workspace.country_id),
            Ogc.getInstalledCalibrations()
        ])
        .then(data => {
            if (!OGCases.isCurrent(pageID)){
                return;
            }
            let [cases, installed] = data;
            let list = $.isArray(cases) ? cases : (cases.cases || []);
            list = $.grep(list, function (c) {
                return c.country_id == OGCases.workspace.country_id;
            });
            //runs come per case, so fetch them together and key by case name
            return Promise.all($.map(list, function (c) {
                return Ogc.getRuns(OGCases.workspace.country_id, c.casename)
                    .then(r => ({ casename: c.casename, runs: r.runs || r || [] }))
                    .catch(error => ({ casename: c.casename, runs: [], error: error }));
            }))
            .then(runResults => {
                if (!OGCases.isCurrent(pageID)){
                    return;
                }
                let runsByCase = {};
                let failed = [];
                $.each(runResults, function (id, r) {
                    runsByCase[r.casename] = r.runs;
                    if (r.error) failed.push(r.casename);
                });
                OGCases.model = new Model(list, runsByCase, installed.calibrations, OGCases.workspace.country_id);
                OGCases.render(OGCases.model, pageID);
                if (failed.length){
                    Message.warning('Runs could not be loaded for: ' + failed.join(', ') + '.');
                }
                if (initEvents){
                    OGCases.initEvents();
                }
            });
        })
        .catch(error => {
            if (!OGCases.isCurrent(pageID)){
                return;
            }
            Message.danger(error);
            OGCases.model = new Model([], {}, [], OGCases.workspace.country_id);
            OGCases.render(OGCases.model, pageID);
            if (initEvents){
                OGCases.initEvents();
            }
        });
    }

    static render(model, pageID){
        if (!OGCases.isCurrent(pageID)){
            return;
        }
        $('#ogcCasesTitle').text(OGCases.workspace.country_name + ' workspace');
        $('#ogcCasesSub').text('An isolated workspace for ' + OGCases.workspace.country_name + '. Cases, runs, and results stay with this calibration.');
        $('#ogcWorkspaceName').text(OGCases.workspace.country_name);
        $('#ogcWorkspaceId').text(OGCases.workspace.country_id);
        let iso2 = FLAG_ISO2[OGCases.workspace.country_id];
        $('#ogcWorkspaceFlag').html(iso2
            ? `<img class="ogc-flag" src="References/flags/4x3/${iso2}.svg" alt="">`
            : '<span class="ogc-flag ogc-flag-none"><i class="fa fa-flag-o"></i></span>');
        let entries = OGCases.entries(model);
        let baselines = $.grep(entries, e => e.run && e.run.run_type == 'baseline');
        let reforms = $.grep(entries, e => e.run && e.run.run_type == 'reform');
        //The calibration reference is not a backend run and must not inflate the
        //number of user-created baselines.
        $('#ogcBaselineCount').text(baselines.length);
        $('#ogcReformCount').text(reforms.length);
        $('#ogcBaselineLabel').text(baselines.length == 1 ? 'baseline' : 'baselines');
        $('#ogcReformLabel').text(reforms.length == 1 ? 'reform' : 'reforms');
        OGCases.renderCases(entries);
        //a case needs an installed calibration to be created at all
        let installed = !!model.records[OGCases.workspace.country_id];
        $('[data-act="new-case"]').prop('disabled', !installed);
        if (!installed){
            $('#ogcCasesNote').show();
        }else{
            $('#ogcCasesNote').hide();
        }
    }

    static entries(model){
        let entries = [];
        $.each(model.cases, function (id, c) {
            if (!c.runs.length){
                entries.push({case: c, run: null});
                return;
            }
            $.each(c.runs, function (rid, run) { entries.push({case: c, run: run}); });
        });
        return entries;
    }

    static renderCases(entries){
        let q = (OGCases.query || '').toLowerCase();
        let visible = $.grep(entries, function (e) {
            let text = e.run
                ? e.run.run_name + ' ' + e.case.casename + ' ' + (e.run.baseline_run || '')
                : e.case.casename + ' incomplete setup';
            return !q || text.toLowerCase().indexOf(q) >= 0;
        });
        let baselines = $.grep(visible, e => e.run && e.run.run_type == 'baseline');
        let reforms = $.grep(visible, e => e.run && e.run.run_type == 'reform');
        let incomplete = $.grep(visible, e => !e.run);
        $('#ogcLayoutLabel').text(OGCases.layout == 'grouped' ? 'Split baselines and reforms' : 'Group by baseline');
        if (OGCases.layout == 'separate'){
            $('#ogcCasesContent').html(`<div class="ogc-case-split">
                ${OGCases.panel('cubes', 'Baselines', baselines, true)}
                ${OGCases.panel('flask', 'Reforms', reforms, false)}
                ${incomplete.length ? OGCases.panel('exclamation-circle', 'Incomplete cases', incomplete, false) : ''}
            </div>`);
            return;
        }
        let rows = OGCases.defaultRow();
        $.each(incomplete, function (id, entry) { rows += OGCases.entryRows(entry); });
        $.each(baselines, function (id, b) {
            rows += OGCases.entryRows(b);
            $.each(reforms, function (rid, r) {
                if (r.case.casename == b.case.casename && r.run.baseline_run == b.run.run_name){
                    rows += OGCases.entryRows(r, true);
                }
            });
        });
        $.each(reforms, function (id, r) {
            let parent = $.grep(baselines, b => b.case.casename == r.case.casename && b.run.run_name == r.run.baseline_run);
            if (!parent.length) rows += OGCases.entryRows(r, true);
        });
        $('#ogcCasesContent').html(OGCases.table(rows));
    }

    static panel(icon, title, entries, includeDefault){
        let rows = includeDefault ? OGCases.defaultRow() : '';
        $.each(entries, function (id, e) { rows += OGCases.entryRows(e); });
        if (!rows) rows = `<tr><td class="ogc-empty-cell" colspan="4">No ${esc(title.toLowerCase())} yet.</td></tr>`;
        return `<section class="ogc-case-panel"><h3><i class="fa fa-${icon}"></i> ${esc(title)} <span>(${entries.length})</span></h3>${OGCases.table(rows)}</section>`;
    }

    static table(rows){
        return `<table class="ogc-table ogc-case-table"><thead><tr><th>Name</th><th>Type</th><th>Created from</th><th></th></tr></thead><tbody>${rows}</tbody></table>`;
    }

    static defaultRow(){
        let installed = !!(OGCases.model && OGCases.model.records[OGCases.workspace.country_id]);
        return `<tr class="ogc-case-row ogc-reference-row" data-act="expand" data-key="default">
            <td><i class="fa fa-caret-right ogc-caret"></i> <b>Calibration defaults</b> <span class="ogc-tag ogc-tag-mut"><i class="fa fa-bookmark-o"></i> reference only</span></td>
            <td class="ogc-mut">&mdash;</td><td class="ogc-mut">&mdash;</td>
            <td class="ogc-actcell"><button class="btn ogc-btn ogc-btn-sm" data-act="new-case" title="Create a runnable baseline from these calibration values"${installed ? '' : ' disabled'}><i class="fa fa-plus"></i> Create baseline</button></td></tr>
            <tr class="ogc-detail-row" data-detail="default" style="display:none"><td colspan="4"><div class="ogc-case-detail">
                <div><label>Type</label>Calibration reference (not runnable)</div><div><label>Country</label>${esc(OGCases.workspace.country_name)}</div>
                <div><label>Calibration</label>${esc(OGCases.workspace.country_id)}</div><div><label>Purpose</label>Starting values for creating a user baseline</div>
            </div></td></tr>`;
    }

    static entryRows(entry, nested){
        let c = entry.case, run = entry.run;
        if (!run){
            return `<tr class="ogc-case-row">
                <td><b>${esc(c.casename)}</b></td>
                <td><span class="ogc-tag ogc-tag-need">incomplete</span></td>
                <td class="ogc-mut">Baseline setup did not finish</td>
                <td class="ogc-actcell">
                    <button class="btn ogc-btn ogc-btn-sm" data-act="retry-baseline" data-case="${esc(c.casename)}" title="Create the missing baseline run and continue editing its parameters"><i class="fa fa-refresh"></i> Retry setup</button>
                    <button class="btn ogc-btn ogc-btn-sm ogc-btn-danger" data-act="del-case" data-case="${esc(c.casename)}" title="Delete this incomplete case"><i class="fa fa-trash"></i> Delete case</button>
                </td></tr>`;
        }
        let key = runKey(c.country_id, c.casename, run.run_name);
        let from = run.run_type == 'reform' ? OGCases.baselineDisplayName(c, run.baseline_run) : 'Calibration defaults';
        let type = run.run_type == 'reform' ? 'reform' : 'baseline';
        let name = OGCases.displayName(c, run);
        let addReform = type == 'baseline'
            ? `<button class="btn ogc-btn ogc-btn-sm" data-act="new-run" data-case="${esc(c.casename)}" title="Create a policy change to compare with this baseline"><i class="fa fa-plus"></i> Add reform</button>`
            : '';
        let menuAddReform = type == 'baseline'
            ? `<button type="button" role="menuitem" data-act="new-run" data-case="${esc(c.casename)}"><i class="fa fa-plus"></i> Add reform</button>`
            : '';
        return `<tr class="ogc-case-row${nested ? ' ogc-nested' : ''}" data-act="expand" data-key="${esc(key)}">
            <td><i class="fa fa-caret-right ogc-caret"></i> <b>${esc(name)}</b></td>
            <td><span class="ogc-tag ogc-tag-${type == 'reform' ? 'reform' : 'base'}">${type}</span></td>
            <td class="ogc-mut">${esc(from)}</td>
            <td class="ogc-actcell"><button class="btn ogc-btn ogc-btn-sm" data-act="run" data-case="${esc(c.casename)}" data-run="${esc(run.run_name)}" title="Open the run queue with this configuration selected"><i class="fa fa-play"></i> Run</button>
            <button class="btn ogc-btn ogc-btn-sm" data-act="params" data-case="${esc(c.casename)}" data-run="${esc(run.run_name)}" title="Edit the parameters used by this run"><i class="fa fa-pencil"></i> Edit</button>
            <span class="ogc-action-menu"><button class="btn ogc-btn ogc-btn-ico" data-act="run-menu" data-case="${esc(c.casename)}" data-run="${esc(run.run_name)}" aria-label="Actions for ${esc(name)}" aria-haspopup="menu" aria-expanded="false"><i class="fa fa-ellipsis-v"></i></button>
            <span class="ogc-case-menu" role="menu" aria-hidden="true">${menuAddReform}
                <button type="button" role="menuitem" class="ogc-menu-danger" data-act="del-run" data-case="${esc(c.casename)}" data-run="${esc(run.run_name)}"><i class="fa fa-trash"></i> ${type == 'baseline' ? 'Delete case' : 'Delete reform'}</button>
            </span></span></td></tr>
            <tr class="ogc-detail-row" data-detail="${esc(key)}" style="display:none"><td colspan="4"><div class="ogc-case-detail">
                <div><label>Type</label>${type == 'reform' ? 'Reform' : 'User baseline'}</div><div><label>Created from</label>${esc(from)}</div>
                <div><label>Backend case</label>${esc(c.casename)}</div><div><label>Description</label>${esc(type == 'reform' ? (run.description || 'No description') : (c.description || 'No description'))}</div>
                ${addReform ? `<div class="ogc-detail-actions">${addReform}</div>` : ''}
            </div></td></tr>`;
    }

    static displayName(c, run){
        return run && run.run_type == 'baseline' && run.run_name == 'baseline'
            ? c.casename : (run ? run.run_name : '');
    }

    static baselineDisplayName(c, runName){
        let baseline = $.grep((c && c.runs) || [], r => r.run_type == 'baseline' && r.run_name == runName)[0];
        return baseline ? OGCases.displayName(c, baseline) : runName;
    }

    //dialog

    static openModal(head, body, foot, headClass){
        $('#ogcCasesModalHead').attr('class', 'ogc-box-head ' + (headClass || '')).html(head);
        $('#ogcCasesModalBody').html(body);
        $('#ogcCasesModalFoot').html(foot);
        $('#ogcCasesModal').removeAttr('data-case data-run data-type').show();
    }

    static closeModal(){
        $('#ogcCasesModal').hide();
    }

    static baselineChoices(){
        let choices = [];
        $.each((OGCases.model && OGCases.model.cases) || [], function (id, c) {
            $.each(Model.baselines(c.runs), function (rid, run) {
                choices.push({
                    casename: c.casename,
                    run_name: run.run_name,
                    label: OGCases.displayName(c, run)
                });
            });
        });
        return choices;
    }

    static nextBaselineName(){
        let next = OGCases.baselineChoices().length + 1;
        while (OGCases.findCase('Baseline ' + next)) next++;
        return 'Baseline ' + next;
    }

    static openNewCase(type, preferredCase){
        let choices = OGCases.baselineChoices();
        OGCases.newCaseBaselines = choices;
        let canReform = choices.length > 0;
        type = type == 'reform' && canReform ? 'reform' : 'baseline';
        let bopts = '';
        $.each(choices, function (id, choice) {
            let selected = preferredCase && choice.casename == preferredCase ? ' selected' : '';
            bopts += `<option value="${id}"${selected}>${esc(choice.label)}</option>`;
        });
        if (!canReform){
            bopts = '<option value="">Create a baseline first</option>';
        }
        let baselineName = OGCases.nextBaselineName();
        let body = `
            <div class="ogc-formrow">
                <label>Type</label>
                <div class="ogc-type-switch" role="group" aria-label="Case type">
                    <button type="button" data-act="case-type" data-type="baseline">Baseline</button>
                    <button type="button" data-act="case-type" data-type="reform"${canReform ? '' : ' disabled title="Create a baseline before adding a reform"'}>Reform</button>
                </div>
            </div>
            <div class="ogc-formrow">
                <label>Name</label>
                <input type="text" id="ogcCaseName" maxlength="64" autocomplete="off">
            </div>
            <div class="ogc-formrow" id="ogcCaseBaseWrap">
                <label>Based on</label>
                <select id="ogcCaseBaseline" class="ogc-select">${bopts}</select>
            </div>
            <div class="ogc-formrow">
                <label>Description <span class="ogc-optional">(optional)</span></label>
                <input type="text" id="ogcCaseDesc" maxlength="240">
            </div>
            <div class="ogc-form-note" id="ogcCaseNote"></div>
            <div id="ogcCaseErr"></div>`;
        let foot = `<button class="btn ogc-btn ogc-btn-line" data-act="close">Cancel</button>
                    <button class="btn ogc-btn ogc-btn-main" data-act="new-case-confirm">Create and edit</button>`;
        OGCases.openModal(`<i class="fa fa-pencil"></i> Add a case`, body, foot, '');
        $('#ogcCasesModal')
            .attr('data-baseline-name', baselineName)
            .attr('data-reform-name', 'New reform');
        OGCases.setNewCaseType(type);
    }

    static setNewCaseType(type){
        if (type == 'reform' && !OGCases.newCaseBaselines.length) return;
        let modal = $('#ogcCasesModal');
        let previous = modal.attr('data-type');
        if (previous){
            modal.attr('data-' + previous + '-name', $.trim($('#ogcCaseName').val()));
        }
        modal.attr('data-type', type);
        $('.ogc-type-switch [data-type]').each(function () {
            let active = $(this).attr('data-type') == type;
            $(this).toggleClass('active', active).attr('aria-pressed', active ? 'true' : 'false');
        });
        let reform = type == 'reform';
        $('#ogcCaseBaseWrap').toggle(reform);
        $('#ogcCaseName').val(modal.attr('data-' + type + '-name'));
        $('#ogcCaseDesc').attr('placeholder', reform ? 'What does this reform change?' : 'What is this baseline for?');
        $('#ogcCaseNote').html(reform
            ? `<i class="fa fa-info-circle"></i> The reform inherits this baseline's values and is compared against it.`
            : '<i class="fa fa-info-circle"></i> Starts from the calibration default.');
        $('#ogcCaseErr').empty();
        $('#ogcCaseName').focus().select();
    }

    static openNewRun(casename){
        OGCases.openNewCase('reform', casename);
    }

    static requireCreated(response, fallback){
        if (response && (response.status_code == 'error' || response.status_code == 'exist')){
            throw (response.message || fallback);
        }
        return response;
    }

    static newCaseConfirm(){
        let type = $('#ogcCasesModal').attr('data-type') || 'baseline';
        let name = $.trim($('#ogcCaseName').val());
        let description = $.trim($('#ogcCaseDesc').val());
        let countryId = OGCases.workspace.country_id;
        if (!name){
            $('#ogcCaseErr').html('<div class="ogc-checknote ogc-checknote-warn">Give the case a name.</div>');
            return;
        }

        let request, selection, createdContainer = false;
        if (type == 'baseline'){
            if (OGCases.findCase(name)){
                $('#ogcCaseErr').html('<div class="ogc-checknote ogc-checknote-warn">A baseline with this name already exists.</div>');
                return;
            }
            request = Ogc.saveCase({ casename: name, country_id: countryId, description: description })
                .then(response => {
                    OGCases.requireCreated(response, 'The baseline could not be created.');
                    createdContainer = true;
                })
                .then(() => Ogc.createRun({
                    country_id: countryId, casename: name, run_name: 'baseline',
                    run_type: 'baseline', description: description
                }));
            selection = {
                casename: name, run_name: 'baseline', run_type: 'baseline',
                baseline_run: null, country_id: countryId, display_name: name
            };
        }else{
            let choice = OGCases.newCaseBaselines[parseInt($('#ogcCaseBaseline').val(), 10)];
            if (!choice){
                $('#ogcCaseErr').html('<div class="ogc-checknote ogc-checknote-warn">Pick the baseline this reform is built on.</div>');
                return;
            }
            let parent = OGCases.findCase(choice.casename);
            let duplicate = false;
            $.each((parent && parent.runs) || [], function (id, run) {
                if (run.run_name == name) duplicate = true;
            });
            if (duplicate){
                $('#ogcCaseErr').html('<div class="ogc-checknote ogc-checknote-warn">A case with this name already exists under that baseline.</div>');
                return;
            }
            request = Ogc.createRun({
                country_id: countryId,
                casename: choice.casename,
                run_name: name,
                run_type: 'reform',
                baseline_run: choice.run_name,
                description: description
            });
            selection = {
                casename: choice.casename, run_name: name, run_type: 'reform',
                baseline_run: choice.run_name, country_id: countryId,
                display_name: name, baseline_display_name: choice.label
            };
        }

        let pageID = PAGE_ID;
        let confirm = $('#ogcCasesModal [data-act="new-case-confirm"]');
        confirm.prop('disabled', true).text('Creating...');
        request
        .then(response => OGCases.requireCreated(response, 'The case could not be created.'))
        .then(response => {
            OGCases.closeModal();
            Message.smallBoxInfo('OG-Core', type == 'reform' ? 'Reform created.' : 'Baseline created.', 3000);
            if (OGCases.isCurrent(pageID)){
                saveSelection(selection);
                window.location.hash = '#/OGParameters';
            }
        })
        .catch(async error => {
            let cleanupFailed = false;
            if (type == 'baseline' && createdContainer){
                try {
                    await Ogc.deleteCase(countryId, name);
                }catch (cleanupError){
                    cleanupFailed = true;
                }
                createdContainer = false;
            }
            confirm.prop('disabled', false).text('Create and edit');
            let recovery = cleanupFailed
                ? ' The incomplete case is shown in the list so setup can be retried or deleted.'
                : '';
            $('#ogcCaseErr').html(`<div class="ogc-checknote ogc-checknote-warn"><i class="fa fa-times"></i> ${esc(error + recovery)}</div>`);
            if (cleanupFailed && OGCases.isCurrent(pageID)) OGCases.refresh(false, pageID);
        });
    }

    static retryBaseline(casename){
        let c = OGCases.findCase(casename);
        if (!c) return;
        let pageID = PAGE_ID;
        Ogc.createRun({
            country_id: OGCases.workspace.country_id,
            casename: casename,
            run_name: 'baseline',
            run_type: 'baseline',
            description: c.description || ''
        })
        .then(response => OGCases.requireCreated(response, 'The baseline setup could not be completed.'))
        .then(() => {
            if (!OGCases.isCurrent(pageID)) return;
            saveSelection({
                casename: casename, run_name: 'baseline', run_type: 'baseline',
                baseline_run: null, country_id: OGCases.workspace.country_id,
                display_name: casename
            });
            window.location.hash = '#/OGParameters';
        })
        .catch(error => Message.danger(error));
    }

    static openDeleteCase(casename){
        let body = `<p>Delete the case <b>${esc(casename)}</b> and every run inside it, including any results? This cannot be undone.</p>`;
        let foot = `<button class="btn ogc-btn ogc-btn-line" data-act="close">Cancel</button>
                    <button class="btn ogc-btn ogc-btn-danger" data-act="del-case-confirm">Delete case</button>`;
        OGCases.openModal(`<i class="fa fa-exclamation-triangle"></i> Delete ${esc(casename)}?`, body, foot, 'ogc-head-err');
        $('#ogcCasesModal').attr('data-case', casename);
    }

    static openDeleteRun(casename, runName){
        let c = OGCases.findCase(casename);
        let run = c && $.grep(c.runs || [], item => item.run_name == runName)[0];
        let baseline = run && run.run_type == 'baseline';
        let reforms = c ? Model.reformsOf(c.runs, runName) : [];
        let warn = baseline && reforms.length
            ? `<p class="ogc-mut" style="margin-top:8px"><i class="fa fa-exclamation-triangle"></i> This also deletes ${reforms.length} reform${reforms.length == 1 ? '' : 's'} and all of their results.</p>`
            : '';
        let body = baseline
            ? `<p>Delete the case <b>${esc(casename)}</b>, every run inside it, and all results? This cannot be undone.</p>${warn}`
            : `<p>Delete the reform <b>${esc(runName)}</b> and its results? This cannot be undone.</p>`;
        let foot = `<button class="btn ogc-btn ogc-btn-line" data-act="close">Cancel</button>
                    <button class="btn ogc-btn ogc-btn-danger" data-act="del-run-confirm">${baseline ? 'Delete case' : 'Delete reform'}</button>`;
        OGCases.openModal(`<i class="fa fa-exclamation-triangle"></i> Delete ${esc(baseline ? casename : runName)}?`, body, foot, 'ogc-head-err');
        $('#ogcCasesModal').attr('data-case', casename).attr('data-run', runName);
    }

    static deleteCaseConfirm(casename){
        let pageID = PAGE_ID;
        OGCases.closeModal();
        let countryId = OGCases.workspace.country_id;
        Ogc.setSession(casename, countryId)
        .then(() => Ogc.deleteCase(countryId, casename))
        .then(response => {
            //a deleted case must not stay selected for the parameters page
            let sel = loadSelection();
            if (sel && sel.country_id == countryId && sel.casename == casename){
                saveSelection(null);
            }
            Message.smallBoxInfo('OG-Core', 'Case deleted.', 3000);
            if (OGCases.isCurrent(pageID)){
                OGCases.refresh(false, pageID);
            }
        })
        .catch(error => Message.danger(error));
    }

    static deleteRunConfirm(casename, runName){
        let pageID = PAGE_ID;
        OGCases.closeModal();
        let countryId = OGCases.workspace.country_id;
        Ogc.setSession(casename, countryId)
        .then(() => Ogc.deleteRun(countryId, casename, runName))
        .then(response => {
            let sel = loadSelection();
            if (sel && sel.country_id == countryId
                && sel.casename == casename && sel.run_name == runName){
                saveSelection(null);
            }
            Message.smallBoxInfo('OG-Core', 'Case deleted.', 3000);
            if (OGCases.isCurrent(pageID)){
                OGCases.refresh(false, pageID);
            }
        })
        .catch(error => Message.danger(error));
    }

    //open the parameters page on one run

    static openParams(casename, runName){
        let c = OGCases.findCase(casename);
        if (c && !c.installed){
            Message.warning('The calibration for this case is not installed, so its parameters cannot be read.');
            return;
        }
        let run = null;
        $.each((c && c.runs) || [], function (id, r) {
            if (r.run_name == runName) run = r;
        });
        saveSelection({
            casename: casename,
            run_name: runName,
            run_type: run ? run.run_type : 'baseline',
            baseline_run: run ? (run.baseline_run || null) : null,
            country_id: c ? c.country_id : null,
            display_name: run ? OGCases.displayName(c, run) : runName,
            baseline_display_name: run && run.run_type == 'reform'
                ? OGCases.baselineDisplayName(c, run.baseline_run)
                : null
        });
        window.location.hash = '#/OGParameters';
    }

    static openRun(casename, runName){
        let c = OGCases.findCase(casename);
        let run = $.grep((c && c.runs) || [], r => r.run_name == runName)[0];
        if (!run) return;
        let selection = {
            casename: casename,
            run_name: runName,
            run_type: run.run_type,
            baseline_run: run.baseline_run || null,
            country_id: c.country_id,
            display_name: OGCases.displayName(c, run),
            baseline_display_name: run.run_type == 'reform'
                ? OGCases.baselineDisplayName(c, run.baseline_run) : null
        };
        saveSelection(selection);
        localStorage.setItem(RUN_SEL_KEY, JSON.stringify(selection));
        window.location.hash = '#/OGRuns';
    }

    static findCase(casename){
        let found = null;
        $.each(OGCases.model.cases, function (id, c) {
            if (c.casename == casename) found = c;
        });
        return found;
    }

    static closeActionMenus(returnFocus){
        let open = $('.ogc-action-menu.ogc-menu-open');
        let trigger = open.find('[data-act="run-menu"]').first();
        open.removeClass('ogc-menu-open');
        open.find('[data-act="run-menu"]').attr('aria-expanded', 'false');
        open.find('.ogc-case-menu').attr('aria-hidden', 'true');
        if (returnFocus && trigger.length) trigger.focus();
    }

    static toggleActionMenu(button){
        let trigger = $(button);
        let menu = trigger.closest('.ogc-action-menu');
        let opening = !menu.hasClass('ogc-menu-open');
        OGCases.closeActionMenus(false);
        if (!opening) return;
        menu.addClass('ogc-menu-open');
        trigger.attr('aria-expanded', 'true');
        menu.find('.ogc-case-menu').attr('aria-hidden', 'false')
            .find('[role="menuitem"]').first().focus();
    }

    //events

    static initEvents(){
        $('#ogcCasesPage').off('click.ogcases').on('click.ogcases', '[data-act]', function (e) {
            e.preventDefault();
            e.stopPropagation();
            let act = $(this).attr('data-act');
            let casename = $(this).attr('data-case');
            let runName = $(this).attr('data-run');
            if (act == 'run-menu'){
                OGCases.toggleActionMenu(this);
                return;
            }
            OGCases.closeActionMenus(false);
            if (act == 'new-case') OGCases.openNewCase();
            if (act == 'new-run') OGCases.openNewRun(casename);
            if (act == 'retry-baseline') OGCases.retryBaseline(casename);
            if (act == 'run') OGCases.openRun(casename, runName);
            if (act == 'params') OGCases.openParams(casename, runName);
            if (act == 'del-case') OGCases.openDeleteCase(casename);
            if (act == 'del-run') OGCases.openDeleteRun(casename, runName);
            if (act == 'layout'){
                OGCases.layout = OGCases.layout == 'grouped' ? 'separate' : 'grouped';
                localStorage.setItem(LAYOUT_KEY, OGCases.layout);
                OGCases.renderCases(OGCases.entries(OGCases.model));
            }
            if (act == 'expand'){
                let key = $(this).attr('data-key');
                let detail = $('.ogc-detail-row').filter(function () { return $(this).attr('data-detail') == key; });
                detail.toggle();
                $(this).toggleClass('ogc-expanded', detail.is(':visible'));
            }
        });

        $('#ogcCasesPage').off('input.ogcases').on('input.ogcases', '#ogcCaseSearch', function () {
            OGCases.query = $(this).val();
            OGCases.renderCases(OGCases.entries(OGCases.model));
        });

        $('#ogcCasesModal').off('click.ogcases').on('click.ogcases', '[data-act]', function (e) {
            e.preventDefault();
            let act = $(this).attr('data-act');
            let casename = $('#ogcCasesModal').attr('data-case');
            let runName = $('#ogcCasesModal').attr('data-run');
            if (act == 'close') OGCases.closeModal();
            if (act == 'case-type') OGCases.setNewCaseType($(this).attr('data-type'));
            if (act == 'new-case-confirm') OGCases.newCaseConfirm();
            if (act == 'del-case-confirm') OGCases.deleteCaseConfirm(casename);
            if (act == 'del-run-confirm') OGCases.deleteRunConfirm(casename, runName);
        });

        //the dimmed backdrop closes the dialog
        $('#ogcCasesModal').off('click.ogcasesback').on('click.ogcasesback', function (e) {
            if (e.target === this) OGCases.closeModal();
        });

        $(document).off('click.ogcasesmenu').on('click.ogcasesmenu', function (e) {
            if (!$(e.target).closest('.ogc-action-menu').length){
                OGCases.closeActionMenus(false);
            }
        });
        $(document).off('keydown.ogcasesmenu').on('keydown.ogcasesmenu', function (e) {
            if (e.key == 'Escape') OGCases.closeActionMenus(true);
        });
    }
}
