import { Base } from "./Base.Class.js";

export class Ogc {

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
                        || 'The OG-Core service could not be reached.';
                    reject(msg);
                }
            });
        });
    }

    //countries from the installer register, tagged with this machine's
    //install state; also carries catalog_source live | cache | none
    static getCalibrationCatalog() {
        return Ogc._request('GET', 'ogc/getCalibrationCatalog');
    }

    //calibrations on this machine, including custom ones not in the register
    static getInstalledCalibrations() {
        return Ogc._request('GET', 'ogc/getInstalledCalibrations');
    }

    //pre flight for the two custom sources, a local folder or a Git URL
    static checkCalibration(data) {
        return Ogc._request('POST', 'ogc/checkCalibration', data);
    }

    //install from the catalogue or a Git URL, returns an install_id to poll
    static installCalibration(data) {
        return Ogc._request('POST', 'ogc/installCalibration', data);
    }

    //adopt an existing local clone, returns an install_id to poll
    static registerLocalCalibration(data) {
        return Ogc._request('POST', 'ogc/registerLocalCalibration', data);
    }

    //progress of a running install or registration job
    static getInstallStatus(installId) {
        return Ogc._request('GET', 'ogc/getInstallStatus?install_id=' + encodeURIComponent(installId));
    }

    //check_only true compares against upstream, false applies the update
    static refreshCalibration(data) {
        return Ogc._request('POST', 'ogc/refreshCalibration', data);
    }

    //removes MUIOGO's record only, files on disk are kept
    static unregisterCalibration(countryId) {
        return Ogc._request('POST', 'ogc/unregisterCalibration', { country_id: countryId });
    }

    static getCases() {
        return Ogc._request('GET', 'ogc/getCases');
    }

    static getSession() {
        return Ogc._request('GET', 'ogc/getSession');
    }

    static setSession(casename, countryId) {
        let payload = { casename: casename };
        if (countryId !== undefined) payload.country_id = countryId;
        return Ogc._request('POST', 'ogc/setSession', payload);
    }

    static saveCase(data) {
        return Ogc._request('POST', 'ogc/saveCase', {
            data: {
                'ogc-casename': data.casename,
                'ogc-description': data.description || '',
                country_id: data.country_id
            }
        });
    }

    static deleteCase(casename) {
        return Ogc._request('POST', 'ogc/deleteCase', { casename: casename });
    }

    static getRuns(casename) {
        return Ogc._request('POST', 'ogc/getRuns', { casename: casename })
            .then(Ogc.normaliseRuns);
    }

    static createRun(data) {
        let payload = {
            casename: data.casename,
            run_name: data.run_name,
            run_type: data.run_type
        };
        if (data.baseline_run){
            payload.baseline_run_name = data.baseline_run;
        }
        if (data.description){
            payload.description = data.description;
        }
        return Ogc._request('POST', 'ogc/createRun', payload);
    }

    static deleteRun(casename, runName) {
        return Ogc._request('POST', 'ogc/deleteRun', { casename: casename, run_name: runName });
    }

    static getParams(casename, runName) {
        return Ogc._request('POST', 'ogc/getParams', { casename: casename, run_name: runName })
            .then(params => ({ params: params.params || params }));
    }

    static saveParams(casename, runName, params) {
        return Ogc._request('POST', 'ogc/saveParams', {
            casename: casename, run_name: runName, params: params
        });
    }

    static getParameterSchema(casename) {
        return Ogc._request('GET', 'ogc/getParameterSchema?casename=' + encodeURIComponent(casename));
    }

    static run(casename, runName, timePath) {
        return Ogc._request('POST', 'ogc/run', {
            casename: casename,
            run_name: runName,
            time_path: !!timePath
        });
    }

    static getRunStatus(casename, runName) {
        return Ogc._request('POST', 'ogc/getRunStatus', {
            casename: casename,
            run_name: runName
        });
    }

    //Newer backends expose the complete live queue. Callers must still fall
    //back to per-run status because older installations do not have this route.
    static getRunQueue(casename) {
        return Ogc._request('POST', 'ogc/getRunQueue', { casename: casename });
    }

    static cancelRun(casename, runName) {
        return Ogc._request('POST', 'ogc/cancelRun', {
            casename: casename,
            run_name: runName
        });
    }

    static normaliseRuns(response) {
        let raw = response && response.runs ? response.runs : response;
        let list = [];
        if ($.isArray(raw)){
            list = raw;
        }else if (raw){
            $.each(['baseline', 'reform', 'reforms'], function (id, key) {
                let value = raw[key];
                if (!value) return;
                if ($.isArray(value)){
                    list = list.concat(value);
                }else{
                    list.push(value);
                }
            });
        }
        return { runs: $.map(list, function (run) {
            return $.extend({}, run, {
                run_name: run.run_name || run.RunName,
                run_type: run.run_type || run.RunType,
                baseline_run: run.baseline_run || run.baseline_run_name || null
            });
        }) };
    }
}
