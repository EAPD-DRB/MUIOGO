import { Message } from "../../Classes/Message.Class.js";
import { Base } from "../../Classes/Base.Class.js";
import { Html } from "../../Classes/Html.Class.js";
import { Model } from "../Model/Navbar.Model.js";

export class Navbar {
    static initPage(casename){
        Base.getCaseStudies()
        .then(cases => {
            let model = new Model(cases, casename);
            Html.renderCasePicker(model.cases, model.casename);
            this.initEvents();
        })
        .catch(error =>{ 
            Message.danger(error);
        });
    }

    static refreshPage(casename){
    }

    static initEvents(){
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