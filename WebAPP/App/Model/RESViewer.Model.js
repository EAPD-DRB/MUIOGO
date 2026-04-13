import { DataModel } from "../../Classes/DataModel.Class.js";

export class Model {

    constructor (casename, genData, DemandComms, settings, techSelect=null) {

        let TechIdByName = DataModel.TechIdByName(genData);
        // let CommNames = DataModel.CommName(genData); 
        // let DemandComms = DataModel.getDemandComms(RYCdata, genData['osy-years']);
        let resData = DataModel.RESData(genData, DemandComms);
        let techData = DataModel.getTechData(genData);
        let commData = DataModel.getCommData(genData);

        let index = 0;
        let labelIndex = {};
        let color = [];
        let label = [];
        let source = [];
        let target = [];
        let value = [];
        let colorLink = [];
        let labelLink = [];
        let selectedTechs = [];

        $.each(resData.Techs, function (id, obj) {
            labelIndex[obj.TechId] = index;
            if(settings.Desc){
                label.push(obj.Tech+'-'+obj.TechDesc);
            }
            else{
                label.push(obj.Tech);
            }
            
            index++;
            if(obj.TechId == 'DS' || obj.TechId == 'DT'){
                color.push('#b32d00');
            }
            else if(obj.TechId == 'FD'){
                color.push('#0099cc');
            }
            else if (techSelect != null){
                if(techSelect.includes(obj.TechId)){
                    color.push('#71a06a');
                }
                else{
                    color.push('#f0ad4e');
                }
            }
            else{
                color.push('#71a06a');
            }
            selectedTechs.push(obj.TechId);
        });


        //let osyScheme= ['#b3d9ff','#ecc6c6','#d1d1e0','#d1e0e0','#ffecb3','#ffb3b3','#e0e0d1','#ecc6d9','#ffd9b3','#ccffff','#f2d9e6','#d6e0f5','#ffffcc','#e5e5cc', '#f2d9d9', '#ffecb3','#ebebe0','#e6e6e6', '#ccf5ff'];
        //let osyScheme= ['#1B2B32', '#37646F', '#a0a8ac', '#71a06a', '#B22E2F', '#cccccc', '#999966', '#cc9900'];
        let osyScheme= ['#1B2B3270', '#37646F70', '#a0a8ac70', '#71a06a70', '#B22E2F70', '#cccccc70', '#99996670', '#cc990070']  

        let colorId = 0;
        $.each(commData, function (id, obj) {
            if(settings.Colors){
                if(typeof osyScheme[colorId] === 'undefined') {
                    colorId = 0
                }   
                obj.Color = osyScheme[colorId];
                colorId++;
            }
            else{
                obj.Color = '#e1e3ea';
            }
        });

        if(techSelect != null){
            selectedTechs = techSelect;
        }
        let dispayedTechs = [];
        let dispayedComms = [];

        $.each(resData.Data.OAR, function (idOAR, objOAR) {
            $.each(objOAR, function (id, CommId) {
                $.each(resData.Data.IAR, function (idIAR, objIAR) {
                    if(objIAR.includes(CommId)){
                        if (techSelect == null || techSelect.includes(idOAR) || techSelect.includes(idIAR)){
                            if (!(dispayedTechs.includes(idOAR))){
                                dispayedTechs.push(idOAR);
                            }
                            if (!(dispayedTechs.includes(idIAR))){
                                dispayedTechs.push(idIAR);
                            }
                            if (!(dispayedComms.includes(CommId))){
                                dispayedComms.push(CommId);
                            }
                            source.push(labelIndex[idOAR]);
                            target.push(labelIndex[idIAR]);
                            //labelLink.push(CommNames[CommId]);
                            if(settings.Desc){
                                labelLink.push(commData[CommId].Comm + '-' + commData[CommId].Desc );
                            }
                            else{
                                labelLink.push(commData[CommId].Comm );
                            }
                            colorLink.push(commData[CommId].Color);
                            value.push(1);
                        }
                    }
                });
            });
        });

        //singles
        $.each(resData.Data.IAR, function (techId, commArr) {
            $.each(commArr, function (id, CommId) { 
                if(resData.Singles.IAR.includes(CommId)){
                    if (techSelect == null || techSelect.includes('DS') || techSelect.includes(techId)){

                        if (!(dispayedTechs.includes(techId))){
                            dispayedTechs.push(techId);
                        }
                        // if (!(dispayedTechs.includes(techId))){
                        //     dispayedTechs.push(techId);
                        // }
                        if (!(dispayedComms.includes(CommId))){
                            dispayedComms.push(CommId);
                        }

                        source.push(labelIndex['DS']);
                        target.push(labelIndex[techId]);
                        //labelLink.push(CommNames[CommId]);
                        //labelLink.push(commData[CommId].Comm + '-' + commData[CommId].Desc );
                        if(settings.Desc){
                            labelLink.push(commData[CommId].Comm + '-' + commData[CommId].Desc );
                        }
                        else{
                            labelLink.push(commData[CommId].Comm );
                        }
                        colorLink.push(commData[CommId].Color);
                        value.push(1);
                    }

                }
            }); 
        });

        $.each(resData.Data.OAR, function (techId, commArr) {
            $.each(commArr, function (id, CommId) {
                if(resData.Singles.OAR.includes(CommId)){
                    if (techSelect == null || techSelect.includes('DT') || techSelect.includes(techId)){

                        if (!(dispayedTechs.includes(techId))){
                            dispayedTechs.push(techId);
                        }
                        // if (!(dispayedTechs.includes(techId))){
                        //     dispayedTechs.push(techId);
                        // }
                        if (!(dispayedComms.includes(CommId))){
                            dispayedComms.push(CommId);
                        }


                        source.push(labelIndex[techId]);
                        target.push(labelIndex['DT']);   
                        //labelLink.push(CommNames[CommId]);
                        //labelLink.push(commData[CommId].Comm + '-' + commData[CommId].Desc );
                        if(settings.Desc){
                            labelLink.push(commData[CommId].Comm + '-' + commData[CommId].Desc );
                        }
                        else{
                            labelLink.push(commData[CommId].Comm );
                        }
                        colorLink.push(commData[CommId].Color);
                        value.push(1);
                    }
                }
                if(resData.Singles.FD.includes(CommId)){
                    if (techSelect == null || techSelect.includes('FD') || techSelect.includes(techId)){

                        if (!(dispayedTechs.includes(techId))){
                            dispayedTechs.push(techId);
                        }
                        // if (!(dispayedTechs.includes(techId))){
                        //     dispayedTechs.push(techId);
                        // }
                        if (!(dispayedComms.includes(CommId))){
                            dispayedComms.push(CommId);
                        }


                        source.push(labelIndex[techId]);
                        target.push(labelIndex['FD']);   
                        //labelLink.push(CommNames[CommId]);
                        //labelLink.push(commData[CommId].Comm + '-' + commData[CommId].Desc );
                        if(settings.Desc){
                            labelLink.push(commData[CommId].Comm + '-' + commData[CommId].Desc );
                        }
                        else{
                            labelLink.push(commData[CommId].Comm );
                        }
                        colorLink.push(commData[CommId].Color);
                        value.push(1);
                    }
                }
            }); 
        });



        let labelCount = source.length;
        this.selectedTechs = selectedTechs;
        this.dispayedTechs = dispayedTechs;
        this.dispayedComms = dispayedComms;

        this.casename = casename;
        this.labelCount = labelCount;
        this.RES = resData;

        this.label = label;
        this.color = color;
        this.height = 600;

        this.source = source;
        this.target = target;
        this.value = value;
        this.labelLink = labelLink;
        this.colorLink = colorLink;

        this.genData = genData;
        this.DemandComms = DemandComms;
        this.TechIdByName = TechIdByName;
        this.techData = techData;
        this.commData = commData;
        this.settings = settings;
        this.pageId = 'RES'
    }
}