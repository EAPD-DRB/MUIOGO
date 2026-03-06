import { Base } from "./Base.Class.js";

export class Osemosys {
    
    static getParamFile(dataJson='Parameters.json') {
        return new Promise((resolve, reject) => {
            $.ajax({
                url:Base.apiUrl() + "getParamFile",
                async: true,  
                type: 'POST',
                dataType: 'json',
                cache: false,
                data: JSON.stringify({ "dataJson": dataJson }),
                contentType: 'application/json; charset=utf-8',
                success: function (result) {            
                    resolve(result);
                },
                error: function(xhr, status, error) {
                    if(error == 'UNKNOWN'){ error =  xhr.responseJSON.message }
                    reject(error);
                }
            });
        });
    }
    
    static saveParamFile(ParamData, VarData) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url:Base.apiUrl() + "saveParamFile",
                async: true,  
                type: 'POST',
                cache:false,
                dataType: 'json',
                data: JSON.stringify({ "ParamData": ParamData, "VarData": VarData }),
                contentType: 'application/json; charset=utf-8',
                success: function (result) {             
                    resolve(result);
                },
                error: function(xhr, status, error) {
                    if(error == 'UNKNOWN'){ error =  xhr.responseJSON.message }
                    reject(error);
                }
            });
        });
    }

    static saveScOrder(data, casename) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url:Base.apiUrl() + "saveScOrder",
                async: true,  
                type: 'POST',
                dataType: 'json',
                data: JSON.stringify({ "data": data, "casename": casename }),
                contentType: 'application/json; charset=utf-8',
                success: function (result) {             
                    resolve(result);
                },
                error: function(xhr, status, error) {
                    if(error == 'UNKNOWN'){ error =  xhr.responseJSON.message }
                    reject(error);
                }
            });
        });
    }

    static saveCase(data) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url:Base.apiUrl() + "saveCase",
                async: true,  
                type: 'POST',
                dataType: 'json',
                data: JSON.stringify({ "data": data }),
                contentType: 'application/json; charset=utf-8',
                // credentials: 'include',
                // xhrFields: { withCredentials: true},
                // crossDomain: true,
                success: function (result) {             
                    resolve(result);
                },
                error: function(xhr, status, error) {
                    if(error == 'UNKNOWN'){ error =  xhr.responseJSON.message }
                    reject(error);
                }
            });
        });
    }

    static saveView(casename, data, param) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url:Base.apiUrl() + "saveView",
                async: true,  
                type: 'POST',
                dataType: 'json',
                data: JSON.stringify({ "casename": casename, "data": data, "param": param }),
                contentType: 'application/json; charset=utf-8',
                success: function (result) {             
                    resolve(result);
                },
                error: function(xhr, status, error) {
                    if(error == 'UNKNOWN'){ error =  xhr.responseJSON.message }
                    reject(error);
                }
            });
        });
    }

    static updateViews(casename, data, param) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url:Base.apiUrl() + "updateViews",
                async: true,  
                type: 'POST',
                dataType: 'json',
                data: JSON.stringify({ "casename": casename, "data": data, "param": param }),
                contentType: 'application/json; charset=utf-8',
                success: function (result) {             
                    resolve(result);
                },
                error: function(xhr, status, error) {
                    if(error == 'UNKNOWN'){ error =  xhr.responseJSON.message }
                    reject(error);
                }
            });
        });
    }

    static generateDataFile(casename, caserunname) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url:Base.apiUrl() + "generateDataFile",
                async: true,  
                type: 'POST',
                dataType: 'json',
                data: JSON.stringify({ "casename": casename, 'caserunname': caserunname }),
                contentType: 'application/json; charset=utf-8',
                // credentials: 'include',
                // xhrFields: { withCredentials: true},
                // crossDomain: true,
                success: function (result) {             
                    resolve(result);
                },
                error: function(xhr, status, error) {
                    if(error == 'UNKNOWN'){ error =  xhr.responseJSON.message }
                    reject(error);
                }
            });
        });
    }

    static createCaseRun(casename, caserunname, data) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url:Base.apiUrl() + "createCaseRun",
                async: true,  
                type: 'POST',
                dataType: 'json',
                data: JSON.stringify({ "casename": casename, 'caserunname': caserunname, 'data': data }),
                contentType: 'application/json; charset=utf-8',
                // credentials: 'include',
                // xhrFields: { withCredentials: true},
                // crossDomain: true,
                success: function (result) {             
                    resolve(result);
                },
                error: function(xhr, status, error) {
                    if(error == 'UNKNOWN'){ error =  xhr.responseJSON.message }
                    reject(error);
                }
            });
        });
    }

    static deleteScenarioCaseRuns(casename, scenarioId) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url:Base.apiUrl() + "deleteScenarioCaseRuns",
                async: true,  
                type: 'POST',
                dataType: 'json',
                data: JSON.stringify({ "casename": casename,"scenarioId": scenarioId }),
                contentType: 'application/json; charset=utf-8',
                success: function (result) {             
                    resolve(result);
                },
                error: function(xhr, status, error) {
                    if(error == 'UNKNOWN'){ error =  xhr.responseJSON.message }
                    reject(error);
                }
            });
        });
    }

    static updateCaseRun(casename, caserunname, oldcaserunname, data) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url:Base.apiUrl() + "updateCaseRun",
                async: true,  
                type: 'POST',
                dataType: 'json',
                data: JSON.stringify({ "casename": casename, 'caserunname': caserunname, 'oldcaserunname': oldcaserunname, 'data': data }),
                contentType: 'application/json; charset=utf-8',
                // credentials: 'include',
                // xhrFields: { withCredentials: true},
                // crossDomain: true,
                success: function (result) {             
                    resolve(result);
                },
                error: function(xhr, status, error) {
                    if(error == 'UNKNOWN'){ error =  xhr.responseJSON.message }
                    reject(error);
                }
            });
        });
    }

    static run(casename, solver, caserunname) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url:Base.apiUrl() + "run",
                async: true,  
                type: 'POST',
                dataType: 'json',
                data: JSON.stringify({ "casename": casename, "solver": solver, 'caserunname': caserunname  }),
                contentType: 'application/json; charset=utf-8',
                // credentials: 'include',
                // xhrFields: { withCredentials: true},
                // crossDomain: true,
                success: function (result) {             
                    resolve(result);
                },
                error: function(xhr, status, error) {
                    console.log("xhr, status, error ", xhr, status, error )
                    if(error == 'UNKNOWN'){ error =  xhr.responseJSON.message }
                    reject(error);
                }
            });
        });
    }

    static batchRun(modelname, cases, solver="cbc") {
        return new Promise((resolve, reject) => {
            $.ajax({
                url:Base.apiUrl() + "batchRun",
                async: true,  
                type: 'POST',
                dataType: 'json',
                data: JSON.stringify({ "modelname": modelname, 'cases': cases, "solver": solver  }),
                contentType: 'application/json; charset=utf-8',
                // credentials: 'include',
                // xhrFields: { withCredentials: true},
                // crossDomain: true,
                success: function (result) {             
                    resolve(result);
                },
                error: function(xhr, status, error) {
                    console.log("xhr, status, error ", xhr, status, error )
                    if(error == 'UNKNOWN'){ error =  xhr.responseJSON.message }
                    reject(error);
                }
            });
        });
    }

    static cleanUp(modelname) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url:Base.apiUrl() + "cleanUp",
                async: true,  
                type: 'POST',
                dataType: 'json',
                data: JSON.stringify({ "modelname": modelname }),
                contentType: 'application/json; charset=utf-8',
                // credentials: 'include',
                // xhrFields: { withCredentials: true},
                // crossDomain: true,
                success: function (result) {             
                    resolve(result);
                },
                error: function(xhr, status, error) {
                    console.log("xhr, status, error ", xhr, status, error )
                    if(error == 'UNKNOWN'){ error =  xhr.responseJSON.message }
                    reject(error);
                }
            });
        });
    }

    static readDataFile(casename, caserunname) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url:Base.apiUrl() + "readDataFile",
                async: true,  
                type: 'POST',
                dataType: 'json',
                data: JSON.stringify({ "casename": casename, 'caserunname': caserunname }),
                contentType: 'application/json; charset=utf-8',
                // credentials: 'include',
                // xhrFields: { withCredentials: true},
                // crossDomain: true,
                success: function (result) {             
                    resolve(result);
                },
                error: function(xhr, status, error) {
                    if(error == 'UNKNOWN'){ error =  xhr.responseJSON.message }
                    reject(error);
                }
            });
        });
    }

    static validateInputs(casename, caserunname) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url:Base.apiUrl() + "validateInputs",
                async: true,  
                type: 'POST',
                dataType: 'json',
                data: JSON.stringify({ "casename": casename, 'caserunname': caserunname }),
                contentType: 'application/json; charset=utf-8',
                // credentials: 'include',
                // xhrFields: { withCredentials: true},
                // crossDomain: true,
                success: function (result) {             
                    resolve(result);
                },
                error: function(xhr, status, error) {
                    if(error == 'UNKNOWN'){ error =  xhr.responseJSON.message }
                    reject(error);
                }
            });
        });
    }

    static resultsExists(casename) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url:Base.apiUrl() + "resultsExists",
                async: true,  
                type: 'POST',
                dataType: 'json',
                data: JSON.stringify({"casename": casename }),
                contentType: 'application/json; charset=utf-8',
                success: function (result) {            
                    resolve(result);
                },
                error: function(xhr, status, error) {
                    if(error == 'UNKNOWN'){ error =  xhr.responseJSON.message }
                    reject(error);
                }
            });
        });
    }

    // static getData(casename, dataJson) {
    //     return fetch('../../DataStorage/'+casename+'/'+dataJson, {cache: "no-store"})  // return this promise
    //     .then(response => response.json())
    //     .catch(error => error);
    // }

    // static getData(casename, dataJson) {
    //     // return fetch('../../DataStorage/'+casename+'/'+dataJson, {cache: "no-store"})
    //     // .then(response => response.json())
    //     // .catch(error => error);

    //     return fetch('../../DataStorage/'+casename+'/'+dataJson, {cache: "no-store"}) 
    //         .then((response) => {
    //             if (response.ok) {
    //                 //console.log('response1 ', response)
    //                 //console.log('data ', response.json())
    //             return response;
    //             }
    //             throw new Error('No casename selecetd');
    //         })
    //         .then(response => response.json())
    //         .catch(error => null);
    // }

    static getData(casename, dataJson) {
        if (!casename || casename === "null") {
            console.warn("getData called without valid casename");
            return Promise.resolve(null);
        }
        return fetch('../../DataStorage/'+casename+'/'+dataJson, {cache: "no-store"}) 
            .then((response) => {
                if (response.ok) {
                    return response;
                }
                throw new Error('Invalid casename');
            })
            .then(response => response.json())
            .catch(error => null);
    }

    static getData_(casename, dataJson) {
        return  fetch('../../DataStorage/'+casename+'/'+dataJson, {cache: "no-store"})
        .then((response) => {
            if (response.status !== 200) {
              //console.log('Looks like there was a problem. Status Code: ' + response.status);
              return response;
            }
            // Examine the text in the response
            response.json().then(function(data) {
              //console.log(data);
            });
        })
        .then(response => response.json())
        .catch(function(err) {
          //console.log('Fetch Error :-S', err);
        });
    }

    // static getResultData(casename, dataJson) {
    //     // return new Promise((resolve, reject) => {
    //     //     fetch('../../DataStorage/'+casename+'/view/' +dataJson, {cache: "no-store"})
    //     //     .then(DATA => {
    //     //         DATA = DATA.json();
    //     //         resolve(DATA);
    //     //     })
    //     //     .catch(error => {
    //     //         if(error == 'UNKNOWN'){ error =  xhr.responseJSON.message }
    //     //         reject(error);
    //     //     });
    //     // });

    //     return fetch('../../DataStorage/'+casename+'/view/' +dataJson, {cache: "no-store"})
    //         .then((response) => {
    //             if (response.ok) {
    //                 //console.log('response1 ', response)
    //                 return response;
    //             }
    //             throw new Error('No casename selecetd');
    //         })
    //         .then(response =>  response.json())
    //         .catch(error => null);
    // }

    static getResultData(casename, dataJson) {
        if (!casename || casename === "null") {
            console.warn("getResultData called without valid casename");
            return Promise.resolve(null);
        }
        return fetch('../../DataStorage/'+casename+'/view/' +dataJson, {cache: "no-store"})
            .then((response) => {
                if (response.ok) {
                    return response;
                }
                throw new Error('Invalid casename');
            })
            .then(response => response.json())
            .catch(error => null);
    }

    static updateData(data, param, dataJson) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url:Base.apiUrl() + "updateData",
                async: true,  
                type: 'POST',
                dataType: 'json',
                data: JSON.stringify({ "data": data, "param": param, "dataJson": dataJson }),
                contentType: 'application/json; charset=utf-8',
                success: function (result) {             
                    resolve(result);
                },
                error: function(xhr, status, error) {
                    if(error == 'UNKNOWN'){ error =  xhr.responseJSON.message }
                    reject(error);
                }
            });
        });
    }

    static viewData(casename) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url:Base.apiUrl() + "viewData",
                async: true,  
                type: 'POST',
                dataType: 'json',
                data: JSON.stringify({ "casename": casename }),
                contentType: 'application/json; charset=utf-8',
                success: function (result) {             
                    resolve(result);
                },
                error: function(xhr, status, error) {
                    if(error == 'UNKNOWN'){ error =  xhr.responseJSON.message }
                    reject(error);
                }
            });
        });
    }

    // static viewData(casename) {
    //     return fetch(Base.apiUrl() + "viewData", {
    //         cache: "no-store",
    //         method: 'POST',
    //         headers: {
    //             'Accept': 'application/json',
    //             'Content-Type': 'application/json'
    //           },
    //         body: JSON.stringify({ "casename": casename })
    //     })  // return this promise
    //     .then(response => response.json())
    //     .catch(error => error);
    // }


    static viewTEData(casename) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url:Base.apiUrl() + "viewTEData",
                async: true,  
                type: 'POST',
                dataType: 'json',
                data: JSON.stringify({ "casename": casename }),
                contentType: 'application/json; charset=utf-8',
                success: function (result) {             
                    resolve(result);
                },
                error: function(xhr, status, error) {
                    if(error == 'UNKNOWN'){ error =  xhr.responseJSON.message }
                    reject(error);
                }
            });
        });
    }

    static updateViewData(casename, year, ScId, groupId, paramId, TechId, CommId, EmisId, Timeslice, value) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url:Base.apiUrl() + "updateViewData",
                async: true,  
                type: 'POST',
                dataType: 'json',
                data: JSON.stringify({ "casename": casename, year: year, ScId: ScId,
                 groupId: groupId, paramId: paramId, TechId: TechId, CommId: CommId, EmisId:EmisId, Timeslice: Timeslice, value: value}),
                contentType: 'application/json; charset=utf-8',
                success: function (result) {             
                    resolve(result);
                },
                error: function(xhr, status, error) {
                    if(error == 'UNKNOWN'){ error =  xhr.responseJSON.message }
                    reject(error);
                }
            });
        });
    }

    static updateTEViewData(casename, ScId, GroupId, ParamId, TechId, EmisId, value) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url:Base.apiUrl() + "updateTEViewData",
                async: true,  
                type: 'POST',
                dataType: 'json',
                data: JSON.stringify({ "casename": casename, scId:ScId,
                 groupId: GroupId, paramId: ParamId, techId: TechId, emisId: EmisId, value: value}),
                contentType: 'application/json; charset=utf-8',
                success: function (result) {             
                    resolve(result);
                },
                error: function(xhr, status, error) {
                    if(error == 'UNKNOWN'){ error =  xhr.responseJSON.message }
                    reject(error);
                }
            });
        });
    }

    static importTemplate(data) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url:Base.apiUrl() + "importTemplate",
                async: true,  
                type: 'POST',
                dataType: 'json',
                data: JSON.stringify({"data": data }),
                contentType: 'application/json; charset=utf-8',
                success: function (result) {             
                    resolve(result);
                },
                error: function(xhr, status, error) {
                    if(error == 'UNKNOWN'){ error =  xhr.responseJSON.message }
                    reject(error);
                }
            });
        });
    }
}