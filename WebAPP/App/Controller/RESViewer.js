import { Message } from "../../Classes/Message.Class.js";
import { Base } from "../../Classes/Base.Class.js";
import { Html } from "../../Classes/Html.Class.js";
import { Model } from "../Model/RESViewer.Model.js";
import { Osemosys } from "../../Classes/Osemosys.Class.js";
import { DEF } from "../../Classes/Definition.Class.js";
import { MessageSelect } from "./MessageSelect.js";
import { Chart } from "../../Classes/Chart.Class.js";
import { DataModel } from "../../Classes/DataModel.Class.js";
import { MultiSelect } from "../../Classes/MultiSelect.Class.js";

export default class RESViewer {
    static onLoad() {
        Message.loaderStart('Preparing RES...');
        Base.getSession()
            .then(response => {
                let casename = response['session'];
                if (casename) {
                    const promise = [];
                    promise.push(casename);
                    const genData = Osemosys.getData(casename, 'genData.json');
                    promise.push(genData);
                    const RYCdata = Osemosys.getData(casename, 'RYC.json');
                    promise.push(RYCdata);
                    return Promise.all(promise);
                } else {
                    MessageSelect.init(RESViewer.refreshPage.bind(RESViewer));
                }
            })
            .then(data => {
                let settings = {};
                settings.Colors = false;
                settings.Desc = false;
                let [casename, genData, RYCdata] = data;
                let DemandComms = DataModel.getDemandComms(RYCdata, genData['osy-years']);
                let model = new Model(casename, genData, DemandComms, settings);
                this.initPage(model);
                this.initEvents(model);
            })
            .catch(error => {
                Message.warning(error);
            });
    }

    static refreshPage(casename, model) {
        Message.loaderStart('Preparing RES...');
        Base.setSession(casename)
            .then(response => {
                const promise = [];
                promise.push(casename);
                const genData = Osemosys.getData(casename, 'genData.json');
                promise.push(genData);
                const RYCdata = Osemosys.getData(casename, 'RYC.json');
                promise.push(RYCdata);
                return Promise.all(promise);
            })
            .then(data => {
                let [casename, genData, RYCdata] = data;
                let settings = {};
                settings.Colors = $("#useColors").is(":checked");
                settings.Desc = $("#useDesc").is(":checked");

                let DemandComms = DataModel.getDemandComms(RYCdata, genData['osy-years']);
                let modelNew = new Model(casename, genData, DemandComms, settings);
                this.initPage(modelNew);
                this.initEvents(modelNew);
            })
            .catch(error => {
                Message.warning(error);
            });
    }


    static sankeySize(model){
        //console.log('model.labelCount ', model.labelCount)
        // if(model.labelCount <= 20){
        //     model.height = 620;
        // }else if(model.labelCount > 20 && model.labelCount <= 50){
        //     model.height = 1000;
        // }else if(model.labelCount > 50 && model.labelCount <= 100){
        //     model.height = 2000;
        // }else if(model.labelCount > 100 && model.labelCount <= 150){
        //     model.height = 3000;
        // }else if(model.labelCount > 150 ){
        //     model.height = 6000;
        // }

        if(model.labelCount <= 2){
            model.height = 250;
        }else if(model.labelCount > 2 && model.labelCount <= 5){
            model.height = 300;
        }else if(model.labelCount > 5 && model.labelCount <= 8){
            model.height = 350;
        }else if(model.labelCount > 8 && model.labelCount <= 10){
            model.height = 400;
        }else if(model.labelCount > 10 && model.labelCount <= 15){
            model.height = 450;
        }else if(model.labelCount > 15 && model.labelCount <= 20){
            model.height = 500;
        }else if(model.labelCount > 20 && model.labelCount <= 25){
            model.height = 550;
        }else if(model.labelCount > 25 && model.labelCount <= 30){
            model.height = 600;
        }else if(model.labelCount > 30 && model.labelCount <= 35){
            model.height = 650;
        }else if(model.labelCount > 35 && model.labelCount <= 40){
            model.height = 700;
        }else if(model.labelCount > 45 && model.labelCount <= 50){
            model.height = 750;
        }else if(model.labelCount > 50 && model.labelCount <= 55){
            model.height = 800;
        }else if(model.labelCount > 55 && model.labelCount <= 60){
            model.height = 850;
        }else if(model.labelCount > 60 && model.labelCount <= 65){
            model.height = 900;
        }else if(model.labelCount > 65 && model.labelCount <= 70){
            model.height = 950;
        }else if(model.labelCount > 70 && model.labelCount <= 75){
            model.height = 1000;
        }else if(model.labelCount > 75 && model.labelCount <= 100){
            model.height = 1200;
        }else if(model.labelCount > 100 && model.labelCount <= 125){
            model.height = 1400;
        }else if(model.labelCount > 125 && model.labelCount <= 150){
            model.height = 1600;
        }else if(model.labelCount > 150 && model.labelCount <= 175){
            model.height = 1800;
        }else if(model.labelCount > 175 && model.labelCount <= 200){
            model.height = 2000;
        }else if(model.labelCount > 200 && model.labelCount <= 225){
            model.height = 2200;
        }else if(model.labelCount > 225 && model.labelCount <= 250){
            model.height = 2400;
        }else if(model.labelCount > 250 && model.labelCount <= 275){
            model.height = 2600;
        }else if(model.labelCount > 275 && model.labelCount <= 300){
            model.height = 2800;
        }else if(model.labelCount > 300 && model.labelCount <= 325){
            model.height = 3000;
        }else if(model.labelCount > 325 && model.labelCount <= 350){
            model.height = 3200;
        }else if(model.labelCount > 350 && model.labelCount <= 375){
            model.height = 3400;
        }else if(model.labelCount > 375 && model.labelCount <= 400){
            model.height = 3600;
        }else if(model.labelCount > 400 && model.labelCount <= 425){
            model.height = 3800;
        }else if(model.labelCount > 425 ){
            model.height = 6000;
        }
        //$('#labelCount').html(model.labelCount + ' - ' +  model.height)
        //console.log('tech count, height' , model.labelCount, model.height)
    }
    
    static initPage(model) {

        //console.log('model js ', model)
        Message.clearMessages();
        let $div = 'osy-RESViewer';

        Html.title(model.casename, 'RES Viewer', 'Reference Energy System');
        Html.ResStats(model);


        if(typeof(model.cmbTechs) != 'undefined'){
            model.cmbTechs.destroy();
        }

        model.cmbTechs = new MultiSelect('#osy-activityTechs', {
            placeholder: 'Technologies',
            headerFormat: '{count:n0} Technology',
            displayMemberPath: 'Tech',
            itemsSource: model.RES.Techs,
            showSelectAllCheckbox: true,
            showFilterInput: true,
            checkedItemsChanged: (sender) => {
                model.selectedTechs = [];
                let html = '';
                sender.checkedItems.forEach((item) => {
                    //console.log('item ', item)
                    html += `<li><a><small><b>${item.Tech}</b> - ${item.TechDesc}</small></a> <p class="divider"></p></li>`;
                    model.selectedTechs.push(item.TechId);
                });
                //console.log('model created in cmbTech ', model)
                document.querySelector('#selectedTechs').innerHTML = html;
                
            }
        });

        this.sankeySize(model);
        Chart.RESChart($div, model);
    }

    static initEvents(model) {

        let $div = 'osy-RESViewer';
        $("#casePicker").off('click');
        $("#casePicker").on('click', '.selectCS', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var casename = $(this).attr('data-ps');
            Html.updateCasePicker(casename);
            RESViewer.refreshPage(casename, model);
            Message.smallBoxConfirmation("Confirmation!", "Model " + casename + " selected!", 3500);
        });

        $("#renderSankey").off('click');
        $("#renderSankey").on('click', function (e) {  
            Message.loaderStart('Preparing RES...'); 
            // console.log('model.selectedTechs ', model.selectedTechs);
            // console.log('model.selectedTechs.length ', model.selectedTechs.length);

            if(model.selectedTechs.length >=2){
                $('#undoSankey').show();
            }
            let settings = {};
            settings.Colors = $("#useColors").is(":checked");
            settings.Desc = $("#useDesc").is(":checked");
            //console.log('model.selectedTechs ', model.selectedTechs)
      
            let modelNew = new Model(model.casename, model.genData, model.DemandComms, settings, model.selectedTechs);

            //console.log('modelNew ', modelNew)
            Html.ResStats(modelNew);
            RESViewer.sankeySize(modelNew);
            Chart.RESChart($div, modelNew);
            Message.loaderEnd();
        });

        $("#undoSankey").off('click');
        $("#undoSankey").on('click', function (e) {  
            Message.loaderStart('Undo RES...'); 

            let settings = {};
            settings.Colors = $("#useColors").is(":checked");
            settings.Desc = $("#useDesc").is(":checked");

            model.selectedTechs.pop();

            // console.log('model.selectedTechs ', model.selectedTechs)
      
            let modelNew = new Model(model.casename, model.genData, model.DemandComms, settings, model.selectedTechs);

            //update drop down liste tehnologija
            $.each(modelNew.RES.Techs, function (id, obj) {
                if(model.selectedTechs.includes(obj.TechId)){ 
                    obj.$checked = true;
                }
                else{
                    obj.$checked = false;
                }
            });

            model.cmbTechs.itemsSource = modelNew.RES.Techs;

            Html.ResStats(modelNew);
            RESViewer.sankeySize(modelNew);
            Chart.RESChart($div, modelNew);
            Message.loaderEnd();
        });

        $("#restoreSankey").off('click');
        $("#restoreSankey").on('click', function (e) {
            Message.loaderStart('Preparing RES...');
            let settings = {};
            settings.Colors = $("#useColors").is(":checked");
            settings.Desc = $("#useDesc").is(":checked");
            let modelNew = new Model(model.casename, model.genData, model.DemandComms, settings);
            model.cmbTechs.itemsSource = modelNew.RES.Techs;
            Html.ResStats(modelNew);
            RESViewer.sankeySize(modelNew);
            Chart.RESChart($div, modelNew);
            Message.loaderEnd();
        });

        var myPlot = document.getElementById('osy-RESViewer');
        myPlot.removeAllListeners('plotly_click')
        myPlot.on('plotly_click', function(data){
            Message.loaderStart('Preparing RES...');

            // var pts = '';
            // for(var i=0; i < data.points.length; i++){
            //     // pts = 'x = '+data.points[i].x +'\ny = '+ data.points[i].y.toPrecision(4) + '\n\n';
            //     pts = 'x = '+data.points[i].x1 +'\ny = '+ data.points[i].y1 + '\n\n';
            // }
            //alert('Closest point clicked:\n\n'+pts);

            let msgData = data.points[0];
            let msg;
            if ('source' in msgData && 'target' in msgData){
                msg = `<i class="fa fa-cube fa-lg osy-second-color-d"></i><b>COMMODITY:</b> ${msgData.label} <br /> <i class="fa fa-sign-in fa-lg osy-second-color"></i><b>SOURCE TECHNOLOGY:</b> ${msgData.source.label} <br /> <i class="fa fa-sign-out fa-lg danger"></i><b>TARGET TECHNOLOGY:</b> ${msgData.target.label} <br />`
            }
            else{
                //Technology click

                //console.log('msgData ', msgData)
                if(msgData.label == 'Missing Source Technology' ){
                    msg = `<i class="fa fa-cog fa-lg osy-second-color-d"></i> <b>WARNING:</b> Your model is missing source technology!`;
                    Message.resMessage(msg);
                    Message.loaderEnd();
                    return false;
                }
                if(msgData.label == 'Missing Target Technology' ){
                    msg = `<i class="fa fa-cog fa-lg osy-second-color-d"></i> <b>WARNING:</b> Your model is missing target technology!`;
                    Message.resMessage(msg);
                    Message.loaderEnd();
                    return false;
                }
                if( msgData.label == 'Final demand'){
                    msg = `<i class="fa fa-cog fa-lg osy-second-color-d"></i> <b>Final demand</b>`;
                    Message.resMessage(msg);
                    Message.loaderEnd();
                    return false;
                }
                let sourceData = [];
                let targetData = [];
                if (msgData.sourceLinks !== undefined || msgData.sourceLinks.length != 0) {
                    for(var i=0; i < msgData.sourceLinks.length; i++){
                        if (!sourceData.includes(msgData.sourceLinks[i].label)){
                            sourceData.push(msgData.sourceLinks[i].label)
                        }        
                    }
                }
                if (msgData.targetLinks !== undefined || msgData.targetLinks.length != 0) {
                    for(var i=0; i < msgData.targetLinks.length; i++){
                        //targetData.push(msgData.targetLinks[i].label);
                        if (!targetData.includes(msgData.targetLinks[i].label)){
                            targetData.push(msgData.targetLinks[i].label)
                        }
                    }
                }
                if (sourceData.length != 0 && targetData.length != 0 ) {
                    msg = `<i class="fa fa-cog fa-lg osy-second-color-d"></i> <b>TECHNOLOGY:</b> ${msgData.label} <br /> <i class="fa fa-sign-in fa-lg osy-second-color"></i> <b>INPUT COMMODITY:</b> ${targetData} <br /> <i class="fa fa-sign-out fa-lg danger"></i>  <b>OUTPUT COMMODITY:</b> ${sourceData} <br />`;
                }
                else if(sourceData.length != 0 && targetData.length == 0 ){
                    msg = `<i class="fa fa-cog fa-lg osy-second-color-d"></i> <b>TECHNOLOGY:</b> ${msgData.label} <br /> <i class="fa fa-sign-out fa-lg danger"></i> <b>OUTPUT COMMODITY:</b> ${sourceData} <br />`;
                }
                if (sourceData.length == 0 && targetData.length != 0 ) {
                    msg = `<i class="fa fa-cog fa-lg osy-second-color-d"></i> <b>TECHNOLOGY:</b> ${msgData.label} <br /> <i class="fa fa-sign-in fa-lg osy-second-color"></i> <b>INPUT COMMODITY:</b> ${targetData}`;
                }          
                //console.log('model on plotly click ', model)

                let tech = msgData.label.split('-')[0];
                let techId = model.TechIdByName[tech]    
    
                if(!model.selectedTechs.includes(techId)){ 
                    model.selectedTechs.push(techId);
                }
                if(model.selectedTechs.length >=2){
                    $('#undoSankey').show();
                }

                let settings = {};
                settings.Colors = $("#useColors").is(":checked");
                settings.Desc = $("#useDesc").is(":checked");
    
                let modelNew = new Model(model.casename, model.genData, model.DemandComms, settings, model.selectedTechs);
            
    
                $.each(modelNew.RES.Techs, function (id, obj) {
                    if(model.selectedTechs.includes(obj.TechId)){ 
                        obj.$checked = true;
                    }
                    else{
                        obj.$checked = false;
                    }
                });
    
                model.cmbTechs.itemsSource = modelNew.RES.Techs;
    
                Html.ResStats(modelNew);
                RESViewer.sankeySize(modelNew);
                Chart.RESChart($div, modelNew);

            }
            Message.resMessage(msg)
            Message.bigBoxDefault('Model diagram info', msg, 4000);
            Message.loaderEnd();
        });

        let zoomArr = [0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1];
        var element = document.querySelector('#osy-RESViewer');
        let value = element.getBoundingClientRect().width / element.offsetWidth;
        let indexofArr = 9;
        document.querySelector('#zoomIn').addEventListener('click',()=>{
        //console.log('value of index zoomin is',indexofArr)
        if(indexofArr < zoomArr.length-1){
            indexofArr += 1;
            value = zoomArr[indexofArr];
            element.style['transform'] = `scale(${value})`
        }
        })

        document.querySelector('#zoomOut').addEventListener('click',()=>{
        //console.log('value of index  zoom out is',indexofArr)
        if(indexofArr > 0){
            indexofArr -= 1;
            value = zoomArr[indexofArr];
            element.style['transform'] = `scale(${value})`
        }
        })

        $("#showLog").click(function (e) {
            e.preventDefault();
            $('#definition').html(`
                <h5>${DEF[model.pageId].title}</h5>
                ${DEF[model.pageId].definition}
            `);
            $('#definition').toggle('slow');
        });

        Message.loaderEnd();
    }
}