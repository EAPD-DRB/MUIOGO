import { Html } from "./Html.Class.js";

export class SmartAdmin {

    static rangeSlider(years){
        var d5_instance = $("#range-slider-1").data("ionRangeSlider");

        let from = Math.min(...years);
        let to = Math.max(...years);

        if(d5_instance){
            d5_instance.update({
                from: from,
                to: to,
            });
            Html.years(from, to, years);
        }else{
            $("#range-slider-1").ionRangeSlider({
                skin: "modern",
                min: "2000",
                max: "2070",
                from: from,
                to: to,
                type: 'double',
                step: 1,
                postfix: " Year;",
                prettify: false,
                grid: true,
                inputValuesSeparator: '',
                onStart: function (data) {
                    Html.years(from, to, years);
                },
                onFinish: function (data) {
                    Html.years(data.from, data.to, years);
                    $("#osy-caseForm").jqxValidator('validateInput', '#osy-years');
                }
            });
        }
    }
}