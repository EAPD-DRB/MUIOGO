export class Model {
    constructor (PARAMETERS, VARIABLES, genData, RESULTEXISTS) { 

      if(genData){
        this.menu = true;
        this.ResultsMenu = RESULTEXISTS;
        this.PARAMETERS = PARAMETERS;
        this.VARIABLES = VARIABLES;
        let techs = genData['osy-tech'];
        let stgs = genData['osy-stg'];
        let constraints = genData['osy-constraints'];

        let menuCondition = {}
        let menuGroup = ['IAR', 'OAR', 'EAR', 'INCR', 'ITCR', 'CCM', 'CNCM', 'CAM', 'UCC', 'OLS', 'SLS', 'CCS', 'RSC', 'MSC', 'TTS', 'TFS', 'DS','DIDT'];

        menuCondition.IAR = false;
        menuCondition.OAR = false;
        menuCondition.INCR = false;
        menuCondition.ITCR = false;
        menuCondition.EAR = false;
        menuCondition.CM = false;
        menuCondition.STG = false;

        if(stgs.length != 0 && stgs != undefined){
          menuCondition.STG = true;
        }

        $.each(techs, function (id, obj) {
          if(obj.IAR.length != 0 && obj.OAR.length != 0 && obj.EAR.length != 0 && obj.INCR.length != 0 && obj.ITCR.length != 0){
            menuCondition.IAR = true;
            menuCondition.OAR = true;
            menuCondition.INCR = true;
            menuCondition.ITCR = true;
            menuCondition.EAR = true;
            return false;
          }
          if(obj.IAR.length != 0 && obj.IAR != undefined){
            menuCondition.IAR = true;
          }
          if(obj.OAR.length != 0 && obj.OAR != undefined){
            menuCondition.OAR = true;
          }
          if(obj.INCR.length != 0 && obj.INCR != undefined){
            menuCondition.INCR = true;
          }
          if(obj.ITCR.length != 0 && obj.ITCR != undefined){
            menuCondition.ITCR = true;
          }
          if(obj.EAR.length != 0 && obj.EAR != undefined){
            menuCondition.EAR = true;
          }
        }); 

        $.each(constraints, function (id, obj) {
          if(obj.CM.length != 0){
            menuCondition.CM = true;
            return false;
          }
        });
 
        this.menuCondition = menuCondition;
        this.menuGroup = menuGroup;
      }else{
        this.menu = false;
        this.menuCondition = false;
      }
    }
}
