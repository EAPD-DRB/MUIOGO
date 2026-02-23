import { Html } from "./Html.Class.js";
export class Message {

    static isInitialEmptyState(message) {
        if (!message) return true;

        const text = message.toString().toLowerCase().trim();

        return (
            text === "" ||
            text === "error!" ||
            text.includes("no selected parameters") ||
            text.includes("undefined") ||
            text.includes("null")
        );
    }
    static clearMessages() {
        $("#osy-warning").empty();
        $("#osy-success").empty();
        $("#osy-danger").empty();
        $("#osy-info").empty();

        $("#osy-warning-transparent").empty();
        $("#osy-success-transparent").empty();
        $("#osy-danger-transparent").empty();
        $("#osy-info-transparent").empty();
        $("#osy-default-transparent").empty();
    }

    static warning(message) {
        $("#osy-warning").html(`<div class="alert alert-warning fade in">
                                        <button class="close" data-dismiss="alert">×</button>
                                        <i class="fa-fw fa fa-warning"></i>
                                        <strong>Warning!</strong> `+ message + `
                                    </div>`);
    }

    static success(message) {
        $("#osy-success").html(`<div class="alert alert-success fade in">
                                        <button class="close" data-dismiss="alert">×</button>
                                        <i class="fa-fw fa fa-check"></i>
                                        <strong>Success!</strong> `+ message + `
                                    </div>`);
    }

    static info(message) {
        $("#osy-info").html(`<div class="alert alert-info fade in">
                                        <button class="close" data-dismiss="alert">×</button>
                                        <i class="fa-fw fa fa-info"></i>
                                        <strong>Info!</strong> `+ message + `
                                    </div>`);
    }

    static danger(message) {

    if (Message.isInitialEmptyState(message)) {
        message = "No case loaded. Please create or load a case to begin.";
    }

    $("#osy-danger").html(`<div class="alert alert-danger fade in">
            <button class="close" data-dismiss="alert">×</button>
            <i class="fa-fw fa fa-times"></i>
            <strong>Notice:</strong> `+ message + `
        </div>`);
}

    static warningOsy(message) {
        $("#osy-warning-transparent").html(`
                                    <div class="alert alert-warning-osy fade in">
                                        <button class="close" data-dismiss="alert">×</button>
                                        <i class="fa-fw fa fa-warning fa-2x warning"></i>
                                        <strong>Warning!</strong> <i style="color:grey">`+ message + `</i>
                                    </div>`);
    }

    static successOsy(message) {
        $("#osy-success-transparent").html(`
                                    <div class="alert alert-success-osy fade in">
                                        <button class="close" data-dismiss="alert">×</button>
                                        <i class="fa-fw fa fa-check fa-2x success"></i>
                                        <strong>Success!</strong><i style="color:grey">`+ message + `</i>
                                    </div>`);
    }

    static infoOsy(message) {
        $("#osy-info-transparent").html(`<div class="alert alert-info-osy fade in">
                                        <button class="close" data-dismiss="alert">×</button>
                                        <i class="fa-fw fa fa-info fa-2x info"></i>
                                        <strong>Info!</strong> <i style="color:grey">`+ message + `</i>
                                    </div>`);
    }

    static dangerOsy(message) {

    if (Message.isInitialEmptyState(message)) {
        message = "No case loaded. Please create or load a case to begin.";
    }

    $("#osy-danger-transparent").html(`<div class="alert alert-danger-osy fade in">
            <button class="close" data-dismiss="alert">×</button>
            <i class="fa-fw fa fa-exclamation-triangle fa-2x danger"></i>
            <strong>Notice:</strong> <i style="color:grey">`+ message + `</i>
        </div>`);
}

    static bigBoxDanger(title, content, timeout) {
        $.bigBox({
            title: title,
            content: `<i class='fa fa-clock-o'></i> <i>${content}</i>`,
            color: "#C46A69",
            icon: "fa fa-warning shake animated",
            //number : "1",
            timeout: timeout
        });
    }

    static bigBoxInfo(title, content, timeout) {
        $.bigBox({
            title: title,
            content: content,
            color: "#3276B1",
            icon: "fa fa-bell swing animated",
            //number : "2"
            timeout: timeout
        });
    }

    static bigBoxDefault(title, content, timeout) {
        $.bigBox({
            title: title,
            content: content,
            color: "#4a5168",
            icon: "fa fa-info-circle swing animated",
            //number : "2"
            timeout: timeout
        });
    }

    static bigBoxWarning(title, content, timeout) {
        $.bigBox({
            title: title,
            content: content,
            color: "#C79121",
            timeout: timeout,
            icon: "fa fa-shield fadeInLeft animated",
            //number : "3"
        });
    }

    static bigBoxSuccess(title, content, timeout) {
        $.bigBox({
            title: title,
            content: content,
            timeout: timeout,
            color: "#659265",
            icon: "fa fa-shield fadeInLeft animated",
            //number : "3"
        });
    }

    static smallBoxSuccess(title, content, timeout) {
        $.smallBox({
            title: title,
            timeout: timeout,
            content: `<i class='fa fa-clock-o'></i> <i>${content}</i>`,
            color: "#659265",
            iconSmall: "fa fa-check fa-2x fadeInRight animated"
        });
    }

    static smallBoxWarning(title, content, timeout) {
        $.smallBox({
            title: title,
            timeout: timeout,
            content: `<i class='fa fa-exclamation-triangle warning'></i> <i>${content}</i>`,
            color: "#C79121",
            iconSmall: "fa fa-exclamation-triangle fa-2x fadeInLeft animated shake",
        });
    }

    static smallBoxDanger(title, content, timeout) {
        $.smallBox({
            title: title,
            timeout: timeout,
            content: `<i class='fa fa-clock-o'></i> <i>${content}</i>`,
            color: "#C46A69",
            iconSmall: "fa fa-warning shake animated fa-2x ",
        });
    }

    static smallBoxInfo(title, content, timeout) {
        $.smallBox({
            title: title,
            timeout: timeout,
            content: `<i class='fa fa-clock-o'></i> <i>${content}</i>`,
            color: "#5384AF",
            iconSmall: "fa fa-bell fadeInRight animated"
        });
    }

    static smallBoxConfirmation(title, content, timeout) {
        $.smallBox({
            title: title,
            timeout: timeout,
            content: `<i class='fa fa-clock-o'></i> <i>${content}</i>`,
            color: "#296191",
            iconSmall: "fa fa-thumbs-up bounce animated"
        });
    }

    static SmartMessageBoxDDL(cases, init_f) {
        var casesArr = '"[' + cases.join('][') + ']"';
        $.SmartMessageBox({
            title: "<i class='fa fa-exclamation-triangle danger'></i>No active Model.",
            content: "Please select one of existing models to proceed.",
            buttons: "[Continue]",
            input: "select",
            //options : "[Costa Rica][United States][Autralia][Spain]"
            options: casesArr,
            //options : "[Costa Rica][United States][Autralia][Spain]"
        }, function (ButtonPress, Value) {
            // html.updateCasePicker(Value);
            Html.updateCasePicker(Value);
            init_f(Value);
            //alert(ButtonPress + " " + Value);
        });
    }

    static ddlActivity(cases, init_f) {
        var casesArr = '"[' + cases.join('][') + ']"';
        $.SmartMessageBox({
            title: "<i class='fa fa-exclamation-triangle danger'></i>Selected model has no activity defines.",
            content: "Please select model to proceed.",
            buttons: "[Continue]",
            input: "select",
            //options : "[Costa Rica][United States][Autralia][Spain]"
            options: casesArr,
        }, function (ButtonPress, Value) {
            Html.updateCasePicker(Value);
            init_f(Value);
            //alert(ButtonPress + " " + Value);
        });
    }

    static confirmationDialog(title, msg, model, $divTech, id, rowid, techId) {
        console.log('MODEL ', model)
        $.SmartMessageBox({
            title : "<i class='fa fa-exclamation-triangle danger'></i> " +title,
            content : msg,
            buttons : '[No][Yes]'
        }, function(ButtonPressed) {
            if (ButtonPressed === "Yes") {

                $.smallBox({
                    title : "Confirmation",
                    content : "<i class='fa fa-clock-o'></i> <i>Technology is deleted!</i>",
                    color : "#5384AF",
                    iconSmall : "fa fa-check fa-2x fadeInRight animated",
                    timeout : 4000
                });
                $divTech.jqxGrid('deleterow', rowid);
                model.techs.splice(id, 1);
                //update techNames
                delete model.techNames[techId];
                //update count
                model.techCount--;
                $("#techCount").text(model.techCount);
                //izbrisati iz model constraints eventualne tehnologijel koje smo izbrisali
                $.each(model.constraints, function (id, conObj) {
                    conObj['CM'] = conObj['CM'].filter(item => item !== techId);
                });
            }
            if (ButtonPressed === "No") {
                $.smallBox({
                    title : "Confirmation",
                    content : "<i class='fa fa-clock-o'></i> <i>Deletion is aborted!</i>",
                    color : "#C79121",
                    iconSmall : "fa fa-times fa-2x fadeInRight animated",
                    timeout : 4000
                });
            }

        });
    }

    static resMessage(message) {
        $("#res-message").html(
            `<div class="alert alert-osy-second-color fade in">
                <button class="close" data-dismiss="alert">×</button>
                 <i style="color:grey">`+ message + `
            </div>`);
    }

    static loaderStart(msg){
        $('#loadermain h4').text(msg); 
        $('#loadermain').show();
    }
    static loaderEnd(){
        $('#loadermain').hide();
    }
}

