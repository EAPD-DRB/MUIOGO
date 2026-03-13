import { Message } from "../../Classes/Message.Class.js";
import { Base } from "../../Classes/Base.Class.js";
import { Html } from "../../Classes/Html.Class.js";
import { Model } from "../Model/ViewData.Model.js";
import { Grid } from "../../Classes/Grid.Class.js";
import { Osemosys } from "../../Classes/Osemosys.Class.js";
import { DEF } from "../../Classes/Definition.Class.js";
import { MessageSelect } from "./MessageSelect.js";

export default class ViewData {
    static async onLoad() {
        Message.loaderStart('Loading data...');
        try {
            const response = await Base.getSession();
            const casename = response['session'];
            if (casename) {
                const [genData, viewData, viewTEData, PARAMETERS] = await Promise.all([
                    Osemosys.getData(casename, 'genData.json'),
                    Osemosys.viewData(casename),
                    Osemosys.viewTEData(casename),
                    Osemosys.getParamFile(),
                ]);
                const model = new Model(casename, genData, viewData, viewTEData, PARAMETERS);
                this.initPage(model);
                this.initEvents(model);
            } else {
                Message.loaderEnd();
                MessageSelect.init(ViewData.refreshPage.bind(ViewData));
            }
        } catch (error) {
            Message.loaderEnd();
            Message.warning(error);
        }
    }

    static initPage(model) {
        Message.clearMessages();
        Html.title(model.casename, 'View input data', 'Technologies, commodities, emissions');
        Html.ddlTechs(model.techs, model.techs[0]['TechId']);

        let $divGrid = $('#osy-gridViewData');
        let $divTEGrid = $('#osy-gridRT');

        var daRTGrid = new $.jqx.dataAdapter(model.srcRTGrid, { autoBind: true });
        console.log('daRTGrid', daRTGrid.records);
        Grid.Grid($divTEGrid, daRTGrid, model.columnsRT, { height:200});
        Grid.applyTEviewDataFilter($divTEGrid);

        var daGrid = new $.jqx.dataAdapter(model.srcGrid);
        Grid.Grid($divGrid, daGrid, model.columns,  { height:610});
        $divGrid.jqxGrid('hidecolumn', 'TechName');
        Grid.applyViewDataFilter($divGrid, model.years);
    }

    static async refreshPage(casename) {
        Message.loaderStart('Loading data...');
        Pace.restart();
        try {
            await Base.setSession(casename);
            const [genData, viewData, viewTEData, PARAMETERS] = await Promise.all([
                Osemosys.getData(casename, 'genData.json'),
                Osemosys.viewData(casename),
                Osemosys.viewTEData(casename),
                Osemosys.getParamFile(),
            ]);
            const model = new Model(casename, genData, viewData, viewTEData, PARAMETERS);
            this.initPage(model);
            this.initEvents(model);
        } catch (error) {
            Message.loaderEnd();
            Message.warning(error);
        }
    }

    static initEvents(model) {

        let $divGrid = $('#osy-gridViewData');
        let $divTEGrid = $('#osy-gridRT');

        $("#casePicker").off('click');
        $("#casePicker").on('click', '.selectCS', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var casename = $(this).attr('data-ps');
            Html.updateCasePicker(casename);
            ViewData.refreshPage(casename);
            Message.smallBoxConfirmation("Confirmation!", "Model " + casename + " selected!", 3500);
        });

        $('input[type=radio][name=bytype]').change(function (e) {

            if (this.value == 'Tech') {
                let firstTech = model.techs[0]['TechId'];
                $('#osy-techs').show();
                $('#osy-emis').hide();
                $('#osy-comms').hide();
                Html.ddlTechs(model.techs, firstTech);
                model.srcGrid.root = firstTech;
                $divGrid.jqxGrid('updatebounddata');
                $divGrid.jqxGrid('hidecolumn', 'TechName');
                $divGrid.jqxGrid('showcolumn', 'CommName');
                $divGrid.jqxGrid('showcolumn', 'EmisName');
                Grid.applyViewDataFilter($divGrid, model.years);

                model.srcRTGrid.root = firstTech;
                $divTEGrid.jqxGrid('updatebounddata');
                Grid.applyTEviewDataFilter($divTEGrid);
                $('#gridRT').show();
            }
            else if (this.value == 'Comm') {
                let firstComm = model.comms[0]['CommId'];
                $('#osy-techs').hide();
                $('#osy-emis').hide();
                $('#osy-comms').show();
                Html.ddlComms(model.comms, firstComm);
                model.srcGrid.root = firstComm;
                $divGrid.jqxGrid('updatebounddata');
                $divGrid.jqxGrid('hidecolumn', 'CommName');
                $divGrid.jqxGrid('showcolumn', 'TechName');
                $divGrid.jqxGrid('showcolumn', 'EmisName');
                Grid.applyViewDataFilter($divGrid, model.years);

                $('#gridRT').hide();
            }
            else if (this.value == 'Emi') {
                let firstEmi = model.emis[0]['EmisId'];
                $('#osy-techs').hide();
                $('#osy-emis').show();
                $('#osy-comms').hide();
                Html.ddlEmis(model.emis, firstEmi);
                model.srcGrid.root = firstEmi;
                $divGrid.jqxGrid('updatebounddata');
                $divGrid.jqxGrid('hidecolumn', 'EmisName');
                $divGrid.jqxGrid('showcolumn', 'CommName');
                $divGrid.jqxGrid('showcolumn', 'TechName');
                Grid.applyViewDataFilter($divGrid, model.years);

                model.srcRTGrid.root = firstEmi;
                $divTEGrid.jqxGrid('updatebounddata');
                Grid.applyTEviewDataFilter($divTEGrid);
                $('#gridRT').show();
            }

        });

        $("#osy-techs").off('change');
        $('#osy-techs').on('change', function () {
            Pace.restart();
            //$('#loadermain h4').text("Changing dispatch order" )
            //$('#loadermain').show(); 
            let tech = this.value;
            model.srcGrid.root = tech;
            $divGrid.jqxGrid('updatebounddata');
            Grid.applyViewDataFilter($divGrid, model.years);

            model.srcRTGrid.root = tech;
            $divTEGrid.jqxGrid('updatebounddata');
            Grid.applyTEviewDataFilter($divTEGrid);

            Message.smallBoxConfirmation("Confirmation!", "Technology <b>" + model.TechName[tech] + "</b> selected!", 3500);
            //$('#loadermain').hide(); 

            res = !res;
            if (!res) {
                $("#resizeColumns").trigger("click");
            }
            $("#resizeColumns").trigger("click");
        });

        $("#osy-emis").off('change');
        $('#osy-emis').on('change', function () {
            let emi = this.value;
            model.srcGrid.root = emi;
            $divGrid.jqxGrid('updatebounddata');
            Grid.applyViewDataFilter($divGrid, model.years);

            model.srcRTGrid.root = emi;
            $divTEGrid.jqxGrid('updatebounddata');
            Grid.applyTEviewDataFilter($divTEGrid);

            Message.smallBoxConfirmation("Confirmation!", "Emission <b>" + model.EmiName[emi] + "</b> selected!", 3500);
        });

        $("#osy-comms").off('change');
        $('#osy-comms').on('change', function () {
            let comm = this.value;
            model.srcGrid.root = comm;
            $divGrid.jqxGrid('updatebounddata');
            Grid.applyViewDataFilter($divGrid, model.years);

            Message.smallBoxConfirmation("Confirmation!", "Commodity <b>" + model.CommName[comm] + "</b> selected!", 3500);
        });

        let pasteEvent = false;
        $divGrid.bind('keydown', function (event) {
            pasteEvent = false;
            var ctrlDown = false, ctrlKey = 17, cmdKey = 91, vKey = 86, cKey = 67;
            var key = event.charCode ? event.charCode : event.keyCode ? event.keyCode : 0;
            if (key == vKey) {
                pasteEvent = true;
                Message.smallBoxInfo('View data form', 'Copy/paste option is not allowed on this form', 3000);
            }
        }).on('cellvaluechanged', async function (event) {
            if (!pasteEvent) {
                Pace.restart();

                var args = event.args;
                var year = event.args.datafield;
                var rowBoundIndex = args.rowindex;
                var value = args.newvalue;

                var ScId = $divGrid.jqxGrid('getcellvalue', rowBoundIndex, 'ScId');
                var GroupId = $divGrid.jqxGrid('getcellvalue', rowBoundIndex, 'groupId');
                var ParamId = $divGrid.jqxGrid('getcellvalue', rowBoundIndex, 'param');
                var CommId = $divGrid.jqxGrid('getcellvalue', rowBoundIndex, 'CommId');
                var EmisId = $divGrid.jqxGrid('getcellvalue', rowBoundIndex, 'EmisId');
                var TsId = $divGrid.jqxGrid('getcellvalue', rowBoundIndex, 'TsId');
                var TechId = $divGrid.jqxGrid('getcellvalue', rowBoundIndex, 'TechId');
                let dataType = $('input[type=radio][name=bytype]:checked').val();

                let object;
                if (dataType == 'Tech') {
                    object = model.gridData[dataType][TechId];
                }
                else if (dataType == 'Comm') {
                    object = model.gridData[dataType][CommId];
                }
                if (dataType == 'Emi') {
                    object = model.gridData[dataType][EmisId];
                }
                //update model grid
                $.each(object, function (id, obj) {
                    if (obj.ScId === ScId &&
                        obj.groupId === GroupId &&
                        obj.param === ParamId &&
                        obj.CommId === CommId &&
                        obj.EmisId === EmisId &&
                        obj.TsId === TsId) {
                        if (value) {
                            obj[year] = value;
                        } else {
                            obj[year] = 0;
                        }
                    }
                });

                try {
                    const response = await Osemosys.updateViewData(model.casename, year, ScId, GroupId, ParamId, TechId, CommId, EmisId, TsId, value);
                    Message.bigBoxSuccess('Model message', response.message, 3000);
                    if (Base.AWS_SYNC == 1) {
                        Base.updateSync(model.casename, GroupId + ".json");
                    }
                } catch (error) {
                    Message.bigBoxDanger('Error message', error, null);
                }
            }
        });

        let pasteRTEvent = false;
        $divTEGrid.bind('keydown', function (event) {
            pasteRTEvent = false;
            var ctrlDown = false, ctrlKey = 17, cmdKey = 91, vKey = 86, cKey = 67;
            var key = event.charCode ? event.charCode : event.keyCode ? event.keyCode : 0;
            if (key == vKey) {
                pasteRTEvent = true;
                Message.smallBoxInfo('View data form', 'Copy/paste option is not allowed on this form', 3000);
            }
        }).on('cellvaluechanged', async function (event) {
            if (!pasteRTEvent) {
                Pace.restart();

                var args = event.args;
                var rowBoundIndex = args.rowindex;
                var value = args.newvalue;

                var ScId = $divTEGrid.jqxGrid('getcellvalue', rowBoundIndex, 'ScId');
                var GroupId = $divTEGrid.jqxGrid('getcellvalue', rowBoundIndex, 'groupId');
                var ParamId = $divTEGrid.jqxGrid('getcellvalue', rowBoundIndex, 'param');

                let dataType = $('input[type=radio][name=bytype]:checked').val();

                var TechId;
                var CommId;
                var EmisId;
                let object;
                if (dataType == 'Tech') {
                    TechId = $("#osy-techs").val();
                    object = model.gridRTData[dataType][TechId];
                    CommId = null;
                    EmisId = null;
                }
                else if (dataType == 'Comm') {
                    CommId = $("#osy-comms").val();
                    object = model.gridRTData[dataType][CommId];
                    TechId = null;
                    EmisId = null;
                }
                else if (dataType == 'Emi') {
                    EmisId = $("#osy-emis").val();
                    object = model.gridRTData[dataType][EmisId];
                    CommId = null;
                    TechId = null;
                }
                //update model grid
                $.each(object, function (id, obj) {
                    if (obj.ScId === ScId &&
                        obj.groupId === GroupId &&
                        obj.param === ParamId) {
                        if (value) {
                            obj['value'] = value;
                        } else {
                            obj['value'] = 0;
                        }
                    }
                });

                try {
                    const response = await Osemosys.updateTEViewData(model.casename, ScId, GroupId, ParamId, TechId, EmisId, value);
                    Message.bigBoxSuccess('Model message', response.message, 3000);
                    if (Base.AWS_SYNC == 1) {
                        Base.updateSync(model.casename, GroupId + ".json");
                    }
                } catch (error) {
                    Message.bigBoxDanger('Error message', error, null);
                }
            }
        });

        let res = true;
        $("#resizeColumns").off('click');
        $("#resizeColumns").click(function () {
            // if(res){
            //     $divGrid.jqxGrid('autoresizecolumn', 'Sc',"cells" );
            //     //$divGrid.jqxGrid('autoresizecolumn', 'groupName');
            //     $divGrid.jqxGrid('autoresizecolumn', 'paramName',"cells");
            //     $divGrid.jqxGrid('autoresizecolumn', 'UnitId',"cells" );
            //     $divGrid.jqxGrid('autoresizecolumn', 'TechName',"cells" );
            //     $divGrid.jqxGrid('autoresizecolumn', 'CommName',"cells" );
            //     $divGrid.jqxGrid('autoresizecolumn', 'EmisName',"cells" );
            //     $divGrid.jqxGrid('autoresizecolumn', 'ConName',"cells" );
            //     $divGrid.jqxGrid('autoresizecolumn', 'Timeslice',"cells" );
            //     $divGrid.jqxGrid('autoresizecolumn', 'MoId' );

            //     $divTEGrid.jqxGrid('autoresizecolumn', 'Sc',"cells" );
            //     $divTEGrid.jqxGrid('autoresizecolumn', 'paramName',"cells" );
            //     $divTEGrid.jqxGrid('autoresizecolumn', 'UnitId',"cells" );
            //     $divTEGrid.jqxGrid('autoresizecolumn', 'value',"cells" );
            // }
            // else{
            $divGrid.jqxGrid('autoresizecolumns');
            $divTEGrid.jqxGrid('autoresizecolumns');
            //}
            res = !res;
        });

        // $("#xlsAll").off('click');
        // $("#xlsAll").click(function (e) {
        //     e.preventDefault();
        //     $divGrid.jqxGrid('exportdata', 'xls', 'View data by sets (time dependant)');
        //     setTimeout(function(){$divTEGrid.jqxGrid('exportdata', 'xls', 'View data by sets');}, 1000)
            
        // });

        $("#xlsAll").off('click');
        $("#xlsAll").click(async function (e) {
            e.preventDefault();
            let rytData = $divGrid.jqxGrid('getdisplayrows');
            let data = JSON.parse(JSON.stringify(rytData, ['Sc', 'paramName', 'UnitId', 'TechName', "CommName", "EmisName", "ConName", 'Ts', 'MoId'].concat(model.years)));

            try {
                const response = await Base.prepareCSV(model.casename, data);
                Message.smallBoxInfo('Case study message', response.message, 3000);
                $('#csvDownload').trigger('click');
                window.location = $('#csvDownload').attr('href');
            } catch (error) {
                Message.bigBoxDanger('Error message', error, null);
            }
        });


        $("#decUp").off('click');
        $("#decUp").on('click', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            model.d++;
            model.decimal = 'd' + parseInt(model.d);
            $divGrid.jqxGrid('refresh');
            $divTEGrid.jqxGrid('refresh');
        });

        $("#decDown").off('click');
        $("#decDown").on('click', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            model.d--;
            model.decimal = 'd' + parseInt(model.d);
            $divGrid.jqxGrid('refresh');
            $divTEGrid.jqxGrid('refresh');
        });

        $("#showLog").click(function (e) {
            e.preventDefault();
            $('#definition').html(`
                <h5>${DEF[model.group].title}</h5>
                ${DEF[model.group].definition}
            `);
            $('#definition').toggle('slow');
        });

        Message.loaderEnd();
    }
}