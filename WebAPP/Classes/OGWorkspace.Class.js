import { Ogc } from "./Ogc.Class.js";

const WORKSPACE_KEY = 'osy-ogc-country';
const SELECTION_KEY = 'osy-ogc-selection';
const WORKSPACE_ROUTES = ['/OGCases', '/OGParameters', '/OGRuns'];
const LIFECYCLE_DELAY_MS = 200;

let prepared = null;
let confirmResolve = null;
let actionResolve = null;
let returnFocus = null;
let prepareVersion = 0;
let preparing = false;
let lifecycleTimer = null;
let lifecycleView = null;

const esc = value => String(value == null ? '' : value).replace(/[&<>"']/g,
    ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));

export class OGWorkspace {
    static current(){
        try { return JSON.parse(localStorage.getItem(WORKSPACE_KEY)) || null; }
        catch (e) { return null; }
    }

    static isWorkspaceRoute(route){
        let path = String(route || '/').split('?')[0];
        return WORKSPACE_ROUTES.indexOf(path) >= 0;
    }

    static clearLocal(){
        localStorage.removeItem(WORKSPACE_KEY);
        localStorage.removeItem(SELECTION_KEY);
        prepared = null;
    }

    static takePrepared(countryId){
        if (!prepared || prepared.workspace.country_id != countryId){
            return null;
        }
        let data = prepared;
        prepared = null;
        return data;
    }

    static cancelPreparation(){
        if (!preparing){
            return;
        }
        prepareVersion++;
        preparing = false;
        let resolve = actionResolve;
        actionResolve = null;
        if (resolve) resolve('back');
        OGWorkspace.hideLifecycle();
        //If activation completed while a later opening request was in flight,
        //do not leave a backend country session behind after navigation.
        Ogc.setSession(null).catch(() => {});
    }

    static ensureUi(){
        if ($('#ogWorkspaceConfirm').length){
            return;
        }
        $('body').append(`
            <div class="ogc-modal og-workspace-confirm" id="ogWorkspaceConfirm" style="display:none">
                <div class="ogc-box og-workspace-dialog">
                    <div class="ogc-box-head"><i class="fa fa-sign-out"></i> <span id="ogWorkspaceConfirmTitle"></span></div>
                    <div class="ogc-box-body" id="ogWorkspaceConfirmBody"></div>
                    <div class="ogc-box-foot">
                        <button class="btn ogc-btn" data-og-confirm="stay">Stay</button>
                        <button class="btn ogc-btn ogc-btn-main" data-og-confirm="leave">Exit workspace</button>
                    </div>
                </div>
            </div>
            <div class="og-workspace-lifecycle" id="ogWorkspaceLifecycle" style="display:none">
                <div class="og-workspace-life-backdrop"></div>
                <div class="og-workspace-life-content">
                    <div class="og-workspace-spinner"></div>
                    <h2 id="ogWorkspaceLifeTitle"></h2>
                    <div class="og-workspace-steps" id="ogWorkspaceLifeSteps"></div>
                    <div class="og-workspace-life-error" id="ogWorkspaceLifeError"></div>
                    <div class="og-workspace-life-actions" id="ogWorkspaceLifeActions"></div>
                </div>
            </div>`);

        $(document).on('click.ogWorkspace', '[data-og-confirm]', function () {
            let choice = $(this).attr('data-og-confirm');
            $('#ogWorkspaceConfirm').hide();
            if (returnFocus && document.contains(returnFocus)){
                returnFocus.focus();
            }
            let resolve = confirmResolve;
            confirmResolve = null;
            if (resolve) resolve(choice == 'leave');
        });
        $(document).on('click.ogWorkspace', '[data-og-life-action]', function () {
            let resolve = actionResolve;
            actionResolve = null;
            if (resolve) resolve($(this).attr('data-og-life-action'));
        });
        $(document).on('keydown.ogWorkspace', function (event) {
            if (event.key == 'Escape' && $('#ogWorkspaceConfirm').is(':visible')){
                $('[data-og-confirm="stay"]').trigger('click');
            }
        });
    }

    static confirmExit(){
        let workspace = OGWorkspace.current();
        if (!workspace){
            return Promise.resolve(true);
        }
        OGWorkspace.ensureUi();
        returnFocus = document.activeElement;
        $('#ogWorkspaceConfirmTitle').text('Exit workspace?');
        $('#ogWorkspaceConfirmBody').html(
            `<p>Your saved cases and results will be available when you return.</p>
             <p class="og-workspace-dialog-note">Running jobs are not cancelled and will continue in the background.</p>`
        );
        $('#ogWorkspaceConfirm').css('display', 'flex');
        $('[data-og-confirm="stay"]').focus();
        return new Promise(resolve => { confirmResolve = resolve; });
    }

    static revealLifecycle(view){
        if (!view || lifecycleView !== view){
            return;
        }
        OGWorkspace.ensureUi();
        $('#ogWorkspaceLifeTitle').text(view.title);
        $('#ogWorkspaceLifeError, #ogWorkspaceLifeActions').empty().hide();
        $('#ogWorkspaceLifecycle').removeClass('og-life-failed').css('display', 'flex');
        $('#ogWorkspaceLifeSteps').html($.map(view.steps, function (label, index) {
            return `<div class="og-workspace-step og-step-pending" data-step="${index}">
                <i class="fa fa-circle-o"></i><span>${esc(label)}</span>
            </div>`;
        }).join(''));
        view.visible = true;
        $.each(view.states, function (index, state) {
            OGWorkspace.paintStep(index, state);
        });
    }

    static showLifecycle(title, steps, delay = 0){
        if (lifecycleTimer !== null){
            clearTimeout(lifecycleTimer);
            lifecycleTimer = null;
        }
        $('#ogWorkspaceLifecycle').hide().removeClass('og-life-failed');
        let view = {
            title: title,
            steps: steps,
            states: $.map(steps, () => 'pending'),
            visible: false
        };
        lifecycleView = view;
        if (delay > 0){
            lifecycleTimer = setTimeout(function () {
                lifecycleTimer = null;
                OGWorkspace.revealLifecycle(view);
            }, delay);
            return;
        }
        OGWorkspace.revealLifecycle(view);
    }

    static paintStep(index, state){
        let row = $(`#ogWorkspaceLifeSteps [data-step="${index}"]`);
        let icon = state == 'done' ? 'fa-check' : state == 'failed' ? 'fa-times' :
            state == 'current' ? 'fa-circle-o-notch fa-spin' : 'fa-circle-o';
        row.attr('class', 'og-workspace-step og-step-' + state);
        row.find('.fa').attr('class', 'fa ' + icon);
    }

    static setStep(index, state){
        if (lifecycleView && lifecycleView.states[index] !== undefined){
            lifecycleView.states[index] = state;
        }
        if (lifecycleView && lifecycleView.visible){
            OGWorkspace.paintStep(index, state);
        }
    }

    static currentStep(){
        if (!lifecycleView){
            return undefined;
        }
        let index = lifecycleView.states.indexOf('current');
        return index >= 0 ? index : undefined;
    }

    static failure(message, actions){
        if (lifecycleTimer !== null){
            clearTimeout(lifecycleTimer);
            lifecycleTimer = null;
        }
        if (lifecycleView && !lifecycleView.visible){
            OGWorkspace.revealLifecycle(lifecycleView);
        }else{
            OGWorkspace.ensureUi();
        }
        $('#ogWorkspaceLifecycle').addClass('og-life-failed');
        $('#ogWorkspaceLifeError').text(message).show();
        let html = $.map(actions, function (action) {
            let main = action.primary ? ' ogc-btn-main' : '';
            return `<button class="btn ogc-btn${main}" data-og-life-action="${esc(action.id)}">${esc(action.label)}</button>`;
        }).join('');
        $('#ogWorkspaceLifeActions').html(html).css('display', 'flex');
        return new Promise(resolve => { actionResolve = resolve; });
    }

    static hideLifecycle(){
        if (lifecycleTimer !== null){
            clearTimeout(lifecycleTimer);
            lifecycleTimer = null;
        }
        lifecycleView = null;
        $('#ogWorkspaceLifecycle').hide().removeClass('og-life-failed');
        actionResolve = null;
    }

    static async prepare(country, isCurrent = () => true){
        const version = ++prepareVersion;
        preparing = true;
        prepared = null;
        const active = () => preparing && version == prepareVersion && isCurrent();
        while (true){
            OGWorkspace.showLifecycle('Opening ' + country.country_name, [
                'Checking the installed calibration...',
                'Activating the country workspace...',
                'Loading cases...',
                'Loading runs...'
            ], LIFECYCLE_DELAY_MS);
            let sessionActivated = false;
            try {
                OGWorkspace.setStep(0, 'current');
                let installed = await Ogc.getInstalledCalibrations();
                if (!active()) return false;
                let records = installed.calibrations || [];
                let record = $.grep(records, item => item.country_id == country.country_id)[0];
                if (!record){
                    throw 'That calibration is no longer installed.';
                }
                OGWorkspace.setStep(0, 'done');
                OGWorkspace.setStep(1, 'current');

                await Ogc.setSession(null, country.country_id);
                sessionActivated = true;
                if (!active()){
                    await Ogc.setSession(null).catch(() => {});
                    return false;
                }
                OGWorkspace.setStep(1, 'done');
                OGWorkspace.setStep(2, 'current');

                let casesResponse = await Ogc.getCases(country.country_id);
                if (!active()){
                    await Ogc.setSession(null).catch(() => {});
                    return false;
                }
                let cases = $.isArray(casesResponse) ? casesResponse : (casesResponse.cases || []);
                cases = $.grep(cases, item => item.country_id == country.country_id);
                OGWorkspace.setStep(2, 'done');
                OGWorkspace.setStep(3, 'current');

                let runResults = await Promise.all($.map(cases, function (item) {
                    return Ogc.getRuns(country.country_id, item.casename)
                        .then(response => ({ casename: item.casename, runs: response.runs || [] }))
                        .catch(error => ({ casename: item.casename, runs: [], error: error }));
                }));
                if (!active()){
                    await Ogc.setSession(null).catch(() => {});
                    return false;
                }
                let runsByCase = {};
                let failedRuns = [];
                $.each(runResults, function (id, result) {
                    runsByCase[result.casename] = result.runs;
                    if (result.error) failedRuns.push(result.casename);
                });
                OGWorkspace.setStep(3, 'done');

                let workspace = {
                    country_id: country.country_id,
                    country_name: country.country_name
                };
                localStorage.setItem(WORKSPACE_KEY, JSON.stringify(workspace));
                prepared = { workspace, cases, installed: records, runsByCase, failedRuns };
                preparing = false;
                OGWorkspace.hideLifecycle();
                return true;
            }catch (error){
                if (sessionActivated){
                    try {
                        await Ogc.setSession(null);
                        sessionActivated = false;
                    }catch (cleanupError){
                        error = String(error) + ' The country session could not be cleared: ' + String(cleanupError);
                    }
                }
                if (!active()) return false;
                let current = OGWorkspace.currentStep();
                if (current !== undefined) OGWorkspace.setStep(current, 'failed');
                let choice = await OGWorkspace.failure(String(error), [
                    { id: 'back', label: 'Return to OG-Core' },
                    { id: 'retry', label: 'Retry', primary: true }
                ]);
                if (choice == 'retry') continue;
                preparing = false;
                OGWorkspace.hideLifecycle();
                return false;
            }
        }
    }

    static async leave(){
        let workspace = OGWorkspace.current();
        if (!workspace){
            return true;
        }
        let confirmed = await OGWorkspace.confirmExit();
        if (!confirmed){
            return false;
        }
        while (true){
            OGWorkspace.showLifecycle('Exiting workspace', [
                'Closing the country workspace...'
            ], LIFECYCLE_DELAY_MS);
            OGWorkspace.setStep(0, 'current');
            try {
                await Ogc.setSession(null);
                OGWorkspace.clearLocal();
                OGWorkspace.setStep(0, 'done');
                OGWorkspace.hideLifecycle();
                return true;
            }catch (error){
                OGWorkspace.setStep(0, 'failed');
                let choice = await OGWorkspace.failure(String(error), [
                    { id: 'stay', label: 'Stay' },
                    { id: 'retry', label: 'Retry', primary: true }
                ]);
                if (choice == 'stay'){
                    OGWorkspace.hideLifecycle();
                    return false;
                }
                // The backend session is still active when cleanup fails. Keep
                // the local workspace so Retry remains safe and truthful.
                continue;
            }
        }
    }
}
