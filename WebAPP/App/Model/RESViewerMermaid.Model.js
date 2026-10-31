import { DataModel } from "../../Classes/DataModel.Class.js";

export class Model {
    
    constructor (casename, genData, RYTCMdata) {

        let ActivityComms = DataModel.activityComms(genData);
        let TechNames = DataModel.TechName(genData);
        let CommNames = DataModel.CommName(genData);

        let index = 0;
        let labelIndex = {};
        let color = [];
        let label = [];

        $.each(ActivityComms, function (IO, obj) {
            $.each(obj, function (tech, array) {
                if (typeof labelIndex[tech] === "undefined" ){
                    labelIndex[tech] = index;
                    index++;
                }
            });
        });

        let IAR = RYTCMdata.IAR.SC_0;
        let OAR = RYTCMdata.OAR.SC_0;

        let graphString = 'graph LR \n';

        $.each(OAR, function (idOAR, objOAR) {
            $.each(IAR, function (idIAR, objIAR) {
                if(objOAR.CommId == objIAR.CommId && objOAR.MoId == 1 && objIAR.MoId == 1){
                    graphString += `${labelIndex[objOAR.TechId]}[${TechNames[objOAR.TechId]}] -- ${CommNames[objIAR.CommId]} --> ${labelIndex[objIAR.TechId]}[${TechNames[objIAR.TechId]}] \n`;
                }
            });
        });

        this.casename = casename; 
        this.graphString = graphString;
    }
}