import { Base } from "./Base.Class.js";

export class Calculate {
    
    static normalizePattern(casename) {
        return new Promise((resolve, reject) => {
            $.ajax({
                url:Base.apiUrl() + "normalizePattern",
                async: true,  
                type: 'POST',
                dataType: 'json',
                data: JSON.stringify({ "casename": casename }),
                dataType: 'json',
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