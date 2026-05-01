import { Osemosys } from "../../Classes/Osemosys.Class.js";
import { Message } from "../../Classes/Message.Class.js";
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
        //settings 
        import('../App/Controller/Settings.js')
        .then(Settings => {
            $( ".demo" ).load( 'App/View/Settings.html', function() {
                Settings.default.Load();
            });
        });

        //Sidebar.Load(PARAMETERS);
        crossroads.addRoute('/', function() {
            $('#content').html('<h1 class="ajax-loading-animation"><i class="fa fa-cog fa-spin"></i> Loading...</h1>');
            import('../App/Controller/Home.js')
            .then(Home => {
                $( ".osy-content" ).load( 'App/View/Home.html', function() {
                    localStorage.setItem("osy-pageId", "Home");
                    Home.default.onLoad();
                });
            });
        }); 
        crossroads.addRoute('/Config', function() {
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
            $('#content').html('<h1 class="ajax-loading-animation"><i class="fa fa-cog fa-spin"></i> Loading...</h1>');
            import('../App/Controller/LegacyImport.js')
            .then(ViewData => {
                $( ".osy-content" ).load( 'App/View/LegacyImport.html', function() {
                    localStorage.setItem("osy-pageId", "LegacyImport");
                    ViewData.default.onLoad();
                });
            });
        });
        //dynamic routes
        function addAppRoute(group, id){
            return crossroads.addRoute(`/${group}/${id}`, function() {
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
        //Listen to hash changes
        window.addEventListener("hashchange", function() {
            var route = '/';
            var hash = window.location.hash;
            if (hash.length > 0) {
                route = hash.split('#').pop();
            }
            crossroads.parse(route);
        });
        // trigger hashchange on first page load
        window.dispatchEvent(new CustomEvent("hashchange"));
    }
}

Routes.Load();



