import { Base } from "./Base.Class.js";

export class SyncS3 {

    static updateSync(casename, file) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url:Base.apiUrl() + "updateSync",
                async: true,  
                type: 'POST',
                dataType: 'json',
                data: JSON.stringify({ "casename": casename, "file": file }),
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
    
    static updateSyncParamFile() {
        return new Promise((resolve, reject) => {
            $.ajax({
                url:Base.apiUrl() + "updateSyncParamFile",
                async: true,  
                type: 'GET',
                dataType: 'json',
                contentType: 'application/json; charset=utf-8',
                //credentials: 'include',
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

    static uploadSync(casename) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url:Base.apiUrl() + "uploadSync",
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

    static deleteSync(casename) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url:Base.apiUrl() + "deleteSync",
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

    static deleteResultsPreSync(casename) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url:Base.apiUrl() + "deleteResultsPreSync",
                async: true,  
                type: 'POST',
                data: JSON.stringify({ "casename": casename }),
                dataType: 'json',
                contentType: 'application/json; charset=utf-8',
                success: function (result) {            
                    resolve(result);
                },
                error: function(xhr, status, error) {
                    //custom exception
                    if(error == 'UNKNOWN'){ error =  xhr.responseJSON.message }
                    reject(error);
                }
            });
        });
    }
}