import { Message } from "../../Classes/Message.Class.js";
import { Ogc } from "../../Classes/Ogc.Class.js";
import { Model } from "../Model/OGCases.Model.js";
import { clearRunStale, isRunStale, loadSelection, loadWorkspace } from "./OGCases.js";

const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g,
    ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const STATUS = {
    completed: ['ogc-tag-done', 'Completed'],
    running: ['ogc-tag-run', 'Running'],
    queued: ['ogc-tag-mut', 'Queued'],
    pending: ['ogc-tag-mut', 'Not run'],
    failed: ['ogc-tag-need', 'Failed'],
    cancelled: ['ogc-tag-mut', 'Cancelled'],
    stale: ['ogc-tag-need', 'Needs run'],
    reused: ['ogc-tag-done', 'Reused'],
    planned: ['ogc-tag-mut', 'Planned'],
    waiting: ['ogc-tag-mut', 'Waiting for baseline'],
    blocked: ['ogc-tag-need', 'Blocked']
};
const ACTIVE_STATES = ['queued', 'running'];
const RUN_SELECTION_KEY = 'osy-ogc-run-selection';
let PAGE_ID = 0;
let EXECUTION_ID = 0;

export default class OGRuns {
    static onLoad(sourcePage){
        Message.clearMessages();
        OGRuns.workspace = loadWorkspace();
        if (!OGRuns.workspace || !OGRuns.workspace.country_id){
            window.location.hash = '#/OGCore';
            return;
        }
        let pageToken = ++PAGE_ID;
        OGRuns.pageToken = pageToken;
        OGRuns.monitorID = (OGRuns.monitorID || 0) + 1;
        OGRuns.selected = {};
        OGRuns.plan = [];
        OGRuns.entries = [];
        OGRuns.running = false;
        OGRuns.execution = null;
        OGRuns.stopExecutionID = null;
        OGRuns.load(pageToken, sourcePage, false);
        OGRuns.initEvents();
    }

    static isCurrent(pageToken){
        return pageToken == PAGE_ID && localStorage.getItem('osy-pageId') == 'OGRuns';
    }

    static async load(pageToken, sourcePage, preserveSelection){
        try {
            let cases = await Ogc.getCases();
            let list = $.isArray(cases) ? cases : (cases.cases || []);
            list = $.grep(list, c => c.country_id == OGRuns.workspace.country_id);
            let items = await Promise.all($.map(list, c => Ogc.getRuns(c.casename)
                .then(r => ({case: c, runs: r.runs || r || []}))
                .catch(error => ({case: c, runs: [], error: error}))));
            if (!OGRuns.isCurrent(pageToken)) return;

            let oldEntries = {};
            $.each(OGRuns.entries || [], (id, entry) => { oldEntries[entry.key] = entry; });
            OGRuns.items = items;
            OGRuns.entries = OGRuns.flatten(items);
            let byKey = OGRuns.entriesByKey();
            $.each(OGRuns.plan || [], function (id, job) {
                if (byKey[job.entry.key]) job.entry = byKey[job.entry.key];
            });

            await OGRuns.hydrateBackendState(pageToken);
            if (!OGRuns.isCurrent(pageToken)) return;
            if (!preserveSelection) OGRuns.applyInitialSelection(sourcePage);
            OGRuns.render();
            OGRuns.startMonitor(pageToken);
        } catch (error) {
            if (OGRuns.isCurrent(pageToken)){
                Message.danger(error);
                OGRuns.render();
            }
        }
    }

    static flatten(items){
        let entries = [];
        $.each(items || [], function (id, item) {
            let runs = new Model([], {}, [], null).flattenRuns(item.runs);
            $.each(runs, function (rid, run) {
                let key = item.case.casename + ':' + run.run_name;
                let hasReusable = run.reusable !== undefined;
                let backendStale = hasReusable
                    ? (run.status == 'completed' && !run.reusable)
                    : (run.stale === undefined ? isRunStale(key) : !!run.stale);
                let entry = {
                    case: item.case,
                    run: run,
                    key: key,
                    stale: backendStale,
                    reusable: hasReusable ? !!run.reusable : undefined,
                    name: run.run_type == 'baseline' && run.run_name == 'baseline'
                        ? item.case.casename : run.run_name
                };
                OGRuns.applyBackendStatus(entry, run);
                entries.push(entry);
            });
        });
        return entries;
    }

    static entriesByKey(){
        let byKey = {};
        $.each(OGRuns.entries || [], (id, entry) => { byKey[entry.key] = entry; });
        return byKey;
    }

    static queueRecords(response){
        if (!response) return [];
        if ($.isArray(response)) return response;
        if (response.active !== undefined || response.queued !== undefined){
            let records = response.active ? [response.active] : [];
            return records.concat($.isArray(response.queued) ? response.queued : []);
        }
        let records = response.queue || response.jobs || response.runs || response.items || [];
        return $.isArray(records) ? records : [];
    }

    static queueRecordKey(record){
        let casename = record.casename || record.case_name || (record.case && record.case.casename);
        let runName = record.run_name || record.RunName || record.name;
        return casename && runName ? casename + ':' + runName : null;
    }

    static normaliseState(source, stale){
        source = source || {};
        let raw = String(source.run_state || source.state || source.status || 'pending').toLowerCase();
        let stage = String(source.run_stage || source.stage || '').toLowerCase();
        let error = String(source.error || '').toLowerCase();
        let queuePosition = source.queue_position;
        if (raw == 'cancelled' || error.indexOf('cancel') >= 0) return 'cancelled';
        if (raw == 'failed' || raw == 'error') return 'failed';
        if (raw == 'running' && stage.indexOf('queue') < 0) return 'running';
        if (raw == 'queued' || stage.indexOf('queue') >= 0
            || (queuePosition !== undefined && queuePosition !== null && raw == 'pending')) return 'queued';
        if ((raw == 'stale' || stale) && raw != 'running' && raw != 'queued') return 'stale';
        if (raw == 'completed' || raw == 'complete' || raw == 'success') return 'completed';
        return 'pending';
    }

    static applyBackendStatus(entry, status){
        status = status || {};
        let owns = key => Object.prototype.hasOwnProperty.call(status, key);
        if (status.reusable !== undefined){
            entry.reusable = !!status.reusable;
            if (String(status.run_state || status.status || '').toLowerCase() == 'completed'){
                entry.stale = !entry.reusable;
            }
        }
        if (status.stale !== undefined) entry.stale = !!status.stale;
        entry.state = OGRuns.normaliseState(status, entry.stale);
        if (owns('run_stage') || owns('stage')){
            entry.stage = status.run_stage || status.stage || '';
        }else{
            entry.stage = entry.stage || '';
        }
        if (owns('run_iteration') || owns('iteration')){
            entry.iteration = status.run_iteration || status.iteration || null;
        }else{
            entry.iteration = entry.iteration || null;
        }
        entry.queuePosition = status.queue_position !== undefined
            ? status.queue_position : entry.queuePosition;
        if (owns('completed_at') || owns('finished_at') || owns('updated_at')){
            entry.completedAt = status.completed_at || status.finished_at || status.updated_at || '';
        }else{
            entry.completedAt = entry.completedAt || entry.run.completed_at || '';
        }
        if (owns('error')){
            entry.error = status.error || '';
        }else{
            entry.error = entry.error || entry.run.error || '';
        }
        if (owns('run_log')) entry.log = $.isArray(status.run_log) ? status.run_log : [];
        if (status.run_state) entry.run.status = status.run_state;
        return entry;
    }

    static async hydrateBackendState(pageToken){
        let queue = [];
        if (typeof Ogc.getRunQueue == 'function'){
            let caseNames = [];
            $.each(OGRuns.entries || [], function (id, entry) {
                if (caseNames.indexOf(entry.case.casename) < 0) caseNames.push(entry.case.casename);
            });
            let snapshots = await Promise.all($.map(caseNames, async function (casename) {
                try { return OGRuns.queueRecords(await Ogc.getRunQueue(casename)); }
                catch (error) { return []; }
            }));
            $.each(snapshots, function (id, records) { queue = queue.concat(records); });
        }
        if (!OGRuns.isCurrent(pageToken)) return;
        let byKey = OGRuns.entriesByKey();
        $.each(queue, function (id, record) {
            let entry = byKey[OGRuns.queueRecordKey(record)];
            if (entry) OGRuns.applyBackendStatus(entry, record);
        });

        //Older backends have no queue-list endpoint. Pending runs are probed so
        //getRunStatus can distinguish a genuinely queued run from one never run.
        let candidates = $.grep(OGRuns.entries, entry =>
            entry.state == 'pending' || ACTIVE_STATES.indexOf(entry.state) >= 0);
        await Promise.all($.map(candidates, async function (entry) {
            try {
                let status = await Ogc.getRunStatus(entry.case.casename, entry.run.run_name);
                if (OGRuns.isCurrent(pageToken)) OGRuns.applyBackendStatus(entry, status);
            } catch (error) {
                //The run list still provides a usable state if a single status read fails.
            }
        }));
    }

    static applyInitialSelection(sourcePage){
        $.each(OGRuns.entries, (id, entry) => { OGRuns.selected[entry.key] = false; });
        let selection = null;
        try {
            selection = JSON.parse(localStorage.getItem(RUN_SELECTION_KEY));
        } catch (error) { selection = null; }
        localStorage.removeItem(RUN_SELECTION_KEY);
        if (!selection && sourcePage == 'OGParameters') selection = loadSelection();
        if (!selection || (selection.country_id && selection.country_id != OGRuns.workspace.country_id)) return;
        let key = selection.casename + ':' + selection.run_name;
        if (OGRuns.selected[key] !== undefined) OGRuns.selected[key] = true;
    }

    static baselineName(entry){
        if (entry.run.run_type != 'reform') return '';
        let base = OGRuns.findEntry(entry.case.casename, entry.run.baseline_run);
        return base ? base.name : (entry.run.baseline_display_name || entry.run.baseline_run || '');
    }

    static statusIcon(state){
        if (state == 'completed' || state == 'reused') return 'check-circle';
        if (state == 'running') return 'spinner fa-spin';
        if (state == 'queued') return 'clock-o';
        if (state == 'failed' || state == 'blocked') return 'exclamation-circle';
        return 'circle-o';
    }

    static render(){
        if (!OGRuns.workspace) return;
        $('#ogcRunsTitle').text('Run');
        $('#ogcRunsSub').text('Select baselines and reforms to run. Required baselines are added before their reforms.');
        $('#ogcRunWorkspace').html(`<b>${esc(OGRuns.workspace.country_name)}</b> <span class="ogc-mono ogc-mut">${esc(OGRuns.workspace.country_id)}</span>`);
        let rows = '';
        let force = $('#ogcForceRun').prop('checked');
        $.each(OGRuns.entries || [], function (id, entry) {
            let status = STATUS[entry.state] || STATUS.pending;
            let reusable = !force && (entry.reusable !== undefined
                ? entry.reusable : (entry.state == 'completed' && !entry.stale));
            let from = entry.run.run_type == 'reform' ? OGRuns.baselineName(entry) : '&mdash;';
            rows += `<tr data-key="${esc(entry.key)}">
                <td><input type="checkbox" data-role="select-run" data-key="${esc(entry.key)}"${OGRuns.selected[entry.key] ? ' checked' : ''}${OGRuns.running ? ' disabled' : ''}></td>
                <td><b>${esc(entry.name)}</b> <span class="ogc-tag ogc-tag-${entry.run.run_type == 'reform' ? 'reform' : 'base'}">${esc(entry.run.run_type)}</span></td>
                <td class="ogc-mut">${entry.run.run_type == 'reform' ? esc(from) : from}</td>
                <td><span class="ogc-run-state"><i class="fa fa-${OGRuns.statusIcon(entry.state)}"></i> ${esc(status[1])}</span>${reusable ? ' <span class="ogc-cache-tag">Cached result</span>' : ''}</td>
            </tr>`;
        });
        if (!rows) rows = '<tr><td class="ogc-empty-cell" colspan="4">No configured runs yet. Create a baseline from Cases.</td></tr>';
        $('#ogcRunRows').html(rows);
        OGRuns.renderQueue();
        OGRuns.updateControls();
    }

    static jobState(job){ return job.state || job.entry.state; }

    static renderCurrent(job){
        let entry = job.entry;
        let state = OGRuns.jobState(job);
        let status = STATUS[state] || STATUS.pending;
        let meta = [];
        if (job.stage || entry.stage) meta.push(job.stage || entry.stage);
        let queuePosition = job.queuePosition !== undefined ? job.queuePosition : entry.queuePosition;
        if (queuePosition !== undefined && queuePosition !== null) meta.push('Queue position ' + queuePosition);
        if (job.iteration || entry.iteration) meta.push('Iteration ' + (job.iteration || entry.iteration));
        let log = job.log || entry.log || [];
        let error = job.error || entry.error;
        return `<div class="ogc-job ${state == 'running' ? 'ogc-job-active' : ''}" data-job="${esc(entry.key)}">
            <div class="ogc-job-head"><b>${esc(entry.name)}</b><span class="ogc-tag ${status[0]}">${esc(status[1])}</span></div>
            ${meta.length ? `<div class="ogc-job-meta">${esc(meta.join(' / '))}</div>` : ''}
            ${job.note ? `<div class="ogc-job-meta">${esc(job.note)}</div>` : ''}
            ${error ? `<div class="ogc-run-error">${esc(error)}</div>` : ''}
            <div class="ogc-live-log-label">Live log</div>
            ${log.length
                ? `<pre class="ogc-run-log ogc-live-run-log">${esc(log.join('\n'))}</pre>`
                : '<div class="ogc-live-log-empty">Waiting for worker output...</div>'}
        </div>`;
    }

    static renderOutcome(job){
        let entry = job.entry;
        let state = OGRuns.jobState(job);
        let status = STATUS[state] || STATUS.pending;
        let completedAt = job.completedAt || entry.completedAt;
        let error = job.error || entry.error;
        return `<button class="ogc-history-row" data-act="outcome" data-case="${esc(entry.case.casename)}" data-run="${esc(entry.run.run_name)}" data-key="${esc(entry.key)}">
            <span><i class="fa fa-caret-right"></i> <b>${esc(entry.name)}</b> <span class="ogc-mut">${esc(entry.run.run_type)}</span></span>
            <span><span class="ogc-outcome-time">${esc(OGRuns.formatTime(completedAt))}</span><span class="ogc-tag ${status[0]}">${esc(status[1])}</span></span></button>
            <div class="ogc-history-log" data-outcome="${esc(entry.key)}" style="display:none">
                ${error ? `<div class="ogc-run-error">${esc(error)}</div>` : ''}
            </div>`;
    }

    static renderQueue(){
        let current = [];
        let seen = {};
        $.each(OGRuns.plan || [], function (id, job) {
            if (['planned', 'waiting', 'queued', 'running'].indexOf(OGRuns.jobState(job)) >= 0){
                current.push(job);
                seen[job.entry.key] = true;
            }
        });
        $.each(OGRuns.entries || [], function (id, entry) {
            if (ACTIVE_STATES.indexOf(entry.state) >= 0 && !seen[entry.key]){
                current.push({entry: entry, state: entry.state});
                seen[entry.key] = true;
            }
        });
        current.sort(function (a, b) {
            let aState = OGRuns.jobState(a), bState = OGRuns.jobState(b);
            if (aState == 'running' && bState != 'running') return -1;
            if (bState == 'running' && aState != 'running') return 1;
            let aPosition = a.queuePosition !== undefined ? a.queuePosition : a.entry.queuePosition;
            let bPosition = b.queuePosition !== undefined ? b.queuePosition : b.entry.queuePosition;
            aPosition = aPosition == null ? Number.MAX_SAFE_INTEGER : Number(aPosition);
            bPosition = bPosition == null ? Number.MAX_SAFE_INTEGER : Number(bPosition);
            return aPosition - bPosition || String(a.entry.name).localeCompare(String(b.entry.name));
        });
        $('#ogcCurrentQueue').html(current.length
            ? $.map(current, job => OGRuns.renderCurrent(job)).join('')
            : '<div class="ogc-queue-empty">No runs are currently queued or running.</div>');

        let outcomes = [], outcomeSeen = {};
        $.each(OGRuns.plan || [], function (id, job) {
            if (['completed', 'failed', 'cancelled', 'blocked', 'reused'].indexOf(OGRuns.jobState(job)) >= 0){
                outcomes.push(job);
                outcomeSeen[job.entry.key] = true;
            }
        });
        $.each(OGRuns.entries || [], function (id, entry) {
            if (['completed', 'failed', 'cancelled', 'stale'].indexOf(entry.state) >= 0 && !outcomeSeen[entry.key]){
                outcomes.push({entry: entry, state: entry.state});
            }
        });
        outcomes.sort((a, b) => String(b.completedAt || b.entry.completedAt || '')
            .localeCompare(String(a.completedAt || a.entry.completedAt || '')));
        $('#ogcRecentOutcomes').html(outcomes.length
            ? $.map(outcomes, job => OGRuns.renderOutcome(job)).join('')
            : '<div class="ogc-queue-empty">No run outcomes are available.</div>');
    }

    static formatTime(value){
        if (!value) return '';
        let parsed = new Date(value);
        return isNaN(parsed.getTime()) ? String(value) : parsed.toLocaleString();
    }

    static updateControls(){
        let count = 0;
        $.each(OGRuns.selected || {}, function (key, selected) { if (selected) count++; });
        let allSelected = !!(OGRuns.entries && OGRuns.entries.length)
            && OGRuns.entries.every(entry => !!OGRuns.selected[entry.key]);
        $('#ogcRunSelected').prop('disabled', OGRuns.running || !count)
            .html(`<i class="fa fa-play"></i> Run selected${count ? ' (' + count + ')' : ''}`);
        $('#ogcSelectAll').html(`<i class="fa fa-${allSelected ? 'square-o' : 'check-square-o'}"></i> ${allSelected ? 'Clear selection' : 'Select all'}`);
        let active = $.grep(OGRuns.entries || [], entry => ACTIVE_STATES.indexOf(entry.state) >= 0).length;
        $('#ogcCancelRun').toggle(!!active || OGRuns.running).prop('disabled', !active && !OGRuns.running);
        $('#ogcForceRun, #ogcSelectAll').prop('disabled', OGRuns.running);
    }

    static buildQueue(entries, selected, force){
        let chosen = $.grep(entries || [], entry => !!selected[entry.key]);
        let byKey = {};
        $.each(entries || [], (id, entry) => { byKey[entry.key] = entry; });
        let ordered = [], added = {};
        function stateOf(entry){
            return entry.state || OGRuns.normaliseState(entry.run, entry.stale);
        }
        function canReuse(entry){
            return entry.reusable !== undefined
                ? entry.reusable
                : stateOf(entry) == 'completed' && !entry.stale;
        }
        function add(entry, dependency){
            if (!entry || added[entry.key]) return;
            let invalidatedByBaseline = false;
            if (entry.run.run_type == 'reform'){
                let base = byKey[entry.case.casename + ':' + entry.run.baseline_run];
                invalidatedByBaseline = !!(base && !canReuse(base));
                if (base && (!canReuse(base) || selected[base.key])){
                    add(base, !selected[base.key]);
                }
            }
            added[entry.key] = true;
            ordered.push({
                entry: entry,
                state: canReuse(entry)
                    && !invalidatedByBaseline && !force ? 'reused' : 'planned',
                note: dependency ? 'Added because a selected reform depends on it.' : '',
                log: []
            });
        }
        $.each(chosen, function (id, entry) { add(entry, false); });
        return ordered;
    }

    static executionIsActive(execution){
        return OGRuns.execution === execution
            && OGRuns.stopExecutionID != execution.id
            && window.location.hash.split('?')[0] == '#/OGRuns'
            && OGRuns.isCurrent(execution.pageToken);
    }

    static async runSelected(){
        if (OGRuns.running) return;
        let force = $('#ogcForceRun').prop('checked');
        OGRuns.plan = OGRuns.buildQueue(OGRuns.entries, OGRuns.selected, force);
        if (!OGRuns.plan.length) return;
        let execution = Object.freeze({id: ++EXECUTION_ID, pageToken: OGRuns.pageToken});
        OGRuns.execution = execution;
        OGRuns.stopExecutionID = null;
        OGRuns.running = true;
        OGRuns.render();
        let detached = false;
        try {
            for (let i = 0; i < OGRuns.plan.length; i++){
                if (!OGRuns.executionIsActive(execution)) { detached = true; break; }
                let job = OGRuns.plan[i], entry = job.entry;
                if (job.state == 'reused'){
                    job.note = 'Existing completed results reused; no backend job was submitted.';
                    let verifiedReuse = false;
                    try {
                        await OGRuns.readStatus(job);
                        verifiedReuse = job.state == 'completed'
                            && entry.reusable !== false && !entry.stale;
                        if (verifiedReuse){
                            job.state = 'reused';
                        }else{
                            job.state = 'planned';
                            job.note = 'The previous result is no longer reusable; a new run will be submitted.';
                        }
                    }
                    catch (error) {
                        job.state = 'failed';
                        job.error = 'Could not verify the existing result: ' + String(error);
                    }
                    if (OGRuns.executionIsActive(execution)) OGRuns.render();
                    if (verifiedReuse || job.state == 'failed') continue;
                }
                if (entry.run.run_type == 'reform'){
                    let base = OGRuns.findEntry(entry.case.casename, entry.run.baseline_run);
                    let baseJob = $.grep(OGRuns.plan, item => item.entry.key == (base && base.key))[0];
                    let baseState = baseJob ? baseJob.state : (base && base.state);
                    if (['failed', 'cancelled', 'blocked'].indexOf(baseState) >= 0
                        || (!baseJob && (!base || base.state != 'completed' || base.stale))){
                        job.state = 'blocked';
                        job.error = 'Its baseline did not complete.';
                        OGRuns.render();
                        continue;
                    }
                }
                job.state = entry.run.run_type == 'reform' ? 'waiting' : 'planned';
                OGRuns.render();
                if (!OGRuns.executionIsActive(execution)) { detached = true; break; }
                try {
                    await Ogc.run(entry.case.casename, entry.run.run_name, false);
                    job.accepted = true;
                    job.state = 'queued';
                    job.stage = '';
                    job.iteration = null;
                    job.log = [];
                    job.error = '';
                    entry.state = 'queued';
                    entry.stage = '';
                    entry.iteration = null;
                    entry.log = [];
                    entry.error = '';
                    entry.completedAt = '';
                    if (!OGRuns.executionIsActive(execution)) { detached = true; break; }
                    let result = await OGRuns.waitForTerminal(job, execution);
                    if (result == 'detached' || result == 'stopped') { detached = true; break; }
                } catch (error) {
                    job.state = 'failed';
                    job.error = String(error);
                    entry.state = 'failed';
                    entry.error = job.error;
                }
                if (OGRuns.executionIsActive(execution)) OGRuns.render();
            }
        } catch (error) {
            if (OGRuns.isCurrent(execution.pageToken)) Message.danger(error);
        } finally {
            if (OGRuns.execution === execution){
                OGRuns.running = false;
                OGRuns.execution = null;
                if (OGRuns.isCurrent(execution.pageToken)){
                    OGRuns.updateControls();
                    await OGRuns.load(execution.pageToken, null, true);
                    if (!detached && OGRuns.isCurrent(execution.pageToken)) OGRuns.showSummary();
                }
            }
        }
    }

    static async waitForTerminal(job, execution){
        while (OGRuns.executionIsActive(execution)){
            let status = await OGRuns.readStatus(job);
            if (OGRuns.isCurrent(execution.pageToken)) OGRuns.render();
            if (job.state == 'completed'){
                clearRunStale(job.entry.key);
                job.entry.stale = false;
                return 'terminal';
            }
            if (['failed', 'cancelled'].indexOf(job.state) >= 0) return 'terminal';
            await new Promise(resolve => setTimeout(resolve, 2000));
        }
        return OGRuns.isCurrent(execution.pageToken) ? 'stopped' : 'detached';
    }

    static async readStatus(job){
        let entry = job.entry;
        let status = await Ogc.getRunStatus(entry.case.casename, entry.run.run_name);
        OGRuns.applyBackendStatus(entry, status);
        job.state = entry.state;
        if (job.accepted && job.state == 'pending') job.state = entry.state = 'queued';
        job.stage = entry.stage;
        job.iteration = entry.iteration;
        job.queuePosition = entry.queuePosition;
        job.completedAt = entry.completedAt;
        job.log = entry.log || [];
        job.error = entry.error || job.error;
        return status;
    }

    static showSummary(){
        let executed = $.grep(OGRuns.plan, job => job.accepted && job.state == 'completed').length;
        let reused = $.grep(OGRuns.plan, job => job.state == 'reused').length;
        let failed = $.grep(OGRuns.plan, job => ['failed', 'blocked', 'cancelled'].indexOf(job.state) >= 0).length;
        if (failed){
            Message.warning(failed + ' selected run' + (failed == 1 ? '' : 's') + ' did not complete. '
                + executed + ' executed; ' + reused + ' reused.');
        }else{
            Message.smallBoxInfo('OG-Core', executed + ' executed; ' + reused + ' reused.', 4000);
        }
    }

    static findEntry(casename, runName){
        let found = null;
        $.each(OGRuns.entries || [], function (id, entry) {
            if (entry.case.casename == casename && entry.run.run_name == runName) found = entry;
        });
        return found;
    }

    static findJob(key){
        return $.grep(OGRuns.plan || [], job => job.entry.key == key)[0] || null;
    }

    static async cancelEntry(key){
        let entry = OGRuns.entriesByKey()[key];
        if (!entry) return;
        let job = OGRuns.findJob(key);
        try {
            await Ogc.cancelRun(entry.case.casename, entry.run.run_name);
            entry.state = 'cancelled';
            entry.error = 'Cancelled by user.';
            if (job){ job.state = 'cancelled'; job.error = entry.error; }
        } catch (error) {
            Message.danger(error);
        }
        OGRuns.render();
    }

    static async cancelActive(){
        if (OGRuns.execution) OGRuns.stopExecutionID = OGRuns.execution.id;
        let active = $.grep(OGRuns.entries || [], entry => ACTIVE_STATES.indexOf(entry.state) >= 0);
        await Promise.all($.map(active, entry => OGRuns.cancelEntry(entry.key)));
        OGRuns.render();
    }

    static startMonitor(pageToken){
        let monitorID = ++OGRuns.monitorID;
        if (OGRuns.running) return;
        let monitor = async function () {
            while (OGRuns.isCurrent(pageToken) && window.location.hash.split('?')[0] == '#/OGRuns'
                && monitorID == OGRuns.monitorID && !OGRuns.running){
                let active = $.grep(OGRuns.entries || [], entry => ACTIVE_STATES.indexOf(entry.state) >= 0);
                if (!active.length) return;
                await new Promise(resolve => setTimeout(resolve, 2000));
                if (!OGRuns.isCurrent(pageToken) || monitorID != OGRuns.monitorID) return;
                await Promise.all($.map(active, async function (entry) {
                    try {
                        let status = await Ogc.getRunStatus(entry.case.casename, entry.run.run_name);
                        if (OGRuns.isCurrent(pageToken)) OGRuns.applyBackendStatus(entry, status);
                    } catch (error) { /* keep the last backend-backed state */ }
                }));
                if (OGRuns.isCurrent(pageToken)) OGRuns.render();
            }
        };
        monitor();
    }

    static initEvents(){
        $('#ogcRunsPage').off('.ogruns')
        .on('change.ogruns', '[data-role="select-run"]', function () {
            OGRuns.selected[$(this).attr('data-key')] = $(this).prop('checked');
            OGRuns.updateControls();
        })
        .on('change.ogruns', '#ogcForceRun', function () { OGRuns.render(); })
        .on('click.ogruns', '[data-act]', async function (event) {
            event.preventDefault();
            let act = $(this).attr('data-act');
            if (act == 'run-selected') OGRuns.runSelected();
            if (act == 'cancel') OGRuns.cancelActive();
            if (act == 'select-all'){
                let select = !OGRuns.entries.every(entry => OGRuns.selected[entry.key]);
                $.each(OGRuns.entries, (id, entry) => { OGRuns.selected[entry.key] = select; });
                OGRuns.render();
            }
            if (act == 'outcome'){
                let box = $(this).next('.ogc-history-log');
                box.toggle();
                $(this).find('.fa-caret-right').toggleClass('ogc-rotated', box.is(':visible'));
                if (box.is(':visible') && !box.attr('data-loaded')){
                    let existing = box.html();
                    box.html(existing + '<div class="ogc-mut ogc-log-loading">Loading log…</div>');
                    try {
                        let status = await Ogc.getRunStatus($(this).attr('data-case'), $(this).attr('data-run'));
                        let lines = $.isArray(status.run_log) ? status.run_log : [];
                        let error = status.error ? `<div class="ogc-run-error">${esc(status.error)}</div>` : '';
                        box.html(error + (lines.length
                            ? `<pre class="ogc-run-log">${esc(lines.join('\n'))}</pre>`
                            : '<span class="ogc-mut">No log output recorded.</span>'));
                        box.attr('data-loaded', '1');
                    } catch (error) { box.text(String(error)); }
                }
            }
        });
    }
}
