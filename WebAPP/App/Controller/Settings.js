import { Model } from "../Model/Settings.Model.js";
import { Html } from "../../Classes/Html.Class.js";
import { JqxSources } from "../../Classes/JqxSources.Class.js";
import { Message } from "../../Classes/Message.Class.js";
import { Osemosys } from "../../Classes/Osemosys.Class.js";
import { Base } from "../../Classes/Base.Class.js";

export default class Settings {
    static Load(){
        let model = new Model();
        this.initPage(model);

    }

    // static refreshPage() {
    //     let UnitsSettings = JSON.parse(localStorage.getItem("osy-units"));
    //     UnitsSettings.forEach(function (item) {
    //         $("#dllSettingUnits").jqxDropDownList('checkItem', item.id);
    //     });
    //     let pagesize = localStorage.getItem("osy-pagesize");
    //     if(pagesize){
    //         $("#ddlGridPageSize").jqxDropDownList('selectItem', pagesize);   
    //     }
    //     else{
    //         $("#ddlGridPageSize").jqxDropDownList('uncheckAll'); 
    //     }
    //     let decimalpoint = localStorage.getItem("osy-decimalpoints");
    //     if(decimalpoint){
    //         $("#ddlPivotDecimalPoints").jqxDropDownList('selectItem', decimalpoint);   
    //     }
    //     else{
    //         $("#ddlPivotDecimalPoints").jqxDropDownList('uncheckAll');  
    //     }
    // }

    static initPage(model) {

        let srcUnits = JqxSources.srcUnit(JSON.stringify(model.units));
        var daUnits = new $.jqx.dataAdapter(srcUnits);
        $("#dllSettingUnits").jqxDropDownList(
            { source: daUnits,  
                placeHolder: "Select model units", 
                displayMember: 'name', 
                valueMember: 'id', 
                groupMember: 'group', 
                checkboxes: true, 
                filterable: true, theme:"material",width: '100%',height: 30, itemHeight: 25,filterHeight:30,dropDownHeight: 535,
                ready: function () {
                    let UnitsSettings = JSON.parse(localStorage.getItem("osy-units"));
                    if(UnitsSettings){
                        UnitsSettings.forEach(function (item) {
                            $("#dllSettingUnits").jqxDropDownList('checkItem', item.id);
                        });
                    }
                }
            });

        // $("#ddlGridPageSize").jqxDropDownList(
        //     { source: ['20', '100', '250', '500', '750', '1000'], 
        //         placeHolder: "Select default grid page size", 
        //         theme:"material",  
        //         width: '100%', 
        //         height: 30,
        //         itemHeight: 25,
        //         autoDropDownHeight: true,
        //         ready: function () {
        //             let pagesize = localStorage.getItem("osy-pagesize");
        //             if(pagesize){
        //                 $("#ddlGridPageSize").jqxDropDownList('selectItem', pagesize);
        //             }
        //         }
        //     });
        
        $("#ddlPivotDecimalPoints").jqxDropDownList(
            { source: ['n0', 'n1', 'n2', 'n3', 'n4'], 
                placeHolder: "Select pivot default decimal points", 
                theme:"material",  
                width: '100%', 
                height: 30,
                itemHeight: 25,
                autoDropDownHeight: true,
                ready: function () {
                    let decimalpoint = localStorage.getItem("osy-decimalpoints");
                    if(decimalpoint){
                        $("#ddlPivotDecimalPoints").jqxDropDownList('selectItem', decimalpoint);
                    }
                }
            });

        this.initEvents(model);
    }

    static initEvents(model){

        //console.log('settings model ', model);

        $("#demo-setting").off('click');
        $("#demo-setting").on('click', function () {
            $(".demo").toggleClass("activate");
            $("#demo-setting i").toggleClass("fa-spin");
            // let UnitsSettings = JSON.parse(localStorage.getItem("osy-units"));
            // if(UnitsSettings){
            //     Settings.refreshPage();
            // }else{
            //     $("#dllSettingUnits").jqxDropDownList('uncheckAll'); 
            // }

            // let pagesize = localStorage.getItem("osy-pagesize");
            // if(pagesize){
            //     $("#ddlGridPageSize").jqxDropDownList('checkItem', pagesize);   
            // }
            // else{
            //     $("#ddlGridPageSize").jqxDropDownList('clearSelection'); 
            // }
            // let decimalpoint = localStorage.getItem("osy-decimalpoints");
            // if(decimalpoint){
            //     $("#ddlPivotDecimalPoints").jqxDropDownList('checkItem', decimalpoint);   
            // }
            // else{
            //     $("#ddlPivotDecimalPoints").jqxDropDownList('clearSelection');  
            // }
            // console.log(UnitsSettings, pagesize, decimalpoint);
        });

        $("#osy-saveSettings").off('click');
        $("#osy-saveSettings").on('click', function () {

            var units = $("#dllSettingUnits").jqxDropDownList('getCheckedItems'); 
            let UnitsSettings = [];
            $.each(units, function (id, obj) {
                UnitsSettings.push(JSON.parse(JSON.stringify(obj.originalItem, ['id', 'name', 'group'])));
            });
            if (UnitsSettings.length > 0) {
                localStorage.setItem("osy-units", JSON.stringify(UnitsSettings));
            }
            else{
                localStorage.removeItem("osy-units");
            }

            // var gridPageSize = $("#ddlGridPageSize").jqxDropDownList('getSelectedItem'); 
            // if(gridPageSize){
            //     localStorage.setItem("osy-pagesize", gridPageSize.value);
            // }   
            // else{
            //     localStorage.removeItem("osy-pagesize");
            // }


            var pivotDecimalPoints = $("#ddlPivotDecimalPoints").jqxDropDownList('getSelectedItem'); 
            if(pivotDecimalPoints){
                localStorage.setItem("osy-decimalpoints", pivotDecimalPoints.value);
            }   
            else{
                localStorage.removeItem("osy-decimalpoints");
            }

            let pageId = localStorage.getItem("osy-pageId");
            // console.log('pageId ', pageId);
   

            if(pageId !='Pivot' && pageId !='AddCase'){
                import(`./${pageId}.js`)
                .then((module) => {
                    const promise = [];
                    const session = Base.getSession();
                    promise.push(session);
                    promise.push(module);
                    return Promise.all(promise);

                })
                .then((data) =>{
                    let [session, module] = data; 
                    console.log(pageId, module, session);
                    const AddCase = module.default;
                    const casename = session['session'];
                    console.log('units from strogae ',JSON.parse(localStorage.getItem("osy-units")))
                    // Call the onLoad method
                    AddCase.refreshPage(casename);
                })
                .catch((error) => {
                    console.error('Error importing module:', error);
                }); 
            }else if(pageId =='AddCase'){
                // let $divTech = $("#osy-gridTech");
                // let $divTechGroup = $("#osy-gridTechGroup");
                // let $divStg = $("#osy-gridStg");
                // let $divComm = $("#osy-gridComm");
                // let $divTs = $("#osy-gridTs");
                // let $divSe = $("#osy-gridSe");
                // let $divDt = $("#osy-gridDt");
                // let $divDtb = $("#osy-gridDtb");
                // let $divEmi = $("#osy-gridEmis");
                // console.log('pageId updatedatabound ', pageId);
                // $divComm.jqxGrid('updatebounddata');
                // $divTech.jqxGrid('updatebounddata');
                            Message.loaderStart();
            location.reload();
            }
            else{
                import(`../../AppResults/Controller/${pageId}.js`)
                .then((module) => {
                    const promise = [];
                    const session = Base.getSession();
                    promise.push(session);
                    promise.push(module);
                    return Promise.all(promise);

                })
                .then((data) =>{
                    let [session, module] = data; 
                    const Page = module.default;
                    const casename = session['session'];
                    // Call the onLoad method
                    Page.refreshPage(casename);
                })
                .catch((error) => {
                    console.error('Error importing module:', error);
                });  
            }

            Message.smallBoxInfo("Info!", "MUIOGO settings have been saved successfully!", 5000);
            $(".demo").toggleClass("activate");
            // Message.loaderStart();
            // location.reload();
        
                
        });

        $("#osy-resetSettings").off('click');
        $("#osy-resetSettings").on('click', function () {
            localStorage.clear();
            $("#dllSettingUnits").jqxDropDownList('uncheckAll');
            //$("#ddlGridPageSize").jqxDropDownList('clearSelection'); 
            $("#ddlPivotDecimalPoints").jqxDropDownList('clearSelection');  
            Message.smallBoxInfo("Info!", "You have reset MUIOGO settings!", 5000);
            $(".demo").toggleClass("activate");

            // Message.loaderStart();
            // location.reload(); 
        });

        $("#osy-sounds").off('click');
        $("#osy-sounds").on('click', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();

			$.sound_on = !$.sound_on;
            if( $.sound_on ==false){
                $(this).find($(".fa")).removeClass('fa-volume-up').addClass('fa-volume-off');
                $.smallBox({
                    title : "MUTE",
                    content : "All sounds have been muted!",
                    color : "#a90329",
                    timeout: 4000,
                    icon : "fa fa-volume-off"
                });
            }else{
                $(this).find($(".fa")).removeClass('fa-volume-off').addClass('fa-volume-up');
                $.smallBox({
                    title : "UNMUTE",
                    content : "All sounds have been turned on!",
                    color : "#40ac2b",
                    sound_file: 'voice_alert',
                    timeout: 5000,
                    icon : "fa fa-volume-up"
                });
            }
			
        });
    }
}