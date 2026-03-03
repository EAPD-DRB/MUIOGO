/**
 * Shared ModelRegistry accessor.
 *
 * Both Routes.Class.js and Sidebar.js need the model registry.
 * This module fetches and caches it once so every consumer shares
 * the same Promise / cached object.
 */

let _registryCache = null;

/**
 * Fetch the model registry from DataStorage/ModelRegistry.json.
 * The result is cached after the first successful fetch.
 * @returns {Promise<Object>} the full registry object
 */
export function getModelRegistry() {
    if (_registryCache) return Promise.resolve(_registryCache);
    return fetch('DataStorage/ModelRegistry.json')
        .then(r => r.json())
        .then(registry => { _registryCache = registry; return registry; });
}

/**
 * Return the registry entry for a given model type key.
 * Returns null when the registry has not been loaded yet or the key
 * does not exist.
 * @param {string} modelType – e.g. "osemosys", "ogcore"
 * @returns {Object|null}
 */
export function getModelConfig(modelType) {
    if (!_registryCache) return null;
    return _registryCache[modelType] || null;
}
