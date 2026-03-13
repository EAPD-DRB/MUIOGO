import { Message } from "../../Classes/Message.Class.js";
import { Html } from "../../Classes/Html.Class.js";
import { Base } from "../../Classes/Base.Class.js";
import { SyncS3 } from "../../Classes/SyncS3.Class.js";
import { Model } from "../Model/Home.Model.js";
import { DEF } from "../../Classes/Definition.Class.js";
import { Navbar } from "./Navbar.js";
import { Sidebar } from "./Sidebar.js";
import { Osemosys } from "../../Classes/Osemosys.Class.js";
import { Routes } from "../../Routes/Routes.Class.js";

export default class Home {
    static async onLoad() {
        if (Base.AWS_SYNC == 1 && Base.INIT_SYNC) {
            $('#loadermain h4').text('Syncronizing with S3 Bucket!');
            $('#loadermain').show();
            try {
                const syncResponse = await Base.initSyncS3();
                Message.smallBoxInfo('Sync message', syncResponse.message, 3000);
                Base.INIT_SYNC = 0;
            } catch (syncError) {
                Message.danger(syncError);
            }
        }
        try {
            const response = await Base.getSession();
            const casename = response.session;
            $('#loadermain').hide();
            const cases = await Base.getCaseStudies();
            const model = new Model(casename, cases);
            this.initPage(model);
        } catch (error) {
            Message.danger(error);
        }
    }

    static initPage(model){
        Message.clearMessages();
        Navbar.initPage(model.casename);
        // Sidebar.Load(model.genData, model.PARAMETERS, model.VARIABLES);
        Sidebar.Reload(model.casename);
        Html.renderModels(model.cases, model.casename);
        Home.initEvents(model);
        loadScript("References/smartadmin/js/plugin/dropzone/dropzone5.min.js", Base.uploadFunction);
    }

    static async refreshPage(casename) {
        try {
            await Base.setSession(casename);
            const cases = await Base.getCaseStudies();
            const model = new Model(casename, cases);
            this.initPage(model);
        } catch (error) {
            Message.danger(error);
        }
    }

    static initEvents(model){
        
        $("#cases").tooltip({ selector: '[data-toggle=tooltip]' });

        $("#casePicker, #cases").off('click', '.selectCS');
        $("#casePicker, #cases").on('click.homeSelect', '.selectCS', async function(e) {
            //console.log('model ', model)
            e.preventDefault();
            e.stopImmediatePropagation();
            var casename = $(this).attr('data-ps');
            try {
                const genData = await Osemosys.getData(casename, 'genData.json');
                Home.refreshPage(casename);
                Message.smallBoxInfo("Case selection", casename + " is selected!", 3000);
                if (parseFloat(genData["osy-version"]) < 4.5) {
                    Message.bigBoxWarning("Warning", "You have selected a model created in a earlier version of this UI. In order to update to the current version click <b>Update model</b> on the configuration page.", 10000);
                }
            } catch (error) {
                Message.danger(error);
            }
        });

        $("#cases").off('click.homeEdit', '.editPS');
        $("#cases").on('click.homeEdit', '.editPS', async function(e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var casename = $(this).attr('data-ps');
            Html.updateCasePicker(casename);
            try {
                await Base.setSession(casename);
                $('#Navi>li').removeClass('active');
                $('#Navi').children('li').eq(2).addClass('active');
                hasher.setHash("#");
                hasher.setHash("#AddCase");
            } catch (error) {
                Message.danger(error);
            }
        });

        //copy case
        $(document).off('click', '.copyCS');
        $("#cases").off('click', '.copyCS');
        $("#cases").on('click.homeCopy', '.copyCS', async function(e) {
            e.stopImmediatePropagation();
            var casename = $(this).attr('data-ps');
            if (casename !== model.casename) {
                Message.bigBoxWarning('Copy message',
                    'Select <b>' + casename + '</b> first to copy it.', 4000);
                return;
            }
            try {
                const response = await Base.copyCaseStudy(casename);
                Message.clearMessages();
                if (response.status_code == "success") {
                    Message.bigBoxSuccess('Copy message', response.message, 3000);
                    Html.apendModel(casename + '_copy');
                    Html.appendCasePicker(casename + '_copy', null);
                    if (Base.AWS_SYNC == 1) {
                        await SyncS3.deleteResultsPreSync(casename);
                        SyncS3.uploadSync(casename + '_copy');
                    }
                }
                if (response.status_code == "warning") {
                    Message.bigBoxWarning('Copy message', response.message, 3000);
                }
            } catch (error) {
                Message.danger(error);
            }
        });

        //get descrition
        $("#cases").off('click.homeDescription', '.descriptionPS');
        $("#cases").on('click.homeDescription', '.descriptionPS', async function(e) {
            var titleps = $(this).attr('data-ps');
            try {
                const response = await Base.getCaseDesc(titleps);
                Message.clearMessages();
                $('#mdescriptionps').html(response.desc);
            } catch (error) {
                Message.danger(error);
            }
            $('#mtitleps_desc').html('<i class="ace-icon fa fa-info-circle"></i>  ' + titleps);
        });

        //delete case
        $(document).off('click', '.deleteModel');
        $("#cases").off('click', '.deleteModel');
        $("#cases").on('click.homeDelete', '.deleteModel', function(e){
            var casename = $(this).attr('data-ps');
            if (casename !== model.casename) {
                Message.bigBoxWarning('Delete message',
                    'Select <b>' + casename + '</b> first to delete it.', 4000);
                e.stopImmediatePropagation();
                return;
            }
            $.SmartMessageBox({
                title : "Confirmation Box!",
                content : "You are about to delete <b class='danger'>" + casename + "</b> Model! Are you sure?",
                buttons : '[No][Yes]'
            }, async function(ButtonPressed) {
                if (ButtonPressed === "Yes") {
                    try {
                        const response = await Base.deleteCaseStudy(casename);
                        Message.clearMessages();
                        if (response.status_code == "success_session") {
                            Message.bigBoxSuccess('Delete message', response.message, 3000);
                            Message.info("Please select existing or create new case to proceed!");
                            Sidebar.Reload(null);
                            Html.removeCase(casename);
                            if (Base.AWS_SYNC == 1) {
                                SyncS3.deleteSync(casename);
                            }
                        }
                        if (response.status_code == "info") {
                            Message.info(response.message);
                        }
                        if (response.status_code == "warning") {
                            Message.warning(response.message);
                        }
                    } catch (error) {
                        Message.danger(error);
                    }
                }
                if (ButtonPressed === "No") {
                    Message.bigBoxInfo("Confirmation message", "You pressed No...", 3000);
                }
            });
            //e.preventDefault();
            e.stopImmediatePropagation();
        });

        //Search cases
        $('#CaseSearch').off('keyup.homeSearch');
        $('#CaseSearch').on('keyup.homeSearch', function () {
            var query = $.trim($('#CaseSearch').val()).toLowerCase();
            //console.log('query ', query)
            $('.selectCS').each(function () {
                var $this = $(this);
                if ($this.text().toLowerCase().indexOf(query) === -1)
                    $this.closest('.panel').fadeOut();
                else $this.closest('.panel').fadeIn();
            });
        })

        $("#showLog").off('click.homeLog');
        $("#showLog").on('click.homeLog', function (e) {
            e.preventDefault();
            $('#definition').html(`
                <h5>${DEF[model.pageID].title}</h5>
                ${DEF[model.pageID].definition}
            `);
            $('#definition').toggle('slow');
        });
    }
}
