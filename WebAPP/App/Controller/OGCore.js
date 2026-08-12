import { Message } from "../../Classes/Message.Class.js";
import { Ogc } from "../../Classes/Ogc.Class.js";
import { OGWorkspace } from "../../Classes/OGWorkspace.Class.js";
import { Model } from "../Model/OGCore.Model.js";

//register country ids (repo name suffix) -> vendored flag files (ISO2, see
//References/flags/README.md); unmapped countries get an icon fallback
const FLAG_ISO2 = { ETH: 'et', ZAF: 'za', IDN: 'id', PHL: 'ph', USA: 'us', UK: 'gb', THA: 'th', BRA: 'br' };

//register values render into markup, escape them
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g,
    ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));

const BADGES = {
    'installed': ['ogc-b-ok', 'installed'],
    'update_available': ['ogc-b-upd', 'update available'],
    'not_installed': ['ogc-b-mut', 'not installed'],
    'installing': ['ogc-b-run', 'installing...'],
    'checking': ['ogc-b-run', 'checking...'],
    'failed': ['ogc-b-err', 'failed']
};

const POLL_MS = 3500;
// running jobs by country_id: { installId, timer }
let POLLS = {};
//response ids are a same-page fallback; the backend registry is authoritative
//across reloads and clients
let JOB_IDS = {};
//remove job ids persisted by older versions; source payloads below remain useful
try { localStorage.removeItem('osy-ogc-jobs'); } catch (e) {}
//add-dialog payloads by country, kept until the install succeeds; a failed
//custom install's minimal registry record does not retain its original source
const PENDING_KEY = 'osy-ogc-pending-adds';
function loadPendingAdds(){
    try { return JSON.parse(localStorage.getItem(PENDING_KEY)) || {}; }
    catch (e) { return {}; }
}
function loadPendingAdd(countryId){
    return loadPendingAdds()[countryId] || null;
}
function savePendingAdd(countryId, payload){
    let pending = loadPendingAdds();
    if (payload){ pending[countryId] = payload; } else { delete pending[countryId]; }
    localStorage.setItem(PENDING_KEY, JSON.stringify(pending));
}
// which country's live log the dialog is showing, or null
let LOG_COUNTRY = null;
// incremented for every OG page visit and route change; async work from an
// older visit must not repaint or restart polling on the new page
let PAGE_ID = 0;

//last known job state by country, used to keep the live dialog current
let JOB_STATE = {};
export default class OGCore {
    static onLoad(){
        OGCore.stopAllPolls();
        OGCore.checkedThisVisit = false;
        PAGE_ID++;
        OGCore.pageID = PAGE_ID;
        OGCore.refresh(true, PAGE_ID);
    }

    //a missing or older id is treated as stale, so callers must pass the id they
    //captured; guards fail closed rather than letting stale work through
    static isCurrent(pageID){
        return pageID == PAGE_ID;
    }

    static invalidatePage(){
        PAGE_ID++;
        OGCore.pageID = PAGE_ID;
        OGCore.stopAllPolls();
        LOG_COUNTRY = null;
        //the next visit rebuilds live state from the backend registry
        JOB_STATE = {};
    }

    // Reload catalogue + registry and re-render the grid.
    static refresh(initEvents, pageID){
        Promise.all([Ogc.getCalibrationCatalog(), Ogc.getInstalledCalibrations()])
        .then(data => {
            if (!OGCore.isCurrent(pageID)){
                return;
            }
            let [catalog, installed] = data;
            let model = new Model(catalog.countries, catalog.catalog_source, installed.calibrations);
            OGCore.model = model;
            OGCore.renderGrid(model, pageID);
            OGCore.autoCheckUpdates(model, pageID);
            if (initEvents){
                OGCore.initEvents();
            }
        })
        .catch(error => {
            if (!OGCore.isCurrent(pageID)){
                return;
            }
            Message.danger(error);
            let model = new Model([], 'none', []);
            OGCore.model = model;
            OGCore.renderGrid(model, pageID);
            if (initEvents){
                OGCore.initEvents();
            }
        });
    }

    static renderGrid(model, pageID){
        if (!OGCore.isCurrent(pageID)){
            return;
        }
        $('#ogcGrid').empty();
        //saved adds missing from the current backend lists still need a retry card
        let pendingAdds = {};
        $.each(loadPendingAdds(), function (countryId, p) {
            if (!OGCore.findCalibration(countryId)){
                pendingAdds[countryId] = p;
            }
        });
        if (model.calibrations.length == 0 && $.isEmptyObject(pendingAdds)){
            if (model.catalogSource == 'none'){
                $('#ogcEmptyTitle').text('The calibration catalogue is not reachable');
                $('#ogcEmptyText').text('Check the connection and reload the page, or add a calibration from a local folder or a Git URL.');
            }
            $('#ogcEmptyState').show();
        }else{
            $('#ogcEmptyState').hide();
        }
        if (model.catalogSource == 'cache'){
            $('#ogcSourceNote').show();
        }else{
            $('#ogcSourceNote').hide();
        }
        $.each(model.calibrations, function (id, c) {
            $('#ogcGrid').append(OGCore.cardHtml(c, model.records[c.country_id]));
            if (c.install_state == 'installing' || c.install_state == 'checking'){
                //the registry carries the id, so any client can resume the live job
                let installId = OGCore.jobIdFor(c.country_id);
                if (installId){
                    OGCore.pollJob(c.country_id, installId, pageID);
                }else{
                    OGCore.watchCountry(c.country_id, pageID);
                }
            }
        });
        $.each(pendingAdds, function (countryId, p) {
            //failed until a live job says otherwise
            $('#ogcGrid').append(OGCore.cardHtml({
                country_id: countryId, country_name: p.country_name, install_state: 'failed'
            }));
        });
        // the add card is part of the grid, after the countries
        $('#ogcGrid').append(`
            <div class="ogc-card ogc-addcard" data-act="add" title="Add a calibration from a local folder or a Git URL">
                <i class="fa fa-plus-circle"></i>
                <b>Add calibration</b>
                <span>local folder or Git URL</span>
            </div>`);
    }

    static cardHtml(c, record){
        let badge = BADGES[c.install_state] || ['ogc-b-mut', c.install_state];
        let active = c.install_state == 'installed' || c.install_state == 'update_available';
        let iso2 = FLAG_ISO2[c.country_id];
        let flag = iso2
            ? `<img class="ogc-flag" src="References/flags/4x3/${iso2}.svg" alt="">`
            : `<span class="ogc-flag ogc-flag-none"><i class="fa fa-flag-o"></i></span>`;
        return `
            <div class="ogc-card ${active ? 'ogc-on' : ''}" data-country="${esc(c.country_id)}" ${c.catalog_key ? `data-key="${esc(c.catalog_key)}"` : ''}>
                <div class="ogc-card-head">
                    ${flag}
                    <div class="ogc-card-title">
                        <div class="ogc-card-name">${esc(c.country_name)}</div>
                        <div class="ogc-card-id">${esc(c.country_id)}</div>
                    </div>
                    <span class="ogc-badge ${badge[0]}">${esc(badge[1])}</span>
                </div>
                <div class="ogc-card-actions" data-state="${esc(c.install_state)}">
                    ${active ? `<button class="btn ogc-btn ogc-btn-main" data-act="open-workspace" data-country="${esc(c.country_id)}"><i class="fa fa-folder-open-o"></i> Open workspace</button>` : ''}
                    ${OGCore.actionsHtml(c, record)}
                </div>
            </div>`;
    }

    //register calibrations (catalog_key, no record) and repo_url customs are
    //updatable by MUIOGO; a local_path record is not, the user owns that folder
    static actionsHtml(c, record){
        let state = c.install_state;
        if (state == 'not_installed'){
            return `<button class="btn ogc-btn ogc-btn-line" data-act="install"><i class="fa fa-download"></i> Install</button>`;
        }
        if (state == 'installing' || state == 'checking'){
            return `<button class="btn ogc-btn ogc-btn-line ogc-btn-busy" data-act="log" title="Show the install log">
                        <i class="fa fa-circle-o-notch fa-spin"></i> <span class="ogc-busylabel">Installing...</span>
                    </button>`;
        }
        if (state == 'installed'){
            return `${record && record.last_error
                        ? '<button class="btn ogc-btn ogc-btn-danger" data-act="log"><i class="fa fa-exclamation-triangle"></i> View update error</button>'
                        : ''}
                    <button class="btn ogc-btn ogc-btn-ico" data-act="check" title="Check for updates"><i class="fa fa-refresh"></i></button>
                    <button class="btn ogc-btn ogc-btn-ico" data-act="remove" title="Remove from MUIOGO"><i class="fa fa-times"></i></button>`;
        }
        if (state == 'update_available'){
            if (record && record.source_type == 'local_path'){
                return `<div class="ogc-updatenote" title="This calibration comes from a local folder. Update the folder yourself, then check again.">Update the local folder to get this version</div>
                        <button class="btn ogc-btn ogc-btn-line" data-act="check"><i class="fa fa-refresh"></i> Check again</button>
                        <button class="btn ogc-btn ogc-btn-ico" data-act="remove" title="Remove from MUIOGO"><i class="fa fa-times"></i></button>`;
            }
            return `<button class="btn ogc-btn ogc-btn-main" data-act="update"><i class="fa fa-arrow-circle-up"></i> Update</button>
                    <button class="btn ogc-btn ogc-btn-ico" data-act="remove" title="Remove from MUIOGO"><i class="fa fa-times"></i></button>`;
        }
        if (state == 'failed'){
            return `<button class="btn ogc-btn ogc-btn-line" data-act="log"><i class="fa fa-file-text-o"></i> View error</button>
                    <button class="btn ogc-btn ogc-btn-danger" data-act="retry"><i class="fa fa-refresh"></i> Retry</button>
                    <button class="btn ogc-btn ogc-btn-ico" data-act="remove" title="Remove from MUIOGO"><i class="fa fa-times"></i></button>`;
        }
        return '';
    }

    //jobs

    static startJob(countryId, promise){
        let pageID = PAGE_ID;
        //instant feedback, even a seconds long install stays visible
        OGCore.setCardBusy(countryId, 'Starting...');
        OGCore.openLog(countryId, true);
        promise
        .then(response => {
            if (OGCore.isCurrent(pageID)){
                OGCore.pollJob(countryId, response.install_id, pageID);
            }
        })
        .catch(error => {
            if (!OGCore.isCurrent(pageID)){
                return;
            }
            OGCore.closeModal();
            Message.danger(error);
            OGCore.refresh(false, pageID);
        });
    }

    //repaint one card in place while waiting for the next registry refresh
    static setCardState(countryId, state){
        let card = $(`#ogcGrid .ogc-card[data-country="${countryId}"]`);
        let badge = BADGES[state] || ['ogc-b-mut', state];
        card.find('.ogc-badge').attr('class', 'ogc-badge ' + badge[0]).text(badge[1]);
        let record = (OGCore.model && OGCore.model.records[countryId]) || null;
        //pass the real calibration with the new state applied; a one-field stub
        //would hide source_type from the card actions
        let c = (OGCore.model && OGCore.findCalibration(countryId)) || { country_id: countryId };
        card.find('.ogc-card-actions').html(OGCore.actionsHtml($.extend({}, c, { install_state: state }), record));
    }

    static setCardBusy(countryId, label){
        OGCore.setCardState(countryId, 'installing');
        let card = $(`#ogcGrid .ogc-card[data-country="${countryId}"]`);
        card.find('.ogc-busylabel').text(label || 'Installing...');
    }

    static pollJob(countryId, installId, pageID){
        if (!OGCore.isCurrent(pageID)){
            return;
        }
        OGCore.stopPoll(countryId);
        let tick = function () {
            if (!OGCore.isCurrent(pageID)){
                OGCore.stopPoll(countryId);
                return;
            }
            Ogc.getInstallStatus(installId)
            .then(job => {
                if (OGCore.isCurrent(pageID)){
                    OGCore.applyJob(countryId, job, pageID);
                }
            })
            .catch(error => {
                //transient poll errors keep the timer, the job continues server side
            });
        };
        POLLS[countryId] = { installId: installId, timer: setInterval(tick, POLL_MS) };
        JOB_IDS[countryId] = installId;
        //first status right away
        tick();
    }

    static applyJob(countryId, job, pageID){
        if (!OGCore.isCurrent(pageID)){
            return;
        }
        JOB_STATE[countryId] = job;
        let card = $(`#ogcGrid .ogc-card[data-country="${countryId}"]`);
        if (LOG_COUNTRY == countryId){
            OGCore.renderLog(job.log_tail || [], job.error);
        }
        if (job.install_state == 'installed'){
            OGCore.stopPoll(countryId);
            delete JOB_IDS[countryId];
            savePendingAdd(countryId, null);
            delete JOB_STATE[countryId];
            Message.smallBoxInfo('OG-Core', esc(job.country_name) + ' is installed.', 4000);
            if (LOG_COUNTRY == countryId){
                OGCore.closeModal();
            }
            OGCore.refresh(false, pageID);
            return;
        }
        if (job.install_state == 'failed'){
            OGCore.stopPoll(countryId);
            let record = (OGCore.model && OGCore.model.records[countryId]) || null;
            let workingInstall = record && record.venv_path;
            if (LOG_COUNTRY == countryId){
                // the open dialog becomes the error view in place
                $('#ogcModalHead').attr('class', 'ogc-box-head ogc-head-err')
                    .html(`<i class="fa fa-exclamation-triangle"></i> ${esc(job.country_name)} (${esc(countryId)}): ${workingInstall ? 'update' : 'install'} failed`);
                let retryAct = workingInstall ? 'retry-update-modal' : 'retry-modal';
                if (!$('#ogcModalFoot [data-act="' + retryAct + '"]').length){
                    $('#ogcModalFoot').append(`<button class="btn ogc-btn ogc-btn-danger" data-act="${retryAct}"><i class="fa fa-refresh"></i> Retry ${workingInstall ? 'update' : 'install'}</button>`);
                }
            }
            if (workingInstall){
                //a failed update does not invalidate the existing environment
                record.last_error = job.error || 'Update failed.';
                OGCore.setCardState(countryId, 'installed');
                OGCore.refresh(false, pageID);
                return;
            }
            OGCore.setCardState(countryId, 'failed');
            return;
        }
        card.find('.ogc-busylabel').text(job.progress_label || 'Installing...');
    }

    //background update check, one upstream query per installed country, once
    //per page visit; failures stay silent so offline is fine
    static autoCheckUpdates(model, pageID){
        if (OGCore.checkedThisVisit || !OGCore.isCurrent(pageID)){
            return;
        }
        OGCore.checkedThisVisit = true;
        $.each(model.calibrations, function (id, c) {
            if (c.install_state == 'installed'){
                Ogc.refreshCalibration({ country_id: c.country_id, check_only: true })
                .then(result => {
                    if (OGCore.isCurrent(pageID) && result.install_state == 'update_available'){
                        OGCore.setCardState(c.country_id, 'update_available');
                    }
                })
                .catch(e => {});
            }
        });
    }

    //fallback for an older backend or a best-effort registry write failure
    static watchCountry(countryId, pageID){
        if (!OGCore.isCurrent(pageID) || POLLS[countryId]){
            return;
        }
        let timer = setInterval(function () {
            if (!OGCore.isCurrent(pageID)){
                OGCore.stopPoll(countryId);
                return;
            }
            Ogc.getCalibrationCatalog()
            .then(catalog => {
                if (!OGCore.isCurrent(pageID)){
                    return;
                }
                let entry = null;
                $.each(catalog.countries || [], function (id, c) {
                    if (c.country_id == countryId) entry = c;
                });
                if (entry && entry.install_state != 'installing' && entry.install_state != 'checking'){
                    OGCore.stopPoll(countryId);
                    OGCore.refresh(false, pageID);
                }
            })
            .catch(error => {});
        }, POLL_MS * 3);
        POLLS[countryId] = { installId: null, timer: timer };
    }

    static stopPoll(countryId){
        if (POLLS[countryId]){
            clearInterval(POLLS[countryId].timer);
            delete POLLS[countryId];
        }
    }

    static stopAllPolls(){
        $.each(POLLS, function (countryId, p) { clearInterval(p.timer); });
        POLLS = {};
    }

    //modal

    static openModal(head, body, foot, headClass){
        $('#ogcModalHead').attr('class', 'ogc-box-head ' + (headClass || '')).html(head);
        $('#ogcModalBody').html(body);
        $('#ogcModalFoot').html(foot);
        $('#ogcModal').show();
    }

    static closeModal(){
        LOG_COUNTRY = null;
        $('#ogcModal').hide();
    }

    //log dialog

    static openLog(countryId, starting){
        let c = OGCore.findCalibration(countryId);
        let record = (OGCore.model && OGCore.model.records[countryId]) || null;
        let lastJob = JOB_STATE[countryId];
        let failed = !starting && lastJob
            ? lastJob.install_state == 'failed'
            : !starting && ((c && c.install_state == 'failed') || (record && record.last_error));
        let updateFailed = failed && record && record.venv_path;
        LOG_COUNTRY = countryId;
        let countryName = (lastJob && lastJob.country_name) || (c && c.country_name) || countryId;
        let head = failed
            ? `<i class="fa fa-exclamation-triangle"></i> ${esc(countryName)} (${esc(countryId)}): ${updateFailed ? 'update' : 'install'} failed`
            : `<i class="fa fa-circle-o-notch fa-spin"></i> Installing ${esc(countryName)}`;
        let retryAct = updateFailed ? 'retry-update-modal' : 'retry-modal';
        let foot = `<button class="btn ogc-btn ogc-btn-line" data-act="copylog"><i class="fa fa-clipboard"></i> Copy log</button>
                    <button class="btn ogc-btn ogc-btn-line" data-act="close">Close</button>
                    ${failed ? `<button class="btn ogc-btn ogc-btn-danger" data-act="${retryAct}"><i class="fa fa-refresh"></i> Retry ${updateFailed ? 'update' : 'install'}</button>` : ''}`;
        OGCore.openModal(head, `<div class="ogc-logsum" id="ogcLogSum"></div><div class="ogc-log" id="ogcLog"></div>`, foot, failed ? 'ogc-head-err' : '');
        $('#ogcModal').attr('data-country', countryId);
        if (starting){
            //a fresh job was just requested, never show a previous job's log
            OGCore.renderLog(['Starting install...'], null);
            return;
        }
        //what the job has logged so far, live updates come from the poll
        let installId = OGCore.jobIdFor(countryId);
        if (installId){
            let pageID = PAGE_ID;
            Ogc.getInstallStatus(installId)
            .then(job => {
                if (OGCore.isCurrent(pageID) && LOG_COUNTRY == countryId){
                    JOB_STATE[countryId] = job;
                    OGCore.renderLog(job.log_tail || [], job.error);
                }
            })
            .catch(e => {
                if (OGCore.isCurrent(pageID) && LOG_COUNTRY == countryId){
                    OGCore.renderLog([], null);
                }
            });
        }else{
            //the job ran before this page session, its log id is gone
            OGCore.renderLog([], 'The install log is only kept for the running session. Retry to see fresh output.');
        }
    }

    static renderLog(lines, error){
        $('#ogcLogSum').text(error || '');
        let pane = $('#ogcLog');
        if (!pane.length){
            return;
        }
        let atBottom = pane.length && (pane[0].scrollHeight - pane.scrollTop() - pane.outerHeight() < 24);
        let html = '';
        $.each(lines, function (id, line) {
            let cls = 'ogc-l';
            if (/error|failed/i.test(line)) cls += ' ogc-l-err';
            else if (/warning/i.test(line)) cls += ' ogc-l-warn';
            else if (/^\s*\+ /.test(line)) cls += ' ogc-l-dim';
            else if (/^\s*Imported /.test(line)) cls += ' ogc-l-ok';
            html += `<div class="${cls}">${esc(line)}</div>`;
        });
        if (!lines.length){
            html = '<div class="ogc-l ogc-l-dim">No log output yet.</div>';
        }
        pane.html(html);
        if (atBottom){
            pane.scrollTop(pane[0].scrollHeight);
        }
        OGCore.lastLogText = lines.join('\n');
    }

    //add calibration

    static openAdd(){
        //state for the check-bind: the exact checked values plus a generation
        //counter, so edits and superseded checks invalidate the result
        OGCore.checkedValues = null;
        OGCore.checkGen = 0;
        let head = `<i class="fa fa-plus-circle"></i> Add a calibration`;
        let body = `
            <div class="ogc-formrow">
                <label>Source</label>
                <input type="text" id="ogcAddSource" placeholder="/path/to/OG-XYZ   or   https://github.com/.../OG-XYZ">
            </div>
            <div class="ogc-formrow">
                <label>Label</label>
                <input type="text" id="ogcAddLabel" placeholder="e.g. Kenya">
            </div>
            <div class="ogc-formrow">
                <label>Code</label>
                <input type="text" id="ogcAddCode" placeholder="short id, e.g. KEN" maxlength="32">
            </div>
            <div id="ogcAddCheck"></div>`;
        let foot = `<button class="btn ogc-btn ogc-btn-line" data-act="close">Cancel</button>
                    <button class="btn ogc-btn ogc-btn-main" data-act="add-check"><i class="fa fa-search"></i> Check</button>
                    <button class="btn ogc-btn ogc-btn-main" data-act="add-confirm" disabled><i class="fa fa-plus"></i> Add calibration</button>`;
        OGCore.openModal(head, body, foot, '');
    }

    static suggestFromSource(){
        let src = $.trim($('#ogcAddSource').val());
        let m = src.match(/OG[-_]([A-Za-z0-9_-]{2,10})\/?$/i);
        if (m && !$.trim($('#ogcAddCode').val())){
            $('#ogcAddCode').val(m[1].toUpperCase());
            OGCore.addEdited();
        }
    }

    static addPayload(){
        let src = $.trim($('#ogcAddSource').val());
        let isUrl = /^(https?:\/\/|git@|ssh:\/\/)/i.test(src);
        return {
            source_type: isUrl ? 'repo_url' : 'local_path',
            country_id: $.trim($('#ogcAddCode').val()),
            country_name: $.trim($('#ogcAddLabel').val()),
            [isUrl ? 'repo_url' : 'local_path']: src
        };
    }

    //the check result is valid only for the exact values it ran against
    static addFormValues(){
        return {
            source: $.trim($('#ogcAddSource').val()),
            label: $.trim($('#ogcAddLabel').val()),
            code: $.trim($('#ogcAddCode').val())
        };
    }

    //any edit invalidates a passed check until the form matches it again
    static addEdited(){
        OGCore.checkGen++;
        let v = OGCore.addFormValues();
        let c = OGCore.checkedValues;
        let stillValid = c && c.valid && v.source == c.source && v.label == c.label && v.code == c.code;
        $('[data-act="add-confirm"]').prop('disabled', !stillValid);
    }

    static addCheck(){
        let payload = OGCore.addPayload();
        if (!payload.country_id || !payload.country_name || !(payload.repo_url || payload.local_path)){
            $('#ogcAddCheck').html('<div class="ogc-checknote ogc-checknote-warn">Fill source, label and code first.</div>');
            return;
        }
        let gen = ++OGCore.checkGen;
        let submitted = OGCore.addFormValues();
        $('#ogcAddCheck').html('<div class="ogc-checknote"><i class="fa fa-circle-o-notch fa-spin"></i> Checking...</div>');
        $('[data-act="add-confirm"]').prop('disabled', true);
        Ogc.checkCalibration(payload)
        .then(result => {
            //an edit or a newer check superseded this response
            if (gen != OGCore.checkGen){
                return;
            }
            let notes = '';
            $.each(result.warnings || [], function (id, w) {
                notes += `<div class="ogc-checknote ogc-checknote-warn"><i class="fa fa-exclamation-triangle"></i> ${esc(w)}</div>`;
            });
            if (result.check_state == 'valid'){
                let d = result.detected || {};
                notes += `<div class="ogc-checknote ogc-checknote-ok"><i class="fa fa-check"></i> Looks valid${d.package_name ? ', package ' + esc(d.package_name) : ''}.</div>`;
                OGCore.checkedValues = { source: submitted.source, label: submitted.label, code: submitted.code, valid: true };
                $('[data-act="add-confirm"]').prop('disabled', false);
            }else{
                notes += `<div class="ogc-checknote ogc-checknote-warn"><i class="fa fa-times"></i> This source does not look like an OG calibration.</div>`;
                OGCore.checkedValues = null;
                $('[data-act="add-confirm"]').prop('disabled', true);
            }
            $('#ogcAddCheck').html(notes);
        })
        .catch(error => {
            if (gen != OGCore.checkGen){
                return;
            }
            OGCore.checkedValues = null;
            $('#ogcAddCheck').html(`<div class="ogc-checknote ogc-checknote-warn"><i class="fa fa-times"></i> ${esc(error)}</div>`);
            $('[data-act="add-confirm"]').prop('disabled', true);
        });
    }

    static addConfirm(){
        let v = OGCore.addFormValues();
        let c = OGCore.checkedValues;
        //never install values that were not the checked ones
        if (!c || !c.valid || v.source != c.source || v.label != c.label || v.code != c.code){
            $('[data-act="add-confirm"]').prop('disabled', true);
            return;
        }
        let payload = OGCore.addPayload();
        savePendingAdd(payload.country_id, payload);
        OGCore.closeModal();
        OGCore.startFromPayload(payload);
    }

    static startFromPayload(payload){
        let promise = payload.source_type == 'local_path'
            ? Ogc.registerLocalCalibration(payload)
            : Ogc.installCalibration(payload);
        OGCore.startJob(payload.country_id, promise);
    }

    //card actions

    static findCalibration(countryId){
        let found = null;
        $.each(OGCore.model.calibrations, function (id, c) {
            if (c.country_id == countryId) found = c;
        });
        return found;
    }

    static jobIdFor(countryId){
        let poll = POLLS[countryId];
        let record = (OGCore.model && OGCore.model.records[countryId]) || null;
        let calibration = OGCore.model && OGCore.findCalibration(countryId);
        return (poll && poll.installId)
            || (record && record.install_id)
            || (calibration && calibration.install_id)
            || JOB_IDS[countryId]
            || null;
    }

    static install(countryId){
        let c = OGCore.findCalibration(countryId);
        if (c && c.catalog_key){
            OGCore.startJob(countryId, Ogc.installCalibration({
                source_type: 'catalog', catalog_key: c.catalog_key, country_id: countryId
            }));
            return;
        }
        //custom calibration: an unfinished add is the latest source, otherwise
        //retry from a complete registry record
        let pending = loadPendingAdd(countryId);
        if (pending){
            OGCore.startFromPayload(pending);
            return;
        }
        let record = OGCore.model.records[countryId];
        if (record && record.source_type == 'local_path'){
            OGCore.startJob(countryId, Ogc.registerLocalCalibration({
                country_id: countryId, country_name: record.country_name, local_path: record.local_path
            }));
        }else if (record && record.repo_url){
            OGCore.startJob(countryId, Ogc.installCalibration({
                source_type: 'repo_url', country_id: countryId,
                country_name: record.country_name, repo_url: record.repo_url
            }));
        }else{
            Message.warning('No source is known for this calibration, add it again.');
        }
    }

    static checkUpdates(countryId, button){
        let pageID = PAGE_ID;
        button.find('.fa').addClass('fa-spin');
        Ogc.refreshCalibration({ country_id: countryId, check_only: true })
        .then(result => {
            if (result.install_state == 'update_available'){
                Message.smallBoxInfo('OG-Core', 'A newer version of ' + esc(countryId) + ' is available.', 4000);
            }else{
                Message.smallBoxInfo('OG-Core', esc(countryId) + ' is up to date.', 3000);
            }
            if (OGCore.isCurrent(pageID)){
                OGCore.refresh(false, pageID);
            }
        })
        .catch(error => {
            if (!OGCore.isCurrent(pageID)){
                return;
            }
            button.find('.fa').removeClass('fa-spin');
            Message.danger(error);
        });
    }

    static update(countryId){
        OGCore.startJob(countryId, Ogc.refreshCalibration({ country_id: countryId, check_only: false }));
    }

    static openRemove(countryId){
        let c = OGCore.findCalibration(countryId);
        let head = `<i class="fa fa-exclamation-triangle"></i> Remove ${esc(c ? c.country_name : countryId)}?`;
        let body = `<p>This removes the calibration from MUIOGO. Its files stay on disk and it can be registered again later.</p>`;
        let foot = `<button class="btn ogc-btn ogc-btn-line" data-act="close">Cancel</button>
                    <button class="btn ogc-btn ogc-btn-danger" data-act="remove-confirm">Remove</button>`;
        OGCore.openModal(head, body, foot, 'ogc-head-err');
        $('#ogcModal').attr('data-country', countryId);
    }

    static removeConfirm(countryId){
        let pageID = PAGE_ID;
        OGCore.closeModal();
        //fallback for a pending add missing from the backend registry
        if (!OGCore.model.records[countryId]){
            savePendingAdd(countryId, null);
            delete JOB_IDS[countryId];
            delete JOB_STATE[countryId];
            OGCore.refresh(false, pageID);
            return;
        }
        Ogc.unregisterCalibration(countryId)
        .then(response => {
            savePendingAdd(countryId, null);
            delete JOB_IDS[countryId];
            delete JOB_STATE[countryId];
            Message.smallBoxInfo('OG-Core', 'Calibration removed.', 3000);
            if (OGCore.isCurrent(pageID)){
                OGCore.refresh(false, pageID);
            }
        })
        .catch(error => {
            if (!OGCore.isCurrent(pageID)){
                return;
            }
            Message.danger(error);
        });
    }

    //events

    static initEvents(){
        //polls must not outlive the page
        $(window).off('hashchange.ogcPolls').on('hashchange.ogcPolls', function () {
            OGWorkspace.cancelPreparation();
            OGCore.invalidatePage();
        });

        $('#ogcGrid').off('click.ogc').on('click.ogc', '[data-act]', function (e) {
            e.preventDefault();
            e.stopPropagation();
            let act = $(this).attr('data-act');
            if (act == 'add'){
                OGCore.openAdd();
                return;
            }
            if (act == 'open-workspace'){
                let countryId = $(this).attr('data-country');
                let country = OGCore.findCalibration(countryId);
                if (country){
                    let pageID = PAGE_ID;
                    OGWorkspace.prepare(country, () => OGCore.isCurrent(pageID)).then(ready => {
                        if (ready) window.location.hash = '#/OGCases';
                    });
                }
                return;
            }
            let countryId = $(this).closest('.ogc-card').attr('data-country');
            if (act == 'install' || act == 'retry') OGCore.install(countryId);
            if (act == 'log') OGCore.openLog(countryId);
            if (act == 'check') OGCore.checkUpdates(countryId, $(this));
            if (act == 'update') OGCore.update(countryId);
            if (act == 'remove') OGCore.openRemove(countryId);
        });

        $('#ogcModal').off('click.ogc').on('click.ogc', '[data-act]', function (e) {
            e.preventDefault();
            let act = $(this).attr('data-act');
            let countryId = $('#ogcModal').attr('data-country');
            if (act == 'close') OGCore.closeModal();
            if (act == 'copylog' && navigator.clipboard){
                navigator.clipboard.writeText(OGCore.lastLogText || '');
                Message.smallBoxInfo('OG-Core', 'Log copied.', 2000);
            }
            if (act == 'retry-modal'){
                OGCore.closeModal();
                OGCore.install(countryId);
            }
            if (act == 'retry-update-modal'){
                OGCore.closeModal();
                OGCore.update(countryId);
            }
            if (act == 'remove-confirm') OGCore.removeConfirm(countryId);
            if (act == 'add-check') OGCore.addCheck();
            if (act == 'add-confirm') OGCore.addConfirm();
        });

        //the dimmed backdrop closes the dialog
        $('#ogcModal').off('click.ogcback').on('click.ogcback', function (e) {
            if (e.target === this) OGCore.closeModal();
        });

        $('#ogcModal').off('blur.ogc').on('blur.ogc', '#ogcAddSource', function () {
            OGCore.suggestFromSource();
        });

        //edits after a passed check invalidate it (B2)
        $('#ogcModal').off('input.ogc').on('input.ogc', '#ogcAddSource, #ogcAddLabel, #ogcAddCode', function () {
            OGCore.addEdited();
        });
    }
}
