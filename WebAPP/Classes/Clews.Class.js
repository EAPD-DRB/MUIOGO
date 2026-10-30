import { Base } from "./Base.Class.js";

//the /clews install layer: install a CLEWs country's cases from its repository
export class Clews {

    static _request(type, path, data) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url: Base.apiUrl() + path,
                async: true,
                type: type,
                dataType: 'json',
                contentType: data ? 'application/json' : undefined,
                data: data ? JSON.stringify(data) : undefined,
                credentials: 'include',
                xhrFields: { withCredentials: true },
                crossDomain: true,
                success: function (result) {
                    resolve(result);
                },
                error: function (xhr) {
                    let msg = (xhr.responseJSON && xhr.responseJSON.message)
                        || 'The CLEWs install service could not be reached.';
                    reject(msg);
                }
            });
        });
    }

    //countries from the register (scripts/clews-repos.json), tagged with this
    //machine's install state; also carries catalog_source live | cache | none
    static getCountryCatalog() {
        return Clews._request('GET', 'clews/getCountryCatalog');
    }

    //every case on this machine with its provenance; hand-added ones are 'unmanaged'
    static getInstalledCountries() {
        return Clews._request('GET', 'clews/getInstalledCountries');
    }

    //read a repository's clews-country.json and return its vintages and cases,
    //nothing downloaded; data is {source_type: 'repo_url', repo_url} or
    //{source_type: 'local_path', local_path}
    static inspectSource(data) {
        return Clews._request('POST', 'clews/inspectSource', data);
    }

    //same source fields plus vintage and cases[], returns an install_id to poll
    static installCountry(data) {
        return Clews._request('POST', 'clews/installCountry', data);
    }

    //progress of a running install
    static getInstallStatus(installId) {
        return Clews._request('GET', 'clews/getInstallStatus?install_id=' + encodeURIComponent(installId));
    }
}
