import { Message } from "../../Classes/Message.Class.js";
import { Base } from "../../Classes/Base.Class.js";
import { Html } from "../../Classes/Html.Class.js";
import { Clews } from "../../Classes/Clews.Class.js";
import { Sidebar } from "./Sidebar.js";

//register, manifest and case names render into markup, escape them
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g,
    ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));

const POLL_MS = 2500;

//incremented on every visit and route change; async work from an older visit
//must not repaint or keep polling on the new page
let PAGE_ID = 0;
//one entry per country block on screen, by key: { key, source, menu, entry }
let BLOCKS = {};
//every case on this machine, from the last refresh
let INSTALLED = [];
//the one running install: { timer, key }, or null
let POLL = null;

export default class ClewsInstall {

    static onLoad(){
        ClewsInstall.stopPoll();
        PAGE_ID++;
        ClewsInstall.initEvents();
        ClewsInstall.refresh(PAGE_ID);
    }

    static isCurrent(pageID){
        return pageID == PAGE_ID;
    }

    static stopPoll(){
        if (POLL){
            clearInterval(POLL.timer);
            POLL = null;
        }
    }

    static initEvents(){
        //a poll must not outlive the page
        $(window).off('hashchange.clwPolls').on('hashchange.clwPolls', function () {
            PAGE_ID++;
            ClewsInstall.stopPoll();
        });
        $('.clw-page').off('click.clw').on('click.clw', '[data-act]', function (e) {
            e.preventDefault();
            e.stopPropagation();
            let act = $(this).attr('data-act');
            let block = $(this).closest('.clw-country');
            let key = block.attr('data-key');
            if (act == 'install-latest'){
                ClewsInstall.install(key, block.attr('data-latest-vintage'), block.attr('data-latest-case'));
            }else if (act == 'install'){
                let row = $(this).closest('tr');
                ClewsInstall.install(key, row.attr('data-vintage'), row.attr('data-case'));
            }else if (act == 'toggle-all'){
                block.find('.clw-all').toggle();
                $(this).find('.fa').toggleClass('fa-caret-down fa-caret-up');
            }else if (act == 'delete'){
                ClewsInstall.confirmDelete($(this).closest('[data-case]').attr('data-case'));
            }
        });
        $('#clwLookup').off('click.clw').on('click.clw', function (e) {
            e.preventDefault();
            ClewsInstall.lookup();
        });
        $('#clwSource').off('keydown.clw').on('keydown.clw', function (e) {
            if (e.key == 'Enter'){
                e.preventDefault();
                ClewsInstall.lookup();
            }
        });
    }

    //── loading ──────────────────────────────────────────────────────────────

    //the register and what is on this machine, then one block per repository;
    //each block reads its repository (manifest or a scan of its contents)
    static refresh(pageID){
        $('#clwCountries').html('<div class="clw-note"><i class="fa fa-cog fa-spin"></i> Reading the list of country models...</div>');
        Promise.all([Clews.getCountryCatalog(), Clews.getInstalledCountries()])
        .then(data => {
            if (!ClewsInstall.isCurrent(pageID)){
                return;
            }
            let [catalog, installed] = data;
            INSTALLED = installed.cases || [];
            let entries = catalog.countries || [];
            ClewsInstall.noteSource(catalog.catalog_source, entries.length);
            BLOCKS = {};
            let html = '';
            $.each(entries, function (i, c) {
                let key = 'reg-' + c.catalog_key;
                BLOCKS[key] = { key: key, entry: c, source: { source_type: 'catalog', catalog_key: c.catalog_key }, menu: null };
                html += ClewsInstall.blockHtml(BLOCKS[key]);
            });
            $('#clwCountries').html(html);
            $.each(BLOCKS, function (key, b) {
                ClewsInstall.loadBlock(b, pageID);
            });
            ClewsInstall.renderInstalled();
            //an added repository stays on screen across refreshes
            $('#clwAdded .clw-country').each(function () {
                let key = $(this).attr('data-key');
                if (BLOCKS[key]){
                    ClewsInstall.loadBlock(BLOCKS[key], pageID);
                }
            });
        })
        .catch(error => {
            if (!ClewsInstall.isCurrent(pageID)){
                return;
            }
            Message.danger(error);
            $('#clwCountries').html('<div class="clw-note clw-err">' + esc(error) + '</div>');
        });
    }

    static noteSource(source, count){
        let note = $('#clwSourceNote');
        if (source == 'cache'){
            note.text('No connection to the country list. Showing the last saved list; installing needs a connection.').show();
        }else if (count == 0){
            note.text('The list of country models could not be loaded. You can still add a repository below.').show();
        }else{
            note.hide();
        }
    }

    static loadBlock(b, pageID){
        Clews.inspectSource(b.source)
        .then(menu => {
            if (!ClewsInstall.isCurrent(pageID)){
                return;
            }
            b.menu = menu;
            ClewsInstall.rerender(b);
            ClewsInstall.renderInstalled();
        })
        .catch(error => {
            if (!ClewsInstall.isCurrent(pageID)){
                return;
            }
            b.error = error;
            ClewsInstall.rerender(b);
        });
    }

    static rerender(b){
        let open = ClewsInstall.block(b.key).find('.clw-all').is(':visible');
        ClewsInstall.block(b.key).replaceWith(ClewsInstall.blockHtml(b));
        if (open){
            ClewsInstall.block(b.key).find('.clw-all').show().end().find('[data-act="toggle-all"] .fa').toggleClass('fa-caret-down fa-caret-up');
        }
    }

    static block(key){
        return $('.clw-country').filter(function () { return $(this).attr('data-key') == key; });
    }

    //── what belongs where ───────────────────────────────────────────────────

    //a case on this machine belongs to the version whose case name it starts
    //with (Philippines_v18_GOLD belongs to v18 through Philippines_v18); the
    //longest match wins so Philippines_v12_ENV_LAND is not read as Philippines_v12
    static attribute(menu, casename){
        let best = null;
        $.each(menu.vintages || [], function (i, v) {
            $.each(v.cases || [], function (j, c) {
                if (casename == c.case || casename.indexOf(c.case + '_') == 0){
                    if (!best || c.case.length > best.caseName.length){
                        best = { vintage: v, caseName: c.case };
                    }
                }
            });
        });
        return best;
    }

    //installed cases grouped by version for one block: [{vintage, cases: [names]}]
    static installedByVersion(menu){
        let groups = {};
        $.each(INSTALLED, function (i, rec) {
            let hit = ClewsInstall.attribute(menu, rec.casename);
            if (hit){
                (groups[hit.vintage.id] = groups[hit.vintage.id] || { vintage: hit.vintage, cases: [] }).cases.push(rec.casename);
            }
        });
        let out = [];
        $.each(menu.vintages || [], function (i, v) {
            if (groups[v.id]){
                groups[v.id].cases.sort();
                out.push(groups[v.id]);
            }
        });
        return out;
    }

    static latestOf(menu){
        let vintages = menu.vintages || [];
        if (!vintages.length){
            return null;
        }
        let v = vintages.find(x => x.recommended) || vintages[0];
        let c = (v.cases || []).find(x => x.recommended) || (v.cases || [])[0];
        return { vintage: v, caseName: c ? c.case : null };
    }

    //── rendering ────────────────────────────────────────────────────────────

    //paint one repository block from a menu and a list of the machine's cases,
    //replacing whatever is on screen; the browser test drives the page this way
    static renderOne(menu, installed){
        //a new visit as far as pending loads are concerned, so an initial
        //refresh still in flight cannot repaint over what is drawn here
        PAGE_ID++;
        ClewsInstall.stopPoll();
        INSTALLED = installed || [];
        let source = menu.source && menu.source.repo_url
            ? { source_type: 'repo_url', repo_url: menu.source.repo_url }
            : { source_type: 'local_path', local_path: (menu.source || {}).local_path || '' };
        BLOCKS = { test: { key: 'test', entry: null, source: source, menu: menu } };
        $('#clwCountries').html(ClewsInstall.blockHtml(BLOCKS.test));
        ClewsInstall.renderInstalled();
    }

    static repoLabel(b){
        let url = (b.menu && b.menu.source && (b.menu.source.repo_url || b.menu.source.local_path))
            || (b.entry && b.entry.repo_url) || b.source.repo_url || b.source.local_path || '';
        return { url: url, text: url.replace(/^https?:\/\/(www\.)?/i, '') };
    }

    static blockHtml(b){
        let repo = ClewsInstall.repoLabel(b);
        let title = repo.url && /^https?:/i.test(repo.url)
            ? '<a class="clw-url" href="' + esc(repo.url) + '" target="_blank" rel="noopener">' + esc(repo.text) + '</a>'
            : '<span class="clw-url">' + esc(repo.text) + '</span>';
        let name = (b.menu && b.menu.name) || (b.entry && b.entry.country_name) || '';
        let head = '<div class="clw-block-head">' + title + (name ? ' <span class="clw-muted">' + esc(name) + '</span>' : '');

        if (b.error){
            return '<div class="clw-block clw-country" data-key="' + esc(b.key) + '">' + head + '</div>'
                + '<div class="clw-note clw-err"><i class="fa fa-exclamation-triangle"></i> ' + esc(b.error) + '</div></div>';
        }
        if (!b.menu){
            return '<div class="clw-block clw-country" data-key="' + esc(b.key) + '">' + head + '</div>'
                + '<div class="clw-note"><i class="fa fa-cog fa-spin"></i> Reading the repository...</div></div>';
        }

        let menu = b.menu;
        let latest = ClewsInstall.latestOf(menu);
        let have = ClewsInstall.installedByVersion(menu);
        let haveLatest = latest && have.some(g => g.vintage.id == latest.vintage.id);
        let badge = haveLatest ? '<span class="clw-badge clw-b-ok">up to date</span>'
            : have.length ? '<span class="clw-badge clw-b-upd">newer version available</span>'
            : '<span class="clw-badge clw-b-mut">nothing installed</span>';
        head += badge + '</div>';

        let html = '<div class="clw-block clw-country" data-key="' + esc(b.key) + '"'
            + (latest ? ' data-latest-vintage="' + esc(latest.vintage.id) + '" data-latest-case="' + esc(latest.caseName) + '"' : '') + '>' + head;

        //newest version and what Install does
        if (latest){
            let latestExists = INSTALLED.some(r => r.casename == latest.caseName);
            let when = latest.vintage.last_changed ? ' <span class="clw-muted">(' + esc(String(latest.vintage.last_changed).slice(0, 10)) + ')</span>' : '';
            html += '<div class="clw-latest"><div class="clw-latest-text">Newest version <b>' + esc(latest.vintage.id) + '</b>' + when
                + ' &mdash; Install adds the model <b>' + esc(latest.caseName) + '</b>'
                + (latestExists ? ' <span class="clw-muted">(already here)</span>' : '') + '</div>'
                + '<div class="clw-latest-actions">'
                + '<button class="btn clw-btn clw-btn-main" data-act="install-latest"' + (latestExists || latest.vintage.version_gate ? ' disabled' : '')
                + (latest.vintage.version_gate ? ' title="' + esc(latest.vintage.version_gate) + '"' : '') + '><i class="fa fa-download"></i> Install</button>'
                + '<button class="btn clw-btn" data-act="toggle-all">All versions <span class="clw-muted">(' + esc((menu.vintages || []).length) + ')</span> <i class="fa fa-caret-down"></i></button>'
                + '</div></div>';
            html += '<div class="clw-status"></div>';
            if (menu.discovered){
                html += '<div class="clw-fine">Versions read from the repository\'s contents'
                    + (menu.ordering == 'date' ? ', newest by last change.' : '; the repository\'s history could not be read, so they are ordered by name.') + '</div>';
            }
        }

        //every version, newest first
        html += '<div class="clw-all" style="display:none"><table class="table table-condensed clw-table"><tbody>';
        $.each(menu.vintages || [], function (i, v) {
            let isLatest = latest && v.id == latest.vintage.id;
            let when = v.last_changed ? '<span class="clw-muted">' + esc(String(v.last_changed).slice(0, 10)) + '</span>' : '';
            $.each(v.cases || [], function (j, c) {
                let exists = INSTALLED.some(r => r.casename == c.case);
                html += '<tr data-vintage="' + esc(v.id) + '" data-case="' + esc(c.case) + '">'
                    + '<td class="clw-vcell">' + (j == 0 ? '<span class="clw-vid">' + esc(v.id) + '</span>' + (isLatest ? ' <span class="clw-badge clw-b-ok">newest</span>' : '') : '') + '</td>'
                    + '<td class="clw-case">' + esc(c.case) + (c.role && (v.cases.length > 1) ? ' <span class="clw-muted">' + esc(c.role) + '</span>' : '') + '</td>'
                    + '<td>' + (j == 0 ? when : '') + '</td>'
                    + '<td class="clw-status">' + (exists ? 'installed here' : '') + '</td>'
                    + '<td class="clw-act">' + (exists
                        ? '<button class="btn btn-default btn-xs" disabled>Install</button>'
                        : v.version_gate
                            ? '<button class="btn btn-default btn-xs" disabled title="' + esc(v.version_gate) + '">Install</button>'
                            : '<button class="btn btn-primary btn-xs" data-act="install">Install</button>') + '</td></tr>';
            });
        });
        html += '</tbody></table></div></div>';
        return html;
    }

    //every model on this machine: grouped under the repository it belongs to
    //(by version), then the ones that belong to no repository on screen
    static renderInstalled(){
        let pending = Object.values(BLOCKS).some(b => !b.menu && !b.error);
        if (pending){
            $('#clwInstalled').html('<div class="clw-note"><i class="fa fa-cog fa-spin"></i> Reading the repositories...</div>');
            return;
        }
        if (!INSTALLED.length){
            $('#clwInstalled').html('<div class="clw-note">No model is installed yet.</div>');
            return;
        }
        let claimed = {};
        let html = '';
        $.each(BLOCKS, function (key, b) {
            if (!b.menu){
                return;
            }
            let have = ClewsInstall.installedByVersion(b.menu);
            if (!have.length){
                return;
            }
            let repo = ClewsInstall.repoLabel(b);
            html += '<div class="clw-have-title">' + esc(repo.text) + (b.menu.name ? ' <span class="clw-muted">' + esc(b.menu.name) + '</span>' : '') + '</div>';
            html += '<table class="table table-condensed clw-table clw-havetable"><tbody>';
            $.each(have, function (i, g) {
                $.each(g.cases, function (j, name) {
                    claimed[name] = true;
                    html += ClewsInstall.installedRowHtml(j == 0 ? g.vintage.id : '', name);
                });
            });
            html += '</tbody></table>';
        });
        let others = INSTALLED.filter(r => !claimed[r.casename]).map(r => r.casename).sort();
        if (others.length){
            html += '<div class="clw-have-title">Other models <span class="clw-muted">not from a listed repository: the demo, uploads, copies, imports</span></div>';
            html += '<table class="table table-condensed clw-table clw-havetable"><tbody>';
            $.each(others, function (i, name) {
                html += ClewsInstall.installedRowHtml('', name);
            });
            html += '</tbody></table>';
        }
        $('#clwInstalled').html(html);
    }

    static installedRowHtml(versionLabel, name){
        return '<tr data-case="' + esc(name) + '">'
            + '<td class="clw-vcell">' + (versionLabel ? '<span class="clw-vid">' + esc(versionLabel) + '</span>' : '') + '</td>'
            + '<td class="clw-case">' + esc(name) + '</td>'
            + '<td class="clw-act"><button class="btn btn-default btn-xs clw-del" data-act="delete" title="Delete this model with all its scenarios and results"><i class="fa fa-trash-o"></i> Delete</button></td></tr>';
    }

    //── add a repository ─────────────────────────────────────────────────────

    static lookup(){
        let pageID = PAGE_ID;
        let text = ($('#clwSource').val() || '').trim();
        if (!text){
            Message.warning('Enter a repository URL or a folder first.');
            return;
        }
        let source = /^https?:\/\//i.test(text)
            ? { source_type: 'repo_url', repo_url: text }
            : { source_type: 'local_path', local_path: text };
        let key = 'added-' + text.replace(/[^A-Za-z0-9]+/g, '-');
        BLOCKS[key] = { key: key, entry: null, source: source, menu: null };
        ClewsInstall.block(key).remove();
        $('#clwAdded').prepend(ClewsInstall.blockHtml(BLOCKS[key]));
        ClewsInstall.loadBlock(BLOCKS[key], pageID);
    }

    //── installing ───────────────────────────────────────────────────────────

    static install(key, vintage, casename){
        let pageID = PAGE_ID;
        let b = BLOCKS[key];
        if (!b || !vintage || !casename){
            return;
        }
        if (POLL){
            Message.warning('An install is already running. Wait for it to finish.');
            return;
        }
        let payload = Object.assign({}, b.source, { vintage: vintage, cases: [casename] });
        ClewsInstall.setStatus(key, 'Installing ' + casename + ': starting...', 'clw-run', true);
        Clews.installCountry(payload)
        .then(job => {
            if (!ClewsInstall.isCurrent(pageID)){
                return;
            }
            ClewsInstall.pollJob(job.install_id, key, casename, pageID);
        })
        .catch(error => {
            if (!ClewsInstall.isCurrent(pageID)){
                return;
            }
            ClewsInstall.setStatus(key, 'Installing ' + casename + ' failed: ' + error, 'clw-err', false);
            Message.danger(error);
        });
    }

    static setStatus(key, text, cls, busy){
        let block = ClewsInstall.block(key);
        block.find('.clw-status').attr('class', 'clw-status ' + cls).text(text);
        block.find('[data-act="install-latest"], [data-act="install"]').prop('disabled', busy);
    }

    static pollJob(installId, key, casename, pageID){
        ClewsInstall.stopPoll();
        let tick = function () {
            if (!ClewsInstall.isCurrent(pageID)){
                ClewsInstall.stopPoll();
                return;
            }
            Clews.getInstallStatus(installId)
            .then(job => {
                if (ClewsInstall.isCurrent(pageID)){
                    ClewsInstall.applyJob(job, key, casename, pageID);
                }
            })
            .catch(error => {
                //a transient poll error keeps the timer; the job continues server side
            });
        };
        POLL = { timer: setInterval(tick, POLL_MS), key: key };
        tick();
    }

    static applyJob(job, key, casename, pageID){
        let results = job.results || [];
        if (job.install_state == 'installed'){
            ClewsInstall.stopPoll();
            let failed = results.filter(r => r.status == 'failed');
            if (failed.length){
                let why = failed[0].message || failed[0].error || 'see the server log';
                ClewsInstall.setStatus(key, 'Installing ' + casename + ' failed: ' + why, 'clw-err', false);
                Message.danger('Installing ' + casename + ' failed: ' + why);
                return;
            }
            Message.success(casename + ' is installed and appears in the case list.');
            ClewsInstall.refreshAfterChange(pageID, key, casename + ' installed.');
            return;
        }
        if (job.install_state == 'failed'){
            ClewsInstall.stopPoll();
            let why = job.error || (results[0] && (results[0].message || results[0].error)) || 'see the server log';
            ClewsInstall.setStatus(key, 'Installing ' + casename + ' failed: ' + why, 'clw-err', false);
            Message.danger('Install failed: ' + why);
            return;
        }
        ClewsInstall.setStatus(key, 'Installing ' + casename + ': ' + (job.progress_label || job.install_state) + '...', 'clw-run', true);
    }

    //after an install or a delete: re-read what is on the machine and repaint
    //every block, keeping a short note on the block that changed
    static refreshAfterChange(pageID, key, note){
        Clews.getInstalledCountries()
        .then(installed => {
            if (!ClewsInstall.isCurrent(pageID)){
                return;
            }
            INSTALLED = installed.cases || [];
            $.each(BLOCKS, function (k, b) {
                if (b.menu){
                    //existence flags in the menu are stale now; the block repaints from INSTALLED
                    ClewsInstall.rerender(b);
                }
            });
            ClewsInstall.renderInstalled();
            if (key && note){
                ClewsInstall.setStatus(key, note, 'clw-ok', false);
            }
        })
        .catch(error => {});
    }

    //── deleting ─────────────────────────────────────────────────────────────

    //the same two steps the Home page uses: make the case the active one, then
    //delete it; /deleteCase refuses anything but the active case
    static confirmDelete(casename){
        let pageID = PAGE_ID;
        $.SmartMessageBox({
            title: "Delete model",
            content: "You are about to delete <b class='danger'>" + esc(casename) + "</b> with all its scenarios and results. This cannot be undone. Are you sure?",
            buttons: '[No][Yes]'
        }, function (ButtonPressed) {
            if (ButtonPressed !== "Yes"){
                return;
            }
            Base.setSession(casename)
            .then(() => Base.deleteCaseStudy(casename))
            .then(response => {
                if (!ClewsInstall.isCurrent(pageID)){
                    return;
                }
                if (response.status_code == 'success_session'){
                    Message.success('Model ' + casename + ' deleted.');
                    Html.removeCase(casename);
                    Sidebar.Reload(null);
                    ClewsInstall.refreshAfterChange(pageID, null, null);
                }else{
                    Message.warning(response.message);
                }
            })
            .catch(error => {
                if (ClewsInstall.isCurrent(pageID)){
                    Message.danger(error);
                }
            });
        });
    }
}
