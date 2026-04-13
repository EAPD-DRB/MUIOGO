import { Message } from "../../Classes/Message.Class.js";
import { Html } from "../../Classes/Html.Class.js";
import { Base } from "../../Classes/Base.Class.js";
import { Osemosys } from "../../Classes/Osemosys.Class.js";
import { Model } from "../Model/LegacyImport.Model.js";
import { DEF } from "../../Classes/Definition.Class.js";

export default class LegacyImport {
    static async onLoad(){
        Base.getCaseStudies()
        .then(cases =>{
            let model = new Model(cases);
            this.initPage(model);
        })
        .catch(error =>{ 
            Message.danger(error);
        });
    }

    static initPage(model){
        Message.clearMessages();
        Html.title('', model.pageID, 'Import facility with OTOOLE provided xls template');
        Html.importData();
        LegacyImport.initEvents(model);
        loadScript("References/smartadmin/js/plugin/dropzone/dropzone.min.js", Base.uploadXls);
    }

    static refreshPage(){
        Base.getCaseStudies()
        .then(cases =>{
            let model = new Model(cases);
            this.initPage(model);
        })
        .catch(error =>{ 
            Message.danger(error);
        });
    }

    static initEvents(model){
        
        $("#cases").tooltip({ selector: '[data-toggle=tooltip]' });

        $("#casePicker").off('click');
        $("#casePicker, #cases").on('click', '.selectCS', function(e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var casename = $(this).attr('data-ps');
            LegacyImport.refreshPage(casename);
            Message.smallBoxInfo("Case selection", casename + " is selected!", 3000);
        });

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
                { input: '#osy-date', message: "Date is required field!", action: 'change', rule: 'required' }
            ]
        });
 
        $("#osy-import").off('click');
        $("#osy-import").on('click', function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();
            $("#osy-caseForm").jqxValidator('validate')
        });

        $("#osy-caseForm").off('validationSuccess');
        $("#osy-caseForm").on('validationSuccess', function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();
            //Message.clearMessages();

            //console.log('cases ', model.cases)
            var casename = $("#osy-casename").val().trim();
            if(model.cases.includes(casename)){
                Message.smallBoxWarning('Warning', 'Model with same name already exists, please change name.', 5000)
            }
            else{
                $('#modalrestore').modal('toggle');
            }
        });

        $("#osy-newImport").off('click');
        $("#osy-newImport").on('click', function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();
            Message.clearMessages();
            $("#ImportOutput").hide();
            Html.newImportProcess();
            Message.smallBoxInfo("Info", 'You have started new import process', 4000)

        });

        $("#osy-process").off('click');
        $("#osy-process").on('click', function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();
            Message.clearMessages();
            Message.loaderStart('Processing template...')
            var casename = $("#osy-casename").val().trim();
            var desc = $("#osy-desc").val().trim();
            var date = $("#osy-date").val();
            var currency = $("#osy-currency").val();
            var templateName = $("#osy-template").val();
            let data = false;
            if ($('#osy-data').is(":checked")){
                data = true;
            }

            let POSTDATA = {
                "osy-version": "5.0",
                "osy-casename": casename,
                "osy-desc": desc,
                "osy-date": date,
                "osy-currency": currency,
                "osy-template": templateName,
                "osy-data": data
            }
            Osemosys.importTemplate(POSTDATA)
            .then(response => {
                if (response.status_code == "success") {
                    Message.loaderEnd();
                    //console.log('response ', response)
                    $("#ImportOutput").show();
                    $("#osy-importOutput").html('<pre class="log-output">' + response.output + '</pre>');
                    $("#osy-newImport").show();
                    Message.successOsy(response.message);
                    Message.bigBoxSuccess('SUCCESS', response.message, 3000);
                }
            })
            .catch(error => {
                Message.loaderEnd();
                Message.bigBoxDanger('Error message', error, null);
            })
        });

        $("#showLog").click(function (e) {
            e.preventDefault();
            $('#definition').html(`
                <h5>${DEF[model.pageID].title}</h5>
                ${DEF[model.pageID].definition}
            `);
            $('#definition').toggle('slow');
        });
    }
}