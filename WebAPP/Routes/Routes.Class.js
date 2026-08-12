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
            $('#content').html('<h1 class="ajax-loading-animation"><i class="fa fa-cog fa-spin"></i> Loading...</h1>');
            if (selected == 'og'){
                import('../App/Controller/OGCore.js')
                .then(OGCore => {
                    $( ".osy-content" ).load( 'App/View/OGCore.html', function() {
                        localStorage.setItem("osy-pageId", "OGCore");
                        OGCore.default.onLoad();
                    });
                });
            }else if (selected == 'clews'){
                import('../App/Controller/Home.js')
                .then(Home => {
                    $( ".osy-content" ).load( 'App/View/Home.html', function() {
                        localStorage.setItem("osy-pageId", "Home");
                        Home.default.onLoad();
                    });
                });
            }else{
                $( ".osy-content" ).load( 'App/View/ModelPick.html', function() {
                    localStorage.setItem("osy-pageId", "ModelPick");
                });
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
            $('#content').html('<h1 class="ajax-loading-animation"><i class="fa fa-cog fa-spin"></i> Loading...</h1>');
            import('../App/Controller/Config.js')
            .then(Config => {
                $( ".osy-content" ).load( 'App/View/Config.html', function() {
                    localStorage.setItem("osy-pageId", "Config");
                    Config.default.onLoad();
                });
            });
        });  
        crossroads.addRoute('/AddCase', function() {
            enterModel('clews');
            $('#content').html('<h1 class="ajax-loading-animation"><i class="fa fa-cog fa-spin"></i> Loading...</h1>');
            import('../App/Controller/AddCase.js')
            .then(AddCase => {
                $( ".osy-content" ).load( 'App/View/AddCase.html', function() {
                    localStorage.setItem("osy-pageId", "AddCase");
                    AddCase.default.onLoad();
                });
            });
        }); 
        crossroads.addRoute('/ViewData', function() {
            enterModel('clews');
            $('#content').html('<h1 class="ajax-loading-animation"><i class="fa fa-cog fa-spin"></i> Loading...</h1>');
            import('../App/Controller/ViewData.js')
            .then(ViewData => {
                $( ".osy-content" ).load( 'App/View/ViewData.html', function() {
                    localStorage.setItem("osy-pageId", "ViewData");
                    ViewData.default.onLoad();
                });
            });
        });
        crossroads.addRoute('/LegacyImport', function() {
            enterModel('clews');
            $('#content').html('<h1 class="ajax-loading-animation"><i class="fa fa-cog fa-spin"></i> Loading...</h1>');
            import('../App/Controller/LegacyImport.js')
            .then(ViewData => {
                $( ".osy-content" ).load( 'App/View/LegacyImport.html', function() {
                    localStorage.setItem("osy-pageId", "LegacyImport");
                    ViewData.default.onLoad();
                });
            });
        });
        crossroads.addRoute('/OGCore', function() {
            enterModel('og');
            $('#content').html('<h1 class="ajax-loading-animation"><i class="fa fa-cog fa-spin"></i> Loading...</h1>');
            import('../App/Controller/OGCore.js')
            .then(OGCore => {
                $( ".osy-content" ).load( 'App/View/OGCore.html', function() {
                    localStorage.setItem("osy-pageId", "OGCore");
                    OGCore.default.onLoad();
                });
            });
        });
        crossroads.addRoute('/OGCases', function() {
            if (!requireWorkspace()) return;
            enterWorkspace();
            $('#content').html('<h1 class="ajax-loading-animation"><i class="fa fa-cog fa-spin"></i> Loading...</h1>');
            import('../App/Controller/OGCases.js')
            .then(OGCases => {
                $( ".osy-content" ).load( 'App/View/OGCases.html', function() {
                    localStorage.setItem("osy-pageId", "OGCases");
                    OGCases.default.onLoad();
                });
            });
        });
        crossroads.addRoute('/OGParameters', function() {
            if (!requireWorkspace()) return;
            enterWorkspace();
            $('#content').html('<h1 class="ajax-loading-animation"><i class="fa fa-cog fa-spin"></i> Loading...</h1>');
            import('../App/Controller/OGParameters.js')
            .then(OGParameters => {
                $( ".osy-content" ).load( 'App/View/OGParameters.html', function() {
                    localStorage.setItem("osy-pageId", "OGParameters");
                    OGParameters.default.onLoad();
                });
            });
        });
        crossroads.addRoute('/OGRuns', function() {
            if (!requireWorkspace()) return;
            enterWorkspace();
            let sourcePage = localStorage.getItem('osy-pageId');
            $('#content').html('<h1 class="ajax-loading-animation"><i class="fa fa-cog fa-spin"></i> Loading...</h1>');
            import('../App/Controller/OGRuns.js')
            .then(OGRuns => {
                $( ".osy-content" ).load( 'App/View/OGRuns.html', function() {
                    localStorage.setItem("osy-pageId", "OGRuns");
                    OGRuns.default.onLoad(sourcePage);
                });
            });
        });
        //dynamic routes
        function addAppRoute(group, id){
            return crossroads.addRoute(`/${group}/${id}`, function() {
                enterModel('clews');
                $('#content').html('<h1 class="ajax-loading-animation"><i class="fa fa-cog fa-spin"></i> Loading...</h1>');
                import(`../App/Controller/${group}.js`)
                .then(f => {
                    $( ".osy-content" ).load( `App/View/${group}.html`, function() {
                        localStorage.setItem("osy-pageId", `${group}`);
                        f.default.onLoad(group, id);
                    });
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
            $('#content').html('<h1 class="ajax-loading-animation"><i class="fa fa-cog fa-spin"></i> Loading...</h1>');
            import('../App/Controller/DataFile.js')
            .then(DataFile => {
                $( ".osy-content" ).load( 'App/View/DataFile.html', function() {
                    localStorage.setItem("osy-pageId", "DataFile");
                    DataFile.default.onLoad();
                });
            });
        });
        crossroads.addRoute('/ModelFile', function() {
            enterModel('clews');
            $('#content').html('<h1 class="ajax-loading-animation"><i class="fa fa-cog fa-spin"></i> Loading...</h1>');
            import('../App/Controller/ModelFile.js')
            .then(ModelFile => {
                $( ".osy-content" ).load( 'App/View/ModelFile.html', function() {
                    localStorage.setItem("osy-pageId", "ModelFile");
                    ModelFile.default.onLoad();
                });
            });
        });
        crossroads.addRoute('/Versions', function() {
            $('#content').html('<h1 class="ajax-loading-animation"><i class="fa fa-cog fa-spin"></i> Loading...</h1>');
            $( ".osy-content" ).load( 'App/View/Versions.html');
            localStorage.setItem("osy-pageId", "Versions");
        });
        crossroads.addRoute('/Pivot', function() {
            enterModel('clews');
            $('#content').html('<h1 class="ajax-loading-animation"><i class="fa fa-cog fa-spin"></i> Loading...</h1>');
            import('../AppResults/Controller/Pivot.js')
            .then(Pivot => {
                $( ".osy-content" ).load( 'AppResults/View/Pivot.html', function() {
                    localStorage.setItem("osy-pageId", "Pivot");
                    Pivot.default.onLoad();
                });
            });
        });
        crossroads.addRoute('/RESViewer', function() {
            enterModel('clews');
            $('#content').html('<h1 class="ajax-loading-animation"><i class="fa fa-cog fa-spin"></i> Loading...</h1>');
            import('../App/Controller/RESViewer.js')
            .then(RESViewer => {
                $( ".osy-content" ).load( 'App/View/RESViewer.html', function() {
                    localStorage.setItem("osy-pageId", "RESViewer");
                    RESViewer.default.onLoad();
                });
            });
        });
        crossroads.addRoute('/RESViewerMermaid', function() {
            enterModel('clews');
            $('#content').html('<h1 class="ajax-loading-animation"><i class="fa fa-cog fa-spin"></i> Loading...</h1>');
            import('../App/Controller/RESViewerMermaid.js')
            .then(RESViewer => {
                $( ".osy-content" ).load( 'App/View/RESViewerMermaid.html', function() {
                    localStorage.setItem("osy-pageId", "RESViewerMermaid");
                    RESViewer.default.onLoad();
                });
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
        function restoreAcceptedHash(clearModelRequest = true){
            if (clearModelRequest) requestedModel = null;
            if (window.location.hash !== acceptedHash) {
                ignoreNextHashChange = true;
                window.location.hash = acceptedHash;
            }
        }
        //Listen to hash changes
        window.addEventListener("hashchange", function() {
            // Ignore the hash change used to restore the current page
            if (ignoreNextHashChange) {
                ignoreNextHashChange = false;
                return;
            }
            if (navigationPending) {
                restoreAcceptedHash(false);
                return;
            }

            var hash = window.location.hash;
            var route = routeFromHash(hash);
            let currentRoute = routeFromHash(acceptedHash);
            let modelRequest = requestedModel;

            navigationPending = true;
            Promise.resolve(NavigationGuard.requestLeave(
                async () => {
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
