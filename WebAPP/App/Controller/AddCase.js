import { Message } from "../../Classes/Message.Class.js";
import { DefaultObj } from "../../Classes/DefaultObj.Class.js";
import { Base } from "../../Classes/Base.Class.js";
import { SyncS3 } from "../../Classes/SyncS3.Class.js";
import { Html } from "../../Classes/Html.Class.js";
import { Grid } from "../../Classes/Grid.Class.js";
import { Osemosys } from "../../Classes/Osemosys.Class.js";
import { SmartAdmin } from "../../Classes/SmartAdmin.Class.js";
import { Model } from "../Model/AddCase.Model.js";
import { Navbar } from "./Navbar.js";
import { DEF } from "../../Classes/Definition.Class.js";
import { Sidebar } from "./Sidebar.js";

export default class AddCase {
    static onLoad() {
        Base.getSession()
            .then(response => {
                let casename = response.session;
                const promise = [];
                let genData = Osemosys.getData(casename, 'genData.json');
                promise.push(genData);
                const resData = Osemosys.getResultData(casename, 'resData.json');
                promise.push(resData);
                const PARAMETERS = Osemosys.getParamFile();
                promise.push(PARAMETERS);
                return Promise.all(promise);
            })
            .then(data => {
                let [genData, resData, PARAMETERS] = data;
                let model = new Model(genData, resData, PARAMETERS, "AddCase");
                
                this.initPage(model);
            })
            .catch(error => {
                Message.danger(error);
            });
    }
    static refreshPage(casename) {
        Base.setSession(casename)
            .then(response => {
                Message.clearMessages();
                const promise = [];
                let genData = Osemosys.getData(casename, 'genData.json');
                promise.push(genData);
                const resData = Osemosys.getResultData(casename, 'resData.json');
                promise.push(resData);
                const PARAMETERS = Osemosys.getParamFile();
                promise.push(PARAMETERS);
                return Promise.all(promise);
            })
            .then(data => {
                let [genData, resData, PARAMETERS] = data;
                let model = new Model(genData, resData, PARAMETERS, "AddCase");
                AddCase.initPage(model);
            })
            .catch(error => {
                console.log(' error ', error)
                Message.bigBoxDanger(error);
            })
    }

    static initPage(model) {
        Message.clearMessages();
        //$('a[href="#tabComms"]').click();
        //Navbar.initPage(model.casename, model.pageId);
        //console.log('model ', model)
        
        Html.title(model.casename, model.title, "create & edit");
        Html.genData(model);

        Grid.tsGrid(model.timeslices, model.seasons, model.daytypes, model.dailytimebrackets, model.seNames, model.dtNames, model.dtbNames);
        Grid.seGrid(model.seasons);
        Grid.dtGrid(model.daytypes);
        Grid.dtbGrid(model.dailytimebrackets);
        Grid.commGrid(model.commodities);
        Grid.stgGrid(model.stg, model.techs, model.techNames);
        Grid.techsGrid(model.techs, model.commodities, model.techGroups, model.emissions, model.commNames, model.emiNames, model.techGroupNames);
      
        Grid.techGroupGrid(model.techGroups);
        Grid.emisGrid(model.emissions);
        Grid.scenarioGrid(model.scenarios);
        Grid.constraintGrid(model.techs, model.constraints, model.techNames);

        if (model.casename == null) {
            $('#osy-save').show();
            $('#osy-update').hide();
            Message.info("Please select existing or create new model!");
        } else {
            $("#osy-new").show();
            $('#osy-update').show();
            $('#osy-save').hide();
        }
        loadScript("References/smartadmin/js/plugin/ion-slider/ion.rangeSlider.min.js", SmartAdmin.rangeSlider.bind(null, model.years));
        pageSetUp();
        this.initEvents(model);
    }

    static initEvents(model) {
        console.log('model ', model)
        let $divTech = $("#osy-gridTech");
        let $divTechGroup = $("#osy-gridTechGroup");
        let $divStg = $("#osy-gridStg");
        let $divComm = $("#osy-gridComm");
        let $divTs = $("#osy-gridTs");
        let $divSe = $("#osy-gridSe");
        let $divDt = $("#osy-gridDt");
        let $divDtb = $("#osy-gridDtb");
        let $divEmi = $("#osy-gridEmis");
        let $divScenario = $("#osy-gridScenario");
        let $divConstraint = $("#osy-gridConstraint");

        $("#casePicker").off('click');
        $("#casePicker").on('click', '.selectCS', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var casename = $(this).attr('data-ps');
            Html.updateCasePicker(casename);
            Sidebar.Reload(casename);
            AddCase.refreshPage(casename);
            Message.smallBoxInfo("Case selection", casename + " is selected!", 3000);
        });

        function render(message, input) {
            if (this._message) {
                this._message.remove();
            }
            this._message = $("<span class='jqx-validator-error-label'>" + message + "</span>")
            this._message.appendTo("#yearsselectmsg");
            Message.smallBoxWarning("Selection", "Model has to have one year at least!", 3000);
            return this._message;
        }

        $("#osy-caseForm").jqxValidator({
            hintType: 'label',
            animationDuration: 500,
            rules: [
                { input: '#osy-casename', message: "Model name is required field!", action: 'keyup', rule: 'required' },
                {
                    input: '#osy-casename', message: "Entered model name is not allowed!", action: 'keyup', rule: function (input, commit) {
                        var casename = $("#osy-casename").val();
                        var result = (/^[a-zA-Z0-9-_ ]*$/.test(casename));
                        return result;
                    }
                },
                { input: '#osy-mo', message: "Mode of operation is required field!", action: 'keyup', rule: 'required' },
                {
                    input: '#osy-mo', message: "Mode of operation should positive value!", action: 'keyup', rule: function (input, commit) {
                        var dr = $("#osy-mo").val();
                        return dr < 1 || isNaN(dr) ? false : true;
                    }
                },
                // { input: '#osy-ns', message: "Number of seasons is required field!", action: 'keyup', rule: 'required' },
                // {
                //     input: '#osy-ns', message: "Number of seasons should be zero or positive value!", action: 'keyup', rule: function (input, commit) {
                //         var dr = $("#osy-ns").val();
                //         return dr < 0 || isNaN(dr) ? false : true;
                //     }
                // },
                // { input: '#osy-dt', message: "Day type is required field!", action: 'keyup', rule: 'required' },
                // {
                //     input: '#osy-dt', message: "Day type should be zero or positive value!", action: 'keyup', rule: function (input, commit) {
                //         var dr = $("#osy-dt").val();
                //         return dr < 0 || isNaN(dr) ? false : true;
                //     }
                // },
                // { input: '#osy-date', message: "Date is required field!", action: 'change', rule: 'required' },
                // {
                //     input: '#osy-years', message: 'Select at least one year', action: 'change', hintRender: render, rule: function () {
                //         var elements = $('#osy-years').find('input[type=checkbox]');
                //         var check = false;
                //         var result = $.grep(elements, function (element, index) {
                //             if (element.checked == true)
                //                 check = true;
                //         });
                //         return (check);
                //     }
                // }
            ]
        });

        $("#osy-new").on('click', function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();
            AddCase.refreshPage(null);
            //Sidebar.Load(null, null)
            Sidebar.Reload(null);

            $divTech.jqxGrid({ pagesizeoptions:['10', '25', '50', '100', '250', '500', '750', '1000']}); 
            $("#osy-new").hide();
            $('#osy-update').hide();
            $('#osy-save').show();
            Message.smallBoxConfirmation("Confirmation!", "Configure new Model!", 3500);
        });

        $("#osy-save").off('click');
        $("#osy-save").on('click', function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();
            $("#osy-caseForm").jqxValidator('validate')
        });

        $("#osy-update").off('click');
        $("#osy-update").on('click', function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();
            $("#osy-caseForm").jqxValidator('validate')
        });

        $("#osy-caseForm").off('validationSuccess');
        $("#osy-caseForm").on('validationSuccess', function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();

            Message.loaderStart('Saving model data')
            var casename = $("#osy-casename").val().trim();
            var desc = $("#osy-desc").val().trim();
            
            const timeElapsed = Date.now();
            const today = new Date(timeElapsed);
            let date = today.toDateString();

            //var date = $("#osy-date").val();
            var currency = $("#osy-currency").val();
            var mo = $("#osy-mo").val().trim();

            var years = new Array();
            $.each($('input[type="checkbox"]:checked'), function (key, value) {
                years.push($(value).attr("id"));
            });

            let POSTDATA = {
                "osy-version": "5.5",
                "osy-casename": casename,
                "osy-desc": desc,
                "osy-date": date,
                "osy-currency": currency,
                "osy-mo": mo,
                "osy-tech": model.techs,
                "osy-stg": model.stg,
                "osy-techGroups": model.techGroups,
                "osy-comm": model.commodities,
                "osy-ts": model.timeslices,
                "osy-se": model.seasons,
                "osy-dt": model.daytypes,
                "osy-dtb": model.dailytimebrackets,
                
                "osy-emis": model.emissions,
                "osy-scenarios": model.scenarios,
                "osy-constraints": model.constraints,
                "osy-years": years
            }

            Osemosys.saveCase(POSTDATA)
            .then(response => {
                Message.loaderEnd()
                if (response.status_code == "created") {
                    $("#osy-new").show();
                    $('#osy-update').show();
                    $('#osy-save').hide();
                    Message.clearMessages();
                    Message.bigBoxSuccess('Model message', response.message, 3000);
                    Html.appendCasePicker(casename, casename);
                    Sidebar.Reload(casename);
                    $("#osy-case").html(casename);
                    if (Base.AWS_SYNC == 1) {
                        SyncS3.deleteResultsPreSync(casename)
                            .then(response => {
                                SyncS3.uploadSync(casename);
                            });
                    }
                }
                if (response.status_code == "edited") {
                    Html.title(casename, 'Model configuration', 'create & edit');
                    $("#osy-new").show();
                    Navbar.initPage(casename);
                    Sidebar.Reload(casename);
                    Message.bigBoxInfo('Model message', response.message, 3000);
                    if (Base.AWS_SYNC == 1) {
                        SyncS3.deleteResultsPreSync(casename)
                            .then(response => {
                                SyncS3.uploadSync(casename);
                            });
                    }
                }
                if (response.status_code == "exist") {
                    $("#osy-new").show();
                    Message.bigBoxWarning('Model message', response.message, 3000);
                }
            })
            .catch(error => {
                Message.loaderEnd()
                Message.bigBoxDanger('Error message', error, null);
            })
        });

        //TECHNOLOGIES GRID AND EVENTS
        $('#osy-caseForm').undelegate("#osy-addTech", "click");
        $('#osy-caseForm').delegate("#osy-addTech", "click", function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();
            let defaultTech = DefaultObj.defaultTech();
            //tech grid se pravi dinalicki potrebno je updatovati model
            //JSON parse strungify potrebno da iz nekog razloga izbacino elemente uid boundindex...
            model.techs.unshift(JSON.parse(JSON.stringify(defaultTech[0], ['TechId', 'Tech', 'Desc', 'CapUnitId', 'ActUnitId', 'TG', 'IAR', 'OAR', "INCR", "ITCR", 'EAR'])));
            //model.techs.push(defaultTech[0]);
            //update technames
            model.techNames[defaultTech[0]['TechId']] = defaultTech[0]['Tech'];
            //add row in grid
            $divTech.jqxGrid('addrow', null, defaultTech, 'first');
            //upat eza broj techs u tabu
            model.techCount++;
            $("#techCount").text(model.techCount);
        });

        $('#osy-caseForm').undelegate(".deleteTech", "click");
        $('#osy-caseForm').delegate(".deleteTech", "click", function (e) {
            //$(".deleteTech").on("click", function(e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var id = $(this).attr('data-id');
            var htmltechId = $(this).attr('data-techId');            
            if (model.techs.length > 1 && $divTech.jqxGrid('getrows').length>1)  {
                var techId = $divTech.jqxGrid('getcellvalue', id, 'TechId');
                //ovdje moramo korisit id ne rowID koji ostaje nepromjenjen nakon brisanja
                //id je index koji se mijnje ako brisemo ili dodajemo na pocetak tabele ili niza
                //sortingn ne utice na rowid i id i index
                var rowid = $divTech.jqxGrid('getrowid', id);

                console.log('rowid id ', rowid,id)
                //var rows = $divTech.jqxGrid('getboundrows');
                // // console.log('rows[rowId].uid ', rows[rowid].uid);
                // // console.log('rows[id]].uid ', rows[id].uid);
                // console.log('model.techs ',model.techs)
                // console.log('rows ', rows)
                // //console.log('model.techs rowid ',model.techs[rowid])
                // console.log('model.techs TECH ',model.techs[id].Tech)
                // console.log("TG ", model.techs[rowid].TG.length)


                //provjera da brisemo tacnu tehnologiju
                //console.log('techIds ', model.techs[id].TechId,techId, htmltechId,    model.techNames[techId],   model.techNames[model.techs[id].TechId],    model.techNames[htmltechId])
                if(model.techs[id].TechId != techId ||techId != htmltechId){
                    console.log('delete tech')  
                    Message.bigBoxDanger('Technology deletion error', `Wrong index!! <b>${model.techs[id].Tech}</b>?`, 3000);
                }
                if(model.techs[id].TG.length>0){          
                    Message.confirmationDialog('Technology deletion warning', `Technology <b>${model.techs[id].Tech}</b> has technology group membership(s). Deleting the technology could impact visalisation of results for previously run cases. Are you sure you want to proceed?`, model, $divTech, id, rowid, techId)
                }
                else{
                    $divTech.jqxGrid('deleterow', rowid);
                    model.techs.splice(id, 1);
                    //update techNames
                    delete model.techNames[techId];
                    //update count
                    model.techCount--;
                    $("#techCount").text(model.techCount);
                    //$divTech.jqxGrid('updatebounddata');
                    //izbrisati iz model constraints eventualne tehnologijel koje smo izbrisali
                    $.each(model.constraints, function (id, conObj) {
                        conObj['CM'] = conObj['CM'].filter(item => item !== techId);
                    });
                }
            }
            else {
                Message.bigBoxWarning('Warning', 'You cannot delete. At least one technology is neccessary.', 3000);
            }
        });

        $divTech.on('cellvaluechanged', function (event) {
            Pace.restart();
            var args = event.args;
            var column = event.args.datafield;
            var rowBoundIndex = args.rowindex;
            var value = args.newvalue.trim();
            if (column == 'CapUnitId' || column == 'ActUnitId') {
                Message.bigBoxWarning('Unit change warninig!', 'Changing technology unit will not recalculate entered nor default values in the model.', 3000);
            }
            if (column != 'IAR' && column != 'OAR' && column != 'EAR' && column != 'INCR' && column != 'ITCR'  && column != 'TG') {
                model.techs[rowBoundIndex][column] = value;
            } else {
                if (value.includes(',') && value) {
                    var array = value.split(',');
                } else if (value) {
                    var array = [];
                    array.push(value);
                } else {
                    var array = [];
                }
                model.techs[rowBoundIndex][column] = array;
            }
            if (column == 'Tech') {
                var techId = $divTech.jqxGrid('getcellvalue', rowBoundIndex, 'TechId');
                model.techNames[techId] = value;
            }
        });

        $('#osy-caseForm').undelegate("#osy-addTechGroup", "click");
        $('#osy-caseForm').delegate("#osy-addTechGroup", "click", function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();
            let defaultTechGroup = DefaultObj.defaultTechGroup();
            //tech grid se pravi dinalicki potrebno je updatovati model
            //JSON parse strungify potrebno da iz nekog razloga izbacino elemente uid boundindex...
            model.techGroups.push(JSON.parse(JSON.stringify(defaultTechGroup[0], ['TechGroupId', 'TechGroup', 'Desc'])));
            //model.techs.push(defaultTech[0]);
            //update technames
            model.techGroupNames[defaultTechGroup[0]['TechGroupId']] = defaultTechGroup[0]['TechGroup'];
            //add row in grid
            $divTechGroup.jqxGrid('addrow', null, defaultTechGroup);
            //upat eza broj techs u tabu
            model.techGroupCount++;
            $("#techGroupCount").text(model.techGroupCount);
        });

        $('#osy-caseForm').undelegate(".deleteTechGroup", "click");
        $('#osy-caseForm').delegate(".deleteTechGroup", "click", function (e) {
            //$(".deleteTech").on("click", function(e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var id = $(this).attr('data-id');
            if (id != 0) {
                var techGroupId = $divTechGroup.jqxGrid('getcellvalue', id, 'TechGroupId');
                var rowid = $divTechGroup.jqxGrid('getrowid', id);
                $divTechGroup.jqxGrid('deleterow', rowid);
                model.techGroups.splice(id, 1);
                //update techNames
                delete model.techGroupNames[techGroupId];
                //update count
                model.techGroupCount--;
                $("#techGroupCount").text(model.techGroupCount);
                //izbirsati iz modela za tech nz EAR za izbrisanu emisiju ako je slucajno odabrana za neku tehnologiju
                $.each(model.techs, function (id, techObj) {
                    techObj['TG'] = techObj['TG'].filter(item => item !== techGroupId);
                });
            }
        });

        $divTechGroup.on('cellvaluechanged', function (event) {
            var args = event.args;
            var column = event.args.datafield;
            var rowBoundIndex = args.rowindex;
            var value = args.newvalue.trim();
            model.techGroups[rowBoundIndex][column] = value;

            if (column == 'TechGroup') {
                var techGroupId = $divTechGroup.jqxGrid('getcellvalue', rowBoundIndex, 'TechGroupId');
                model.techGroupNames[techGroupId] = value;
            }
        });

        //TIMESLICES GRID AND EVENTS
        $('#osy-caseForm').undelegate("#osy-addTs", "click");
        $('#osy-caseForm').delegate("#osy-addTs", "click", function (event) {
            //console.log('add timeslice')
            event.preventDefault();
            event.stopImmediatePropagation();
            let defaultTs = DefaultObj.defaultTs();
            //console.log('defaultTs ',defaultTs)
            model.timeslices.push(JSON.parse(JSON.stringify(defaultTs[0], ['TsId', 'Ts', 'Desc', 'SE', 'DT', 'DTB'])));

            //update commnames
            model.tsNames[defaultTs[0]['TsId']] = defaultTs[0]['Ts'];
            //add row
            $divTs.jqxGrid('addrow', null, defaultTs);
            model.tsCount++;
            $("#tsCount").text(model.tsCount);
        });

        $('#osy-caseForm').undelegate(".deleteTs", "click");
        $('#osy-caseForm').delegate(".deleteTs", "click", function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var id = $(this).attr('data-id');
            if (id != 0) {
                var tsId = $divTs.jqxGrid('getcellvalue', id, 'TsId');
                var rowid = $divTs.jqxGrid('getrowid', id);
                $divTs.jqxGrid('deleterow', rowid);
                model.timeslices.splice(id, 1);
                //update techNames
                delete model.tsNames[tsId];
                //update count
                model.tsCount--;
                $("#tsCount").text(model.tsCount);
            }
        });  

        $divTs.on('cellvaluechanged', function (event) {
            var args = event.args;
            //console.log('arsg ', args)  
            var column = event.args.datafield;
            var rowBoundIndex = args.rowindex;
            var value = args.newvalue.trim();
            model.timeslices[rowBoundIndex][column] = value;

            //console.log('columnd ', column)

            if (column == 'Timeslice') {
                var tsId = $divTs.jqxGrid('getcellvalue', rowBoundIndex, 'TsId');
                model.tsNames[tsId] = value;
            }
        });

        //SESONS GRID AND EVENTS
        $('#osy-caseForm').undelegate("#osy-addSe", "click");
        $('#osy-caseForm').delegate("#osy-addSe", "click", function (event) {
            //console.log('add season')
            event.preventDefault();
            event.stopImmediatePropagation();
            let defaultSe = DefaultObj.defaultSe(false, model.seCount);
            //console.log('defaultSe ',defaultSe)
            model.seasons.push(JSON.parse(JSON.stringify(defaultSe[0], ['SeId', 'Se', 'Desc'])));

            //update commnames
            model.seNames[defaultSe[0]['SeId']] = defaultSe[0]['Se'];
            //add row
            $divSe.jqxGrid('addrow', null, defaultSe);
            model.seCount++;
            $("#seCount").text(model.seCount);
        });
        
        $('#osy-caseForm').undelegate(".deleteSe", "click");
        $('#osy-caseForm').delegate(".deleteSe", "click", function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var id = $(this).attr('data-id');
            if (id != 0) {
                var seId = $divSe.jqxGrid('getcellvalue', id, 'SeId');
                var rowid = $divSe.jqxGrid('getrowid', id);
                $divSe.jqxGrid('deleterow', rowid);
                model.seasons.splice(id, 1);
                //update techNames
                delete model.seNames[seId];
                //ovdje trebamo izbaciti season iz timeslice definicije
                //update count
                model.seCount--;
                $("#seCount").text(model.seCount);
            }
        });  

        //events by number
        $('#osy-caseForm').undelegate("#osy-addSeNumber", "click");
        $('#osy-caseForm').delegate("#osy-addSeNumber", "click", function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();
            let defaultSe = DefaultObj.defaultSe(false, model.seCount);
            model.seasons.push(JSON.parse(JSON.stringify(defaultSe[0], ['SeId', 'Se', 'Desc'])));
            //update commnames
            model.seNames[defaultSe[0]['SeId']] = defaultSe[0]['Se'];
            //add row
            $divSe.jqxGrid('addrow', null, defaultSe);
            model.seCount++;
            $("#seCount").text(model.seCount);
        });
        
        $('#osy-caseForm').undelegate("#deleteSeNumber", "click");
        $('#osy-caseForm').delegate("#deleteSeNumber", "click", function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();

            let rowId = model.seCount-1;
            if(rowId == 0){
                Message.bigBoxWarning('Warning', 'You cannot delete. At least one season is neccessary.', 3000);
            }else{
                var seId = $divSe.jqxGrid('getcellvalue', rowId, 'SeId');
                $divSe.jqxGrid('deleterow',rowId );
                model.seasons.splice(rowId, 1);
                //update techNames
                delete model.seNames[seId];
                //ovdje trebamo izbaciti season iz timeslice definicije
                $.each(model.timeslices, function (id, obj) {
                    if(obj.SE == seId){
                        obj.SE='SE_0';
                    }
                });
                //update count
                model.seCount--;
                $("#seCount").text(model.seCount);
            }
        }); 
        
        $divSe.on('cellvaluechanged', function (event) {
            var args = event.args;
            var column = event.args.datafield;
            var rowBoundIndex = args.rowindex;
            var value = args.newvalue.trim();
            model.seasons[rowBoundIndex][column] = value;
            if (column == 'Se') {
                var seId = $divSe.jqxGrid('getcellvalue', rowBoundIndex, 'SeId');
                console.log('seId ', seId, value)
                model.seNames[seId] = value;
            }
        });

        //DAY TYPE GRID AND EVENTS
        $('#osy-caseForm').undelegate("#osy-addDt", "click");
        $('#osy-caseForm').delegate("#osy-addDt", "click", function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();
            let defaultDt = DefaultObj.defaultDt(false, model.dtCount);
            model.daytypes.push(JSON.parse(JSON.stringify(defaultDt[0], ['DtId', 'Dt', 'Desc'])));
            //update commnames
            model.dtNames[defaultDt[0]['DtId']] = defaultDt[0]['Dt'];
            //add row
            $divDt.jqxGrid('addrow', null, defaultDt);
            model.dtCount++;
            $("#dtCount").text(model.dtCount);
        });
        
        $('#osy-caseForm').undelegate(".deleteDt", "click");
        $('#osy-caseForm').delegate(".deleteDt", "click", function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var id = $(this).attr('data-id');
            if (id != 0) {
                var dtId = $divDt.jqxGrid('getcellvalue', id, 'DtId');
                var rowid = $divDt.jqxGrid('getrowid', id);
                $divDt.jqxGrid('deleterow', rowid);
                model.seasons.splice(id, 1);
                //update techNames
                delete model.dtNames[dtId];
                //ovdje trebamo izbaciti season iz timeslice definicije
                //update count
                model.dtCount--;
                $("#dtCount").text(model.dtCount);
            }
        });  

                //events by number
        $('#osy-caseForm').undelegate("#osy-addDtNumber", "click");
        $('#osy-caseForm').delegate("#osy-addDtNumber", "click", function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();
            let defaultDt = DefaultObj.defaultDt(false, model.dtCount);
            model.daytypes.push(JSON.parse(JSON.stringify(defaultDt[0], ['DtId', 'Dt', 'Desc'])));
            //update commnames
            model.dtNames[defaultDt[0]['DtId']] = defaultDt[0]['Dt'];
            //add row
            $divDt.jqxGrid('addrow', null, defaultDt);
            model.dtCount++;
            $("#dtCount").text(model.dtCount);
        });
        
        $('#osy-caseForm').undelegate("#deleteDtNumber", "click");
        $('#osy-caseForm').delegate("#deleteDtNumber", "click", function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();

            let rowId = model.dtCount-1;
            if(rowId == 0){
                Message.bigBoxWarning('Warning', 'You cannot delete. At least one day type is neccessary.', 3000);
            }else{
                var dtId = $divDt.jqxGrid('getcellvalue', rowId, 'DtId');
                $divDt.jqxGrid('deleterow',rowId );
                model.daytypes.splice(rowId, 1);
                //update techNames
                delete model.dtNames[dtId];
                //ovdje trebamo izbaciti season iz timeslice definicije
                $.each(model.timeslices, function (id, obj) {
                    if(obj.DT == dtId){
                        obj.DT='DT_0';
                    }
                });
                //update count
                model.dtCount--;
                $("#dtCount").text(model.dtCount);
            }
        }); 
        
        $divDt.on('cellvaluechanged', function (event) {
            var args = event.args;
            var column = event.args.datafield;
            var rowBoundIndex = args.rowindex;
            var value = args.newvalue.trim();
            model.daytypes[rowBoundIndex][column] = value;
            if (column == 'Dt') {
                var dtId = $divDt.jqxGrid('getcellvalue', rowBoundIndex, 'DtId');
                model.dtNames[dtId] = value;
            }
        });

        //DAILY TIME BRACKETS GRID AND EVENTS
        $('#osy-caseForm').undelegate("#osy-addDtb", "click");
        $('#osy-caseForm').delegate("#osy-addDtb", "click", function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();
            let defaultDtb = DefaultObj.defaultDtb(false, model.dtbCount);
            model.dailytimebrackets.push(JSON.parse(JSON.stringify(defaultDtb[0], ['DtbId', 'Dtb', 'Desc'])));
            //update commnames
            model.dtbNames[defaultDtb[0]['DtbId']] = defaultDtb[0]['Dtb'];
            //add row
            $divDtb.jqxGrid('addrow', null, defaultDtb);
            model.dtbCount++;
            $("#dtbCount").text(model.dtbCount);
        });
        
        $('#osy-caseForm').undelegate(".deleteDtb", "click");
        $('#osy-caseForm').delegate(".deleteDtb", "click", function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var id = $(this).attr('data-id');
            if (id != 0) {
                var dtbId = $divDtb.jqxGrid('getcellvalue', id, 'DtbId');
                var rowid = $divDtb.jqxGrid('getrowid', id);
                $divDtb.jqxGrid('deleterow', rowid);
                model.dailytimebrackets.splice(id, 1);
                //update techNames
                delete model.dtbNames[dtbId];
                //ovdje trebamo izbaciti season iz timeslice definicije
                //update count
                model.dtbCount--;
                $("#dtbCount").text(model.dtbCount);
            }
        });  

        //events by number
        $('#osy-caseForm').undelegate("#osy-addDtbNumber", "click");
        $('#osy-caseForm').delegate("#osy-addDtbNumber", "click", function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();
            let defaultDtb = DefaultObj.defaultDtb(false, model.dtbCount);
            model.dailytimebrackets.push(JSON.parse(JSON.stringify(defaultDtb[0], ['DtbId', 'Dtb', 'Desc'])));
            //update commnames
            model.dtbNames[defaultDtb[0]['DtbId']] = defaultDtb[0]['Dtb'];
            //add row
            $divDtb.jqxGrid('addrow', null, defaultDtb);
            model.dtbCount++;
            $("#dtbCount").text(model.dtbCount);
        });
        
        $('#osy-caseForm').undelegate("#deleteDtbNumber", "click");
        $('#osy-caseForm').delegate("#deleteDtbNumber", "click", function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();

            let rowId = model.dtbCount-1;
            var dtbId = $divDtb.jqxGrid('getcellvalue', rowId, 'DtbId');
            if(rowId == 0){
                Message.bigBoxWarning('Warning', 'You cannot delete. At least one daily itme bracket is neccessary.', 3000);
            }else{
                $divDtb.jqxGrid('deleterow',rowId );
                model.dailytimebrackets.splice(rowId, 1);
                //update techNames
                delete model.dtbNames[dtbId];
                //ovdje trebamo izbaciti season iz timeslice definicije
                $.each(model.timeslices, function (id, obj) {
                    console.log('dtbCount ', id, obj, dtbId)
                    if(obj.DTB == dtbId){
                        obj.DTB='DTB_0';
                    }
                });
                //update count
                model.dtbCount--;
                $("#dtbCount").text(model.dtbCount);
            }


        }); 
        
        $divDtb.on('cellvaluechanged', function (event) {
            var args = event.args;
            var column = event.args.datafield;
            var rowBoundIndex = args.rowindex;
            var value = args.newvalue.trim();
            model.dailytimebrackets[rowBoundIndex][column] = value;
            if (column == 'Dtb') {
                var dtbId = $divDtb.jqxGrid('getcellvalue', rowBoundIndex, 'DtbId');
                model.dtbNames[dtbId] = value;
            }
        });

        //COMMODITIES GRID AND EVENTS
        $('#osy-caseForm').undelegate("#osy-addComm", "click");
        $('#osy-caseForm').delegate("#osy-addComm", "click", function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();
            let defaultComm = DefaultObj.defaultComm();
            model.commodities.unshift(JSON.parse(JSON.stringify(defaultComm[0], ['CommId', 'Comm', 'Desc', 'UnitId'])));

            //update commnames
            model.commNames[defaultComm[0]['CommId']] = defaultComm[0]['Comm'];
            //add row
            $divComm.jqxGrid('addrow', null, defaultComm, 'first');
            model.commCount++;
            $("#commCount").text(model.commCount);
        });

        $('#osy-caseForm').undelegate(".deleteComm", "click");
        $('#osy-caseForm').delegate(".deleteComm", "click", function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var id = $(this).attr('data-id');
            var htmlcommId = $(this).attr('data-commId');  
            if (model.commodities.length > 1 && $divComm.jqxGrid('getrows').length>1)  {
                var commId = $divComm.jqxGrid('getcellvalue', id, 'CommId');
                var rowid = $divComm.jqxGrid('getrowid', id);

                //provjera da brisemo tacan commoditu
                if(model.commodities[id].CommId != commId ||commId != htmlcommId){ 
                    Message.bigBoxDanger('Commodity deletion error', `Wrong index!! <b>${model.comms[id].CommId}</b>?`, 3000);
                    return false;
                }

                $divComm.jqxGrid('deleterow', rowid);
                model.commodities.splice(id, 1);
                //update techNames
                delete model.commNames[commId];
                //update count
                model.commCount--;
                $("#commCount").text(model.commCount);
                //izbirsati iz modela za tech nz EAR za izbrisanu emisiju ako je slucajno odabrana za neku tehnologiju
                $.each(model.techs, function (id, techObj) {
                    techObj['IAR'] = techObj['IAR'].filter(item => item !== commId);
                    techObj['OAR'] = techObj['OAR'].filter(item => item !== commId);
                    techObj['EAR'] = techObj['EAR'].filter(item => item !== commId);
                    techObj['INCR'] = techObj['INCR'].filter(item => item !== commId);
                    techObj['ITCR'] = techObj['ITCR'].filter(item => item !== commId);
                });
            }
            else{
                Message.bigBoxWarning('Warning', 'You cannot delete. At least one commodity is neccessary.', 3000);
            }
        });

        $divComm.on('cellvaluechanged', function (event) {
            var args = event.args;
            var column = event.args.datafield;
            var rowBoundIndex = args.rowindex;
            var value = args.newvalue.trim();
            model.commodities[rowBoundIndex][column] = value;
            if (column == 'UnitId') {
                Message.bigBoxWarning('Unit change warninig!', 'Changing commodity unit will not recalculate entered nor default values in the model.', 3000);
            }
            if (column == 'Comm') {
                var commId = $divComm.jqxGrid('getcellvalue', rowBoundIndex, 'CommId');
                model.commNames[commId] = value;
            }
        });

        //EMISSIONS GRID AND EVENTS
        $('#osy-caseForm').undelegate("#osy-addEmis", "click");
        $('#osy-caseForm').delegate("#osy-addEmis", "click", function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();
            let defaultEmi = DefaultObj.defaultEmi();
            model.emissions.push(JSON.parse(JSON.stringify(defaultEmi[0], ['EmisId', 'Emis', 'Desc', 'UnitId'])));
            //update commnames
            model.emiNames[defaultEmi[0]['EmisId']] = defaultEmi[0]['Emis'];
            //add row
            $divEmi.jqxGrid('addrow', null, defaultEmi);
            model.emisCount++;
            $("#emisCount").text(model.emisCount);
            $divEmi.jqxGrid('refresh');
        });

        $('#osy-caseForm').undelegate(".deleteEmis", "click");
        $('#osy-caseForm').delegate(".deleteEmis", "click", function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var id = $(this).attr('data-id');
            if (id != 0) {
                var emisId = $divEmi.jqxGrid('getcellvalue', id, 'EmisId');
                var rowid = $divEmi.jqxGrid('getrowid', id);
                $divEmi.jqxGrid('deleterow', rowid);
                model.emissions.splice(id, 1);
                //update emisnames
                delete model.emiNames[emisId];
                //update count
                model.emisCount--;
                $("#emisCount").text(model.emisCount);

                //izbirsati iz modela za tech nz EAR za izbrisanu emisiju ako je slucajno odabrana za neku tehnologiju
                $.each(model.techs, function (id, techObj) {
                    techObj['EAR'] = techObj['EAR'].filter(item => item !== emisId);
                    model.techs[id]['EAR'] = techObj['EAR'];
                });
            }
        });

        $divEmi.on('cellvaluechanged', function (event) {
            var args = event.args;
            var column = event.args.datafield;
            var rowBoundIndex = args.rowindex;
            var value = args.newvalue.trim();
            model.emissions[rowBoundIndex][column] = value;
            if (column == 'UnitId') {
                Message.bigBoxWarning('Unit change warninig!', 'Changing emission unit will not recalculate entered nor default values in the model.', 3000);
            }
            if (column == 'Emis') {
                var emisId = $divEmi.jqxGrid('getcellvalue', rowBoundIndex, 'EmisId');
                model.emiNames[emisId] = value;
            }
        });

        //STORAGE GRID AND EVENTS
        $('#osy-caseForm').undelegate("#osy-addStg", "click");
        $('#osy-caseForm').delegate("#osy-addStg", "click", function (event) {
            //console.log('add season')
            event.preventDefault();
            event.stopImmediatePropagation();
            let defaultStg = DefaultObj.defaultStg();
            model.stg.push(JSON.parse(JSON.stringify(defaultStg[0], ['StgId', 'Stg', 'Desc',"UnitId", "TTS","TFS", "Operation"])));
            //update stgames
            console.log('defaultStg ',defaultStg)
            model.stgNames[defaultStg[0]['StgId']] = defaultStg[0]['Stg'];
            //add row
            $divStg.jqxGrid('addrow', null, defaultStg);
            model.stgCount++;
            $("#stgCount").text(model.stgCount);
        });
        
        $('#osy-caseForm').undelegate(".deleteStg", "click");
        $('#osy-caseForm').delegate(".deleteStg", "click", function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var id = $(this).attr('data-id');
            //if (id != 0) {
                var stgId = $divStg.jqxGrid('getcellvalue', id, 'StgId');
                var rowid = $divStg.jqxGrid('getrowid', id);
                $divStg.jqxGrid('deleterow', rowid);
                model.stg.splice(id, 1);
                //update techNames
                delete model.stgNames[stgId];
                //update count
                model.stgCount--;
                $("#stgCount").text(model.stgCount);
            //}
        });  
        
        $divStg.on('cellvaluechanged', function (event) {
            var args = event.args;
            var column = event.args.datafield;
            var rowBoundIndex = args.rowindex;
            var value = args.newvalue.trim();
            model.stg[rowBoundIndex][column] = value;
            if (column == 'Stg') {
                var stgId = $divStg.jqxGrid('getcellvalue', rowBoundIndex, 'StgId');
                console.log('stgId ', stgId, value)
                model.stgNames[stgId] = value;
            }
        });


        //SCENARIOS GRID AND EVENTS
        $('#osy-caseForm').undelegate("#osy-addScenario", "click");
        $('#osy-caseForm').delegate("#osy-addScenario", "click", function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();
            let defaultSc = DefaultObj.defaultScenario();
            model.scenarios.push(JSON.parse(JSON.stringify(defaultSc[0], ['ScenarioId', 'Scenario', 'Desc', 'Active'])));
            //add scenario id to caserunByScenario
            model.caserunByScenario[defaultSc[0].ScenarioId] =[];
            $divScenario.jqxGrid('addrow', null, defaultSc);
            model.scenariosCount++;
            $("#scenariosCount").text(model.scenariosCount);
            $divScenario.jqxGrid('refresh');
        });

        $('#osy-caseForm').undelegate(".deleteScenario", "click");
        $('#osy-caseForm').delegate(".deleteScenario", "click", function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var id = $(this).attr('data-id');
            if (id != 0) {
                if(model.caserunByScenario[model.scenarios[id]['ScenarioId']].length != 0){
                    Message.bigBoxDanger('Alert', 
                        `You cannot delete this scenario. It is used in ${model.caserunByScenario[model.scenarios[id]['ScenarioId']]}  caserun(s)! 
                        Plese reomve these scenario from caseruns before deletion.`, null)
                }
                else{
                    let scId = model.scenarios[id]['ScenarioId'];
                    Osemosys.deleteScenarioCaseRuns(model.casename, scId)
                    .then(response=>{
                        //console.log('delete ', response)
                        var rowid = $divScenario.jqxGrid('getrowid', id);
                        $divScenario.jqxGrid('deleterow', rowid);
                        model.scenarios.splice(id, 1);
                        model.scenariosCount--;
                        $("#scenariosCount").text(model.scenariosCount);
                        Message.smallBoxInfo(response.message)
                    })
                    .catch(error => {
                        Message.bigBoxDanger(error);
                    })

                }
            }
        });

        $divScenario.on('cellvaluechanged', function (event) {
            var args = event.args;
            var datafield = event.args.datafield;
            var rowBoundIndex = args.rowindex;
            var value = args.newvalue.trim();
            model.scenarios[rowBoundIndex][datafield] = value;
        });

        //CONSTRAINTS GRID AND EVENTS
        $('#osy-caseForm').undelegate("#osy-addConstraint", "click");
        $('#osy-caseForm').delegate("#osy-addConstraint", "click", function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();
            let defaultConstraint = DefaultObj.defaultConstraint();
            model.constraints.push(JSON.parse(JSON.stringify(defaultConstraint[0], ['ConId', 'Con', 'Desc', 'Tag', 'CM'])));

            $divConstraint.jqxGrid('addrow', null, defaultConstraint);
            $divConstraint.jqxGrid('updatebounddata', 'data');
            model.constraintsCount++;
            $("#constraintsCount").text(model.constraintsCount);
            //$divConstraint.jqxGrid('refresh');
        });

        $('#osy-caseForm').undelegate(".deleteConstraint", "click");
        $('#osy-caseForm').delegate(".deleteConstraint", "click", function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var id = $(this).attr('data-id');
            //no condition needed, we can delete all constraints
            //if(id!=0){
            var conId = $divConstraint.jqxGrid('getcellvalue', id, 'ConId');
            var rowid = $divConstraint.jqxGrid('getrowid', id);
            $divConstraint.jqxGrid('deleterow', rowid);
            model.constraints.splice(id, 1);
            //smanji counter za broj emisjia i update html
            model.constraintsCount--;
            $("#constraintsCount").text(model.constraintsCount);

            //izbirsati iz modela za tech nz EAR za izbrisanu emisiju ako je slucajno odabrana za neku tehnologiju
            // $.each(model.techs, function (id, techObj) {
            //     techObj['EAR'] =  techObj['EAR'].filter(item => item !== emisId);
            //     model.techs[id]['EAR'] = techObj['EAR'];
            // });
            //}
        });

        $divConstraint.on('cellvaluechanged', function (event) {
            var args = event.args;
            var column = event.args.datafield;
            var rowBoundIndex = args.rowindex;
            //console.log('newvalue ', args.newvalue)
            if(typeof args.newvalue !== 'object'){
                var value = args.newvalue.trim();
            }else{
                var value = args.newvalue;
            }
            

            if (column != 'CM' && column != 'Tag') {
                model.constraints[rowBoundIndex][column] = value;
            } else if (column == 'CM') {
                if (value.includes(',') && value) {
                    var array = value.split(',');
                } else if (value) {
                    var array = [];
                    array.push(value);
                } else {
                    var array = [];
                }
                model.constraints[rowBoundIndex][column] = array;
            } else if (column == 'Tag') {
                //console.log('eqyuality ', value.value)
                model.constraints[rowBoundIndex][column] = value.value;
            }
        });

        //TABS CHANGE EVENT
        $(".nav-tabs li a").off('click');
        $('.nav-tabs li a').on("click", function (event, ui) {
            var id = $(this).attr('id');
            // console.log('tab id ', id)
            //update tech grid to update IAR OAR EAR with new added or removed comms and emis
            if (id == 'Techs') {
                //Grid.techsGrid(model.techs, model.commodities, model.emissions, model.commNames, model.emiNames);
                $("#osy-gridTech" ).ready(function() {
                    $divTech.jqxGrid('updatebounddata');
                });   
            }
            else if (id == 'Constraints') {
                $("#osy-gridConstraint" ).ready(function() {
                    $divConstraint.jqxGrid('updatebounddata');
                });
            }
            else if (id == 'Ts') {
                $("#osy-gridTs" ).ready(function() {
                    $divTs.jqxGrid('updatebounddata');
                });
            }
            else if (id == 'Storage') {
                $("#osy-gridStg" ).ready(function() {
                    $divStg.jqxGrid('updatebounddata');
                });
            }
        });

        //YEARS EVENTS
        $("#osy-checkAll").on("click", function (event) {
            event.preventDefault();
            var elements = $('#osy-years').find('input[type=checkbox]');
            $.grep(elements, function (element, index) {
                element.checked = true;
            });
            $("#osy-caseForm").jqxValidator('validateInput', '#osy-years');
        });

        $("#osy-uncheckAll").on("click", function (event) {
            event.preventDefault();
            var elements = $('#osy-years').find('input[type=checkbox]');
            $.grep(elements, function (element, index) {
                element.checked = false;
            });
            $("#osy-caseForm").jqxValidator('validateInput', '#osy-years');
        });

        $("#osy-x2").on("click", function (event) {
            event.preventDefault();
            var elements = $('#osy-years').find('input[type=checkbox]');
            $.grep(elements, function (element, index) {
                if ((index) % 2 == 0)
                    element.checked = true;
            });
            $("#osy-caseForm").jqxValidator('validateInput', '#osy-years');
        });

        $("#osy-x5").on("click", function (event) {
            event.preventDefault();
            var elements = $('#osy-years').find('input[type=checkbox]');
            $.grep(elements, function (element, index) {
                if ((index) % 5 == 0)
                    element.checked = true;
            });
            $("#osy-caseForm").jqxValidator('validateInput', '#osy-years');
        });

        $("#showLog").click(function (e) {
            e.preventDefault();
            $('#definition').html(`
                <h5>${DEF[model.pageId].title}</h5>
                ${DEF[model.pageId].definition}
            `);
            $('#definition').toggle('slow');
        });
    }
}





