import { Osemosys } from "../../Classes/Osemosys.Class.js";
import { Message } from "../../Classes/Message.Class.js";
import { NavigationGuard } from "../../Classes/NavigationGuard.Class.js";
import { MuiogoShell } from "../../Classes/MuiogoShell.Class.js";
import { OGWorkspace } from "../../Classes/OGWorkspace.Class.js";
import { Model } from "./Routes.Model.js";

export class Routes {
    static Load(casename) {
        Osemosys.getParamFile()
        .then(PARAMETERS => {
            const promise = [];
            promise.push(PARAMETERS);
            const VARIABLES = Osemosys.getParamFile('Variables.json');
            promise.push(VARIABLES);
            return Promise.all(promise);
        })
        .then(data => {
            let [PARAMETERS, VARIABLES] = data;
            let model = new Model(PARAMETERS,VARIABLES);
            this.getRoutes(model);
        })
        .catch(error => {
            Message.danger(error);
        });
    }

    static getRoutes(model){
        let requestedModel = null;
        let viewVersion = 0;

        function beginView(){
            viewVersion++;
            $('#content').html('<h1 class="ajax-loading-animation"><i class="fa fa-cog fa-spin"></i> Loading...</h1>');
            return viewVersion;
        }

        function loadView(version, path, pageId, onLoad){
            $.get(path).then(function (html) {
                if (version != viewVersion) return;
                $('.osy-content').html(html);
                localStorage.setItem('osy-pageId', pageId);
                if (onLoad) onLoad();
            });
        }

        function enterModel(model){
            MuiogoShell.setModel(model);
            MuiogoShell.applyModel();
            $('body').removeClass('osy-og-workspace');
            if (model == 'og') Message.clearMessages();
        }

        function enterWorkspace(){
            enterModel('og');
            $('body').addClass('osy-og-workspace');
        }

        function requireWorkspace(){
            if (OGWorkspace.current()){
                return true;
            }
            window.location.replace(window.location.href.split('#')[0] + '#/OGCore');
            return false;
        }

        //settings 
        import('../App/Controller/Settings.js')
        .then(Settings => {
            $( "#osy-demo" ).load( 'App/View/Settings.html', function() {
                Settings.default.Load();
            });
        });

        MuiogoShell.applyModel();
        MuiogoShell.initEvents(function (model) {
            let currentRoute = routeFromHash(window.location.hash);
            if (!OGWorkspace.isWorkspaceRoute(currentRoute)){
                requestedModel = null;
                MuiogoShell.setModel(model);
                MuiogoShell.applyModel();
                let hash = window.location.hash;
                if (hash == '' || hash == '#' || hash == '#/'){
                    crossroads.resetState();
                    crossroads.parse('/');
                }else{
                    window.location.hash = '#/';
                }
                return;
            }
            requestedModel = model;
            window.location.hash = '#/';
        });

        //Sidebar.Load(PARAMETERS);
        //home depends on the selected model: OG-Core, CLEWS, or the pick screen
        crossroads.addRoute('/', function() {
            let selected = requestedModel || MuiogoShell.getModel();
            requestedModel = null;
            enterModel(selected);
            let version = beginView();
            if (selected == 'og'){
                import('../App/Controller/OGCore.js')
                .then(OGCore => {
                    loadView(version, 'App/View/OGCore.html', 'OGCore', () => OGCore.default.onLoad());
                });
            }else if (selected == 'clews'){
                import('../App/Controller/Home.js')
                .then(Home => {
                    loadView(version, 'App/View/Home.html', 'Home', () => Home.default.onLoad());
                });
            }else{
                loadView(version, 'App/View/ModelPick.html', 'ModelPick');
            }
        });

        // crossroads.addRoute('/Settings', function() {
        //     $('#content').html('<h1 class="ajax-loading-animation"><i class="fa fa-cog fa-spin"></i> Loading...</h1>');
        //     import('../App/Controller/Settings.js')
        //     .then(Settings => {
        //         $( "#osy-demo" ).load( 'App/View/Settings.html', function() {
        //             Settings.default.Load();
        //         });
        //     });
        // }); 

        crossroads.addRoute('/Config', function() {
            enterModel('clews');
            let version = beginView();
            import('../App/Controller/Config.js')
            .then(Config => {
                loadView(version, 'App/View/Config.html', 'Config', () => Config.default.onLoad());
            });
        });  
        crossroads.addRoute('/AddCase', function() {
            enterModel('clews');
            let version = beginView();
            import('../App/Controller/AddCase.js')
            .then(AddCase => {
                loadView(version, 'App/View/AddCase.html', 'AddCase', () => AddCase.default.onLoad());
            });
        }); 
        crossroads.addRoute('/ViewData', function() {
            enterModel('clews');
            let version = beginView();
            import('../App/Controller/ViewData.js')
            .then(ViewData => {
                loadView(version, 'App/View/ViewData.html', 'ViewData', () => ViewData.default.onLoad());
            });
        });
        crossroads.addRoute('/LegacyImport', function() {
            enterModel('clews');
            let version = beginView();
            import('../App/Controller/LegacyImport.js')
            .then(ViewData => {
                loadView(version, 'App/View/LegacyImport.html', 'LegacyImport', () => ViewData.default.onLoad());
            });
        });
        crossroads.addRoute('/OGCore', function() {
            enterModel('og');
            let version = beginView();
            import('../App/Controller/OGCore.js')
            .then(OGCore => {
                loadView(version, 'App/View/OGCore.html', 'OGCore', () => OGCore.default.onLoad());
            });
        });
        crossroads.addRoute('/OGCases', function() {
            if (!requireWorkspace()) return;
            enterWorkspace();
            let version = beginView();
            import('../App/Controller/OGCases.js')
            .then(OGCases => {
                loadView(version, 'App/View/OGCases.html', 'OGCases', () => OGCases.default.onLoad());
            });
        });
        crossroads.addRoute('/OGParameters', function() {
            if (!requireWorkspace()) return;
            enterWorkspace();
            let version = beginView();
            import('../App/Controller/OGParameters.js')
            .then(OGParameters => {
                loadView(version, 'App/View/OGParameters.html', 'OGParameters', () => OGParameters.default.onLoad());
            });
        });
        crossroads.addRoute('/OGRuns', function() {
            if (!requireWorkspace()) return;
            enterWorkspace();
            let sourcePage = localStorage.getItem('osy-pageId');
            let version = beginView();
            import('../App/Controller/OGRuns.js')
            .then(OGRuns => {
                loadView(version, 'App/View/OGRuns.html', 'OGRuns', () => OGRuns.default.onLoad(sourcePage));
            });
        });
        //dynamic routes
        function addAppRoute(group, id){
            return crossroads.addRoute(`/${group}/${id}`, function() {
                enterModel('clews');
                let version = beginView();
                import(`../App/Controller/${group}.js`)
                .then(f => {
                    loadView(version, `App/View/${group}.html`, group, () => f.default.onLoad(group, id));
                });
            });
        }
        $.each(model.PARAMETERS, function (param, array) {                    
            $.each(array, function (id, obj) {
                addAppRoute(param, obj.id)
            });
        });
        crossroads.addRoute('/DataFile', function() {
            enterModel('clews');
            let version = beginView();
            import('../App/Controller/DataFile.js')
            .then(DataFile => {
                loadView(version, 'App/View/DataFile.html', 'DataFile', () => DataFile.default.onLoad());
            });
        });
        crossroads.addRoute('/ModelFile', function() {
            enterModel('clews');
            let version = beginView();
            import('../App/Controller/ModelFile.js')
            .then(ModelFile => {
                loadView(version, 'App/View/ModelFile.html', 'ModelFile', () => ModelFile.default.onLoad());
            });
        });
        crossroads.addRoute('/Versions', function() {
            let version = beginView();
            loadView(version, 'App/View/Versions.html', 'Versions');
        });
        crossroads.addRoute('/Pivot', function() {
            enterModel('clews');
            let version = beginView();
            import('../AppResults/Controller/Pivot.js')
            .then(Pivot => {
                loadView(version, 'AppResults/View/Pivot.html', 'Pivot', () => Pivot.default.onLoad());
            });
        });
        crossroads.addRoute('/RESViewer', function() {
            enterModel('clews');
            let version = beginView();
            import('../App/Controller/RESViewer.js')
            .then(RESViewer => {
                loadView(version, 'App/View/RESViewer.html', 'RESViewer', () => RESViewer.default.onLoad());
            });
        });
        crossroads.addRoute('/RESViewerMermaid', function() {
            enterModel('clews');
            let version = beginView();
            import('../App/Controller/RESViewerMermaid.js')
            .then(RESViewer => {
                loadView(version, 'App/View/RESViewerMermaid.html', 'RESViewerMermaid', () => RESViewer.default.onLoad());
            });
        });

        crossroads.bypassed.add(function(request) {
            console.error(request + ' seems to be a dead end...');
        });
        //setup hasher
        hasher.init(); //start listening for history change 
        let acceptedHash = window.location.hash;
        let ignoreNextHashChange = false;
        let navigationPending = false;
        function routeFromHash(hash){
            return hash && hash.length > 0 ? hash.split('#').pop() : '/';
        }
        let entryReconcile = OGWorkspace.reconcileEntry(routeFromHash(acceptedHash));
        function restoreAcceptedHash(clearModelRequest = true){
            if (clearModelRequest) requestedModel = null;
            if (window.location.hash !== acceptedHash) {
                ignoreNextHashChange = true;
                window.location.hash = acceptedHash;
            }
        }
        //Listen to hash changes
        window.addEventListener("hashchange", function(event) {
            // Ignore the hash change used to restore the current page
            if (ignoreNextHashChange) {
                ignoreNextHashChange = false;
                return;
            }
            if (navigationPending) {
                restoreAcceptedHash(false);
                return;
            }

            // Read the URL that raised this event. A second navigation can update
            // window.location before the first hashchange callback runs; using the
            // live value would then replace the original, already-confirmed intent.
            var hash = event && event.newURL !== undefined
                ? new URL(event.newURL).hash
                : window.location.hash;
            var route = routeFromHash(hash);
            let currentRoute = routeFromHash(acceptedHash);
            let modelRequest = requestedModel;

            navigationPending = true;
            Promise.resolve(NavigationGuard.requestLeave(
                async () => {
                    if (entryReconcile){
                        await entryReconcile;
                        entryReconcile = null;
                    }
                    if (OGWorkspace.isWorkspaceRoute(currentRoute) && !OGWorkspace.isWorkspaceRoute(route)){
                        let left = await OGWorkspace.leave();
                        if (!left){
                            restoreAcceptedHash();
                            return false;
                        }
                    }
                    if (window.location.hash !== hash) {
                        ignoreNextHashChange = true;
                        window.location.hash = hash;
                    }
                    if (modelRequest) requestedModel = modelRequest;
                    acceptedHash = hash;
                    crossroads.parse(route);
                    return true;
                },
                restoreAcceptedHash
            )).finally(() => { navigationPending = false; });
        });
        // trigger hashchange on first page load
        window.dispatchEvent(new CustomEvent("hashchange"));
    }
}

MuiogoShell.applyModel();
Routes.Load();
