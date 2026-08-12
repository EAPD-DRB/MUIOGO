export class MuiogoShell {

    // Selected model for the whole shell: 'og', 'clews', or null (nothing picked
    // yet, home shows the model pick screen). Persisted so a reload keeps context.
    static getModel(){
        return localStorage.getItem('osy-model');
    }

    static setModel(model){
        if (model){
            localStorage.setItem('osy-model', model);
        }else{
            localStorage.removeItem('osy-model');
        }
    }

    // Body mode class drives all per-model chrome (sidebar sections, navbar
    // pieces, selector active state) from muiogo.css.
    static applyModel(){
        let model = MuiogoShell.getModel();
        $('body').removeClass('osy-mode-none osy-mode-og osy-mode-clews');
        if (model == 'og'){
            $('body').addClass('osy-mode-og');
        }else if (model == 'clews'){
            $('body').addClass('osy-mode-clews');
        }else{
            $('body').addClass('osy-mode-none');
        }
    }

    // Delegated so it works for the header buttons and the pick screen cards,
    // both of which load asynchronously.
    static initEvents(onRequest){
        $(document).off('click.osyModel');
        $(window).off('hashchange.osyNav').on('hashchange.osyNav', function () {
            MuiogoShell.syncSidebarActive();
        });
        let sidebar = document.getElementById('left-panel');
        if (sidebar && window.MutationObserver){
            if (MuiogoShell.sidebarObserver) MuiogoShell.sidebarObserver.disconnect();
            MuiogoShell.sidebarObserver = new MutationObserver(function () {
                MuiogoShell.syncSidebarActive();
            });
            MuiogoShell.sidebarObserver.observe(sidebar, {childList: true, subtree: true});
        }
        // Sidebar.html is loaded asynchronously from index.html. Retry briefly so
        // a direct deep-link such as #/OGCases gets the same active marker as a
        // click, even when the route wins the race with the sidebar fragment.
        [0, 100, 300].forEach(delay => setTimeout(() => {
            MuiogoShell.syncSidebarActive();
        }, delay));
        $(document).on('click.osyModel', '.osy-selectmodel', function(e){
            e.preventDefault();
            let model = $(this).attr('data-model');
            if (onRequest){
                onRequest(model);
                return;
            }
            MuiogoShell.setModel(model);
            MuiogoShell.applyModel();
            let hash = window.location.hash;
            if (hash == '' || hash == '#' || hash == '#/'){
                // already home: crossroads ignores a repeated identical request
                // unless its state is reset first
                crossroads.resetState();
                crossroads.parse('/');
            }else{
                window.location.hash = '#/';
            }
        });
    }

    static syncSidebarActive(){
        let hash = window.location.hash || '#/';
        let route = hash.split('?')[0];
        if (route == '#') route = '#/';
        let nav = $('#Navi');
        if (!nav.length) return;
        let target = nav.children('li').filter(function () {
            return $(this).children('a').attr('href') == route;
        });
        if (!target.length && route == '#/') target = nav.children('li.nav-home');
        // Keep SmartAdmin's `open` submenu state intact; it is independent of
        // which route currently owns the active marker.
        nav.children('li').removeClass('active');
        target.addClass('active');
    }
}
