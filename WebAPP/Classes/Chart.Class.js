export class Chart {
    static theme() {
        let theme = "bootstrap";
        return theme
    }
    static Chart($div, dataAdapter, unit, series, dataField = 'Year', minValue = 0) {

        var settings = {
            title: "",
            description: "",
            theme: this.theme(),
            enableAnimations: true,
            showLegend: true,
            padding: { left: 5, top: 5, right: 5, bottom: 5 },
            titlePadding: { left: 10, top: 0, right: 0, bottom: 10 },
            source: dataAdapter,
            enableCrosshairs: true,
            crosshairsDashStyle: '2,2',
            crosshairsLineWidth: 1.0,
            crosshairsColor: '#888888',
            borderLineColor: 'transparent',
            xAxis:
            {
                dataField: dataField,
                displayField: 'Tech',
                type: 'basic',
                visible: true,
                valuesOnTicks: true,
                labels: 'Years',
                // {
                //     formatFunction: function (value) {
                //         return value.getDate();
                //     }
                // }
                // {
                //     formatFunction: function (value) {
                //         return value.getDate();
                //     }
                // }
                // minValue: 2000,
                // maxValue: 2020,
                // //gridLinesInterval: 24, 
                // flip: false,
                // //valuesOnTicks: true,
                // rangeSelector: {
                //     serieType: 'line',
                //     unitInterval: 2,
                //     padding: { /*left: 0, right: 0,*/ top: 10, bottom: 0 },
                //     // Uncomment the line below to render the selector in a separate container
                //     //renderTo: $('#selectorContainer'),
                //     //backgroundColor: "#E1E1E6",
                //     size: 55,
                // }
            },
            valueAxis:
            {
                // unitInterval: 500,
                minValue: minValue,
                maxValue: 'auto',
                title: { text: 'Installed power [MW]' },
                displayValueAxis: true,
                description: "",
                axisSize: 'auto',
            },
            colorScheme: 'scheme09',
            seriesGroups:
                [

                    {
                        type: 'column',
                        valuesOnTicks: false,
                        columnsGapPercent: 10,
                        seriesGapPercent: 5,
                        columnsMaxWidth: 100,
                        columnsMinWidth: 5,
                        toolTipFormatFunction: function (value, index, data, d) {
                            return data.displayText + ' ' + parseFloat(value).toFixed(2);
                        },

                        formatSettings:
                        {
                            thousandsSeparator: ',',
                            decimalPlaces: 2,
                            sufix: ' ',
                        },

                        labels: {
                            visible: false,
                            verticalAlignment: 'center',
                            offset: { x: 0, y: 0 },
                            angle: 0,
                            formatSettings:
                            {
                                thousandsSeparator: ',',
                                decimalPlaces: 2,
                                sufix: ' ',
                            },
                        },
                        formatFunction:
                            function (value, index, data) {
                                if (value > 0) {
                                    return parseFloat(value).toFixed(2) + ' ' + data.displayText;
                                } else {
                                    return '';
                                }
                            },
                        series: series
                        // [
                        //     { dataField: 'SearchNonPaid', displayText: 'Desktop Search' },
                        //     { dataField: 'SearchPaid', displayText: 'Mobile Search' },
                        //     { dataField: 'Referral', displayText: 'Social media' }
                        // ]
                    }
                ]
        };
        $div.jqxChart(settings);
    }

    static RESChart($div, model){

        let linkData = {
            arrowlen: 20,
            source: model.source,
            target: model.target,
            value:  model.value,
            label:  model.labelLink,
        }
        if(model.settings.Colors){
            linkData.color = model.colorLink;
        }

        var data = [{
            type: "sankey",
            arrangement: "fixed",
            orientation: "h",
            valueformat: ".0f",
            valuesuffix: "",
            node: {
                pad: 20,
                thickness: 20,
                line: { color: "#555c77", width: 2 },
                label: model.label,
                color: model.color
            },
            link: linkData
        }];        
        var layout = {
            title: "",
            showlegend: true,
            //width: 1118,
            height: model.height,
            //autozise: true,
            font: {
                size: 12
            },
        }
        
        Plotly.react($div, data, layout)
    }

    static SankeyChart($div, model){

        var data = [{
            type: "sankey",
            //arrangement: "snap",
            orientation: "h",
            valueformat: ".0f",
            valuesuffix: "",
            node: {
              pad: 15,
              thickness: 30,
              line: {
                color: "black",
                width: 0.5
              },
                label: model.label,
                color: model.color
            },
          
            link: {
                source: model.source[model.sc][model.year],
                target: model.target[model.sc][model.year],
                value:  model.value[model.sc][model.year],
                label:  model.labelLink[model.sc][model.year]
            }
        }];

        var layout = {
            title: "",
            showlegend: true,
            font: {
                size: 12
            }
        }
        
        Plotly.react($div, data, layout)
    }
}