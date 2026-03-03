import { Osemosys } from "../../Classes/Osemosys.Class.js";
import { Message } from "../../Classes/Message.Class.js";
import { Model } from "./Routes.Model.js";

export class Routes {
    /** Currently active model-type key (e.g. "osemosys" or "ogcore"). */
    static activeModelType = 'osemosys';

    /** Cached model registry (loaded once from ModelRegistry.json). */
    static _registry = null;

    /**
     * Fetch the model registry.  Caches the result so subsequent calls
     * are free.
     * @returns {Promise<Object>} the full registry object
     */
    static getModelRegistry() {
        if (this._registry) return Promise.resolve(this._registry);
        return fetch('DataStorage/ModelRegistry.json')
            .then(r => r.json())
            .then(registry => { this._registry = registry; return registry; });
    }

    /**
     * Return the registry entry for the currently active model type.
     * @returns {Object} e.g. { label, paramFile, varFile, sidebarGroups, routes, features }
     */
    static getActiveModelConfig() {
        if (!this._registry) return null;
        return this._registry[this.activeModelType] || null;
    }

    /**
     * Switch the active model type and reload routes.
     * @param {string} modelType – key in ModelRegistry.json (e.g. "osemosys")
     */
    static switchModelType(modelType) {
        this.activeModelType = modelType;
        localStorage.setItem('osy-modelType', modelType);
        this.Load();
    }

    static Load(casename) {
        this.getModelRegistry()
        .then(registry => {
            // Restore persisted model type (default to osemosys)
            const saved = localStorage.getItem('osy-modelType');
            if (saved && registry[saved]) {
                this.activeModelType = saved;
            }
            const cfg = this.getActiveModelConfig();
            const paramFile = cfg ? cfg.paramFile : 'Parameters.json';
            const varFile   = cfg ? cfg.varFile   : 'Variables.json';
            return Promise.all([
                Osemosys.getParamFile(paramFile),
                Osemosys.getParamFile(varFile)
            ]);
        })
        .then(([PARAMETERS, VARIABLES]) => {
            let model = new Model(PARAMETERS, VARIABLES);
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
        //dynamic routes – generated from the active model's registry config
        const cfg = this.getActiveModelConfig();
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

        if (cfg && cfg.sidebarGroups) {
            // Use registry sidebarGroups to drive route generation
            $.each(cfg.sidebarGroups, function (idx, group) {
                if (model.PARAMETERS[group]) {
                    $.each(model.PARAMETERS[group], function (id, obj) {
                        addAppRoute(group, obj.id);
                    });
                }
            });
        } else {
            // Fallback: iterate all parameter groups from the model
            $.each(model.PARAMETERS, function (param, array) {                    
                $.each(array, function (id, obj) {
                    addAppRoute(param, obj.id);
                });
            });
        }
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

// Listen for model-type changes from the navbar switcher
window.addEventListener('modelTypeChanged', function(e) {
    if (e.detail && e.detail.modelType) {
        Routes.switchModelType(e.detail.modelType);
    }
});
