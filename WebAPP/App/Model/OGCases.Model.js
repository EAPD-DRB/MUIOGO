export class Model {

    constructor (cases, runsByCase, installed, countryId) {
        this.installed = installed || [];
        this.records = {};
        let records = this.records;
        $.each(this.installed, function (id, r) { records[r.country_id] = r; });

        let self = this;
        this.cases = ($.map(cases || [], function (c) {
            if (countryId && c.country_id != countryId){
                return null;
            }
            let runs = self.flattenRuns((runsByCase || {})[c.casename]);
            return {
                casename: c.casename,
                country_id: c.country_id,
                description: c.description || '',
                modified_at: c.modified_at || '',
                has_results: !!c.has_results,
                installed: !!records[c.country_id],
                runs: runs
            };
        }));

        this.countryId = countryId || null;

        this.pageID = 'OGCases';
    }

    flattenRuns(runs){
        if (!runs){
            return [];
        }
        if ($.isArray(runs)){
            return runs;
        }
        let out = [];
        $.each(['baseline', 'reform'], function (id, key) {
            $.each(runs[key] || [], function (rid, r) { out.push(r); });
        });
        $.each(runs, function (key, list) {
            if (key == 'baseline' || key == 'reform' || !$.isArray(list)){
                return;
            }
            $.each(list, function (rid, r) { out.push(r); });
        });
        return out;
    }

    static baselines(runs){
        return $.map(runs || [], function (r) {
            return r.run_type == 'baseline' ? r : null;
        });
    }

    static reformsOf(runs, baselineName){
        return $.map(runs || [], function (r) {
            return (r.run_type == 'reform' && r.baseline_run == baselineName) ? r : null;
        });
    }

    static orphanReforms(runs){
        let names = {};
        $.each(runs || [], function (id, r) {
            if (r.run_type == 'baseline'){ names[r.run_name] = true; }
        });
        return $.map(runs || [], function (r) {
            return (r.run_type == 'reform' && !names[r.baseline_run]) ? r : null;
        });
    }

    static baselineDone(runs, baselineName){
        let done = false;
        $.each(runs || [], function (id, r) {
            if (r.run_type == 'baseline' && r.run_name == baselineName && r.status == 'completed'){
                done = true;
            }
        });
        return done;
    }
}
