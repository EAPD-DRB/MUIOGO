import { Message } from "../../Classes/Message.Class.js";
import { Base } from "../../Classes/Base.Class.js";
import { Html } from "../../Classes/Html.Class.js";
import { Model } from "../Model/Pivot.Model.js";
import { Osemosys } from "../../Classes/Osemosys.Class.js";
import { DEF } from "../../Classes/Definition.Class.js";
import { MessageSelect } from "../../App/Controller/MessageSelect.js"
import { DataModelResult } from "../../Classes/DataModelResult.Class.js";
import { DefaultObj } from "../../Classes/DefaultObj.Class.js";

export default class Pivot {
    static onLoad() {
        Base.getSession()
            .then(response => {
                let casename = response['session'];
                if (casename) {
                    const promise = [];
                    promise.push(casename);
                    const genData = Osemosys.getData(casename, 'genData.json');
                    promise.push(genData);
                    const resData = Osemosys.getResultData(casename, 'resData.json');
                    promise.push(resData);
                    const VARIABLES = Osemosys.getParamFile('Variables.json');
                    promise.push(VARIABLES);
                    const VIEWS = Osemosys.getResultData(casename,'viewDefinitions.json');
                    promise.push(VIEWS);
                    const DATA = Osemosys.getResultData(casename, 'RYT.json');
                    promise.push(DATA);
                    return Promise.all(promise);
                } else {
                    let er = {
                        "message": 'There is no model selected!',
                        "status_code": "CaseError"
                    }
                    return Promise.reject(er);
                    // MessageSelect.init(Pivot.refreshPage.bind(Pivot));
                    // throw new Error('No model selected');
                }
            })
            .then(data => {      
                let [casename, genData, resData, VARIABLES, VIEWS, DATA] = data;         
                let model = new Model(casename, genData, resData, VARIABLES, DATA, VIEWS);
                this.initPage(model);
            })
            .catch(error => {
                if (error.status_code == 'CaseError') {
                    MessageSelect.init(Pivot.refreshPage.bind(Pivot));
                }
                else if (error.status_code == 'ActivityError') {
                    MessageSelect.activity(Pivot.refreshPage.bind(Pivot), error.casename);
                }
                Message.warning(error);
            });
    }

    static refreshPage(casename) {
        Base.setSession(casename)
            .then(response => {
                const promise = [];
                promise.push(casename);
                const genData = Osemosys.getData(casename, 'genData.json');
                promise.push(genData);
                const resData = Osemosys.getResultData(casename, 'resData.json');
                promise.push(resData);
                const VARIABLES = Osemosys.getParamFile('Variables.json');
                promise.push(VARIABLES);
                const VIEWS = Osemosys.getResultData(casename, 'viewDefinitions.json');
                promise.push(VIEWS);
                const DATA = Osemosys.getResultData(casename, 'RYT.json');
                promise.push(DATA);
                return Promise.all(promise);
            })
            .then(data => {
                
                let [casename, genData, resData, VARIABLES, VIEWS, DATA] = data;
                let model = new Model(casename, genData, resData, VARIABLES, DATA, VIEWS);
                model.refreshPage = true;
                this.initPage(model);
                //this.initEvents(model);
            })
            .catch(error => {
                setTimeout(function () {
                    if (error.status_code == 'CaseError') {
                        MessageSelect.init(Pivot.refreshPage.bind(Pivot));
                    }
                    else if (error.status_code == 'ActivityError') {
                        MessageSelect.activity(Pivot.refreshPage.bind(Pivot), error.casename);
                    }
                    Message.warning(error.message);
                }, 500);
            });
    }

    static initPage(model) {
        Message.clearMessages();
        Html.title(model.casename, model.VARNAMES[model.group][model.param], model.group);

        //console.log('model ', model)
        // add Grid-based layout for the PivotPanel
        // wijmo.olap.PivotPanel.controlTemplate = 
        // `<div>  
        //     <div class="field-list-label">  
        //         <label wj-part="g-flds"></label>  
        //     </div>  
        //     <div class="field-list pad">  
        //         <div wj-part="d-fields"></div>  
        //     </div>  
        //     <div class="drag-areas-label">  
        //         <label wj-part="g-drag"></label>  
        //     </div>  
        //     <table>
        //         <tbody>
        //             <tr>
        //                 <td width="50%">
        //                     <div class="filter-list pad">  
        //                     <label>  
        //                         <span class="wj-glyph wj-glyph-filter"></span>   
        //                         <span wj-part="g-flt"></span>  
        //                     </label>  
        //                     <div wj-part="d-filters"></div>  
        //                     </div>  
        //                 </td>
        //                 <td width="50%" style="border-left-style: solid;">
        //                     <div class="column-list pad bdr-left">  
        //                         <label>  
        //                             <span class="wj-glyph">⫴</span>   
        //                             <span wj-part="g-cols"></span>  
        //                         </label>  
        //                         <div wj-part="d-cols"></div>  
        //                     </div> 
        //                 </td>
        //             </tr>
        //             <tr style="border-top-style: solid;">
        //                 <td width="50%">
        //                     <div class="row-list pad bdr-top">  
        //                         <label>  
        //                             <span class="wj-glyph">≡</span>   
        //                             <span wj-part="g-rows"></span>  
        //                         </label>  
        //                         <div wj-part="d-rows"></div>  
        //                     </div>  
        //                 </td>
        //                 <td width="50%" style="border-left-style: solid;">
        //                     <div class="values-list pad bdr-left bdr-top">  
        //                         <label>  
        //                             <span class="wj-glyph">Σ</span>   
        //                             <span wj-part="g-vals"></span>  
        //                         </label>  
        //                         <div wj-part="d-vals"></div>  
        //                     </div> 
        //                 </td>
        //             </tr> 
        //         </tbody>
        //     </table>
        //     <div wj-part="d-prog" class="progress-bar"></div>  
        //     <div class="control-area" style="display:none">  
        //         <label>  
        //             <input wj-part="chk-defer" type="checkbox">   
        //             <span wj-part="g-defer">Defer Updates</span>  
        //         </label>  
        //         <button wj-part="btn-update" class="wj-btn wj-state-disabled" type="button" disabled>
        //             Update  
        //         </button>  
        //     </div>  
        // </div>`;

        // let oldFun = wjChart._SvgRenderEngine.prototype._setText;
        wijmo.chart._SvgRenderEngine.prototype._setText = function (svgTextElement, textString) {
            // Clear the existing content of the SVG text element
            svgTextElement.textContent = '';
        
            // Create a temporary div element to parse and render the HTML
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = textString;
            // Iterate through child nodes of the temporary div
            for (const node of tempDiv.childNodes) {
                if (
                    node.nodeType === Node.ELEMENT_NODE &&
                    node.tagName.toLowerCase() != 'sup' &&
                    node.childNodes.length > 0
                ) {
                    this._setText(svgTextElement, node.innerHTML);
                }
                if (node.nodeType === Node.TEXT_NODE) {
                    // If it's a text node, create a new tspan element
                    const tspan = document.createElementNS(
                    'http://www.w3.org/2000/svg',
                    'tspan'
                    );
                    tspan.textContent = node.textContent;
                    svgTextElement.appendChild(tspan);
                } else if (node.nodeType === Node.ELEMENT_NODE) {
                    // If it's an element, handle specific cases (e.g., superscript)
                    if (node.tagName.toLowerCase() === 'sup') {
                    const tspanSup = document.createElementNS(
                        'http://www.w3.org/2000/svg',
                        'tspan'
                    );
                    tspanSup.setAttribute('baseline-shift', 'super');
                    tspanSup.textContent = node.textContent;
            
                    // Create a new tspan for the entire superscript
                    const tspan = document.createElementNS(
                        'http://www.w3.org/2000/svg',
                        'tspan'
                    );
                    tspan.appendChild(tspanSup);
                    svgTextElement.appendChild(tspan);
                    } else {
                    // For other elements, clone and append them directly to the SVG text element
                    const clonedNode = node.cloneNode(true);
                    svgTextElement.appendChild(clonedNode);
                    }
                }
            }
        };

        //kada mjenjamo case, assertation problem sa wijmo kontrolama
        if(model.refreshPage){      
            wijmo.olap.PivotPanel.disposeAll('#pivotPanel');
            wijmo.olap.PivotGrid.disposeAll('#pivotGrid');
            wijmo.olap.PivotChart.disposeAll('#pivotChart');
            wijmo.input.ComboBox.disposeAll('#cmbChartType');
            wijmo.input.ComboBox.disposeAll('#cmbStackedChart');
            wijmo.input.ComboBox.disposeAll('#cmbViews');
            wijmo.input.AutoComplete.disposeAll('#cmbParams');
        }

        // function parseHtmlData(data){
        //     let props = ['Unit'];
        //     console.log('item[prop] ', item[prop] )
        //     data.forEach(item => props.forEach(prop => item[prop] = wijmo.toPlainText(item[prop])))
        // }

        let app = {};
        app.engine = new wijmo.olap.PivotEngine({
            //itemsSourceChanged: (s,e) => parseHtmlData(s.collectionView.sourceCollection),
            itemsSource: model.pivotData,
            rowFields: ['Case', 'Year'],
            valueFields: ['Value'],
            columnFields: ['Tech'],
            showRowTotals: 'None',
            showColumnTotals:'None',

        });

        //wijmo.olap.PivotEngine.invalidate()
        //console.log('app.engine.fields ', app.engine.fields)
        app.engine.fields.getField('Unit').isContentHtml = true;
        app.engine.fields.getField('Tech').isContentHtml = true;
        app.engine.fields.getField('Tech Desc').isContentHtml = true;


        model.DEFAULTVIEW = app.engine.viewDefinition;

        app.panel = new wijmo.olap.PivotPanel('#pivotPanel',{
            itemsSource: app.engine
        });

        //New fieled formats
        let _oldEditField = app.engine.editField;
        app.engine.editField = function(fld) {
            _oldEditField.call(this, fld);
            if(fld.dataType !== wijmo.DataType.Number) {
                return;
            }
            var format = wijmo.Control.getControl('div[wj-part="div-fmt"]');
            addFormats(format);
        }

        function addFormats(format) {
            const view = format.collectionView;
            var newFmt = view.addNew();
            newFmt.key = "Float (n3)";
            newFmt.val = "n3";
            newFmt.all = true; // always set it to true
            var newFmt = view.addNew();
            newFmt.key = "Float (n4)";
            newFmt.val = "n4";
            newFmt.all = true; // always set it to true
            view.commitNew();
        }
        ///////////end field formats


        //03022025 postavljenje default formata Value grupe u gridu
        // Access the pivot engine and loop through fields
        // let decimalpoints = localStorage.getItem("osy-decimalpoints");
        // if(!decimalpoints){
        //     decimalpoints = 'n2';
        // }
        // console.log('decimalpoints ', decimalpoints)    

        //app.engine.fields.getField('Unit').isContentHtml = true;

        // app.engine.fields.forEach(function (field) {
        //     //console.log('field ', field)
        //     if (field.header === 'Value') {
        //         // Set the format to display numbers with 2 decimal places
        //         field.format = model.stgDecimalPoints;
        //     }
        // });

        //app.engine.valueFields.format =  model.stgDecimalPoints;
        app.engine.fields.getField('Value').format = model.stgDecimalPoints;

        // Refresh the pivot engine to apply the changes
        // pivotEngine.refresh();


        app.pivotGrid = new wijmo.olap.PivotGrid('#pivotGrid', {
            itemsSource: app.engine,
            collapsibleSubtotals: true,
            showSelectedHeaders: 'All',  
        });

        app.pivotChart = new wijmo.olap.PivotChart('#pivotChart', {
            //header: 'Country GDP',
            itemsSource: app.engine,
            showTitle: false,
            legendPosition: 4,
            stacking: "Stacked"
        });

        //app.pivotChart.dataLabel.position = 'Top';
        // app.pivotChart.flexChart.palette = wijmo.chart.Palettes.midnight
        app.pivotChart.flexChart.palette = model.ColorSchemes.osyScheme;

        // app.pivotChart.flexChart.axisX.itemFormatter = function (engine, label) {
        //     label.text = wijmo.toPlainText(label.text);
        //     return label;
        // };

        // app.cmbParams = new wijmo.input.AutoComplete('#cmbParams', {
        app.cmbParams = new wijmo.input.ComboBox('#cmbParams', {
            itemsSource: model.VARIABLEOBJECT,
            dropDownCssClass: 'wj-vars',
            displayMemberPath: 'name',
            selectedValuePath: 'value',
            selectedValue: 'ANC',
            selectedIndexChanged: function (s, e) {  
                if(s.selectedValue != null && model.TriggerUpdate){
                    Pivot.updateParam(s.selectedValue, app, model);
                }     
                
            }
        });

        app.cmbChartType = new wijmo.input.ComboBox('#cmbChartType', {
            itemsSource: model.ChartTypes,
            displayMemberPath: 'name',
            selectedValuePath: 'value',
            selectedIndexChanged: function (s, e) {      
                if(s.selectedValue == 1){
                    app.pivotChart.rotated = 1;
                }
                app.pivotChart.chartType = s.selectedValue;
            }
        });

        app.cmbStackedChart  = new wijmo.input.ComboBox('#cmbStackedChart', {
            itemsSource: 'Stacked,Stacked100pc,None'.split(','),
            selectedIndexChanged: function(s, e) {
                //console.log(s, e)
                app.pivotChart.stacking = s.text;
            }
        });

        app.cmbViews = new wijmo.input.ComboBox('#cmbViews', {
            itemsSource: model.VIEWS,
            displayMemberPath: 'osy-viewname',
            selectedValuePath: 'osy-viewId',
            selectedIndexChanged: function (s, e) {   
                if(model.TriggerUpdate){
                    Pivot.updateView(s.selectedValue, app, model)
                }   
            }
        });

        this.initEvents(model, app);
    }

    static initEvents(model, app) {


        //console.log('model ', model)
        $("#casePicker").off('click');
        $("#casePicker").on('click', '.selectCS', function (e) {
            e.preventDefault();
            e.stopImmediatePropagation();
            var casename = $(this).attr('data-ps');
            Pivot.refreshPage(casename);
            Html.updateCasePicker(casename);
            Message.smallBoxConfirmation("Confirmation!", "Model " + casename + " selected!", 3500);
        });

        $("#createView").jqxValidator({
            hintType: 'label',
            animationDuration: 500,
            rules: [
                { input: '#osy-viewname', message: "View name is required field!", action: 'keyup', rule: 'required' },
                {
                    input: '#osy-viewname', message: "Entered view name is not allowed!", action: 'keyup', rule: function (input, commit) {
                        var casename = $("#osy-viewname").val();
                        var result = (/^[a-zA-Z0-9-_ ]*$/.test(casename));
                        return result;
                    }
                }
            ]
        });

        $("#btnSaveView").off('click');
        $("#btnSaveView").on('click', function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();
            $("#createView").jqxValidator('validate')
        });

        $("#createView").off('validationSuccess');
        $("#createView").on('validationSuccess', function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();

            var viewname = $("#osy-viewname").val();
            var desc = $("#osy-viewdesc").val();
            let param = model.param;
            let group = model.group;
            let viewId = DefaultObj.getId('VIEW');

            app.engine.fields.getField('Unit').isContentHtml = true;
            //ako nije demand jer ne zavisi od T
            if(param == 'D'){
                app.engine.fields.getField('Comm').isContentHtml = true;
                app.engine.fields.getField('Comm Desc').isContentHtml = true;
            }
            else if(group == "RYC"){
                app.engine.fields.getField('Comm').isContentHtml = true;
                app.engine.fields.getField('Comm Desc').isContentHtml = true;
            }
            else if(group == "RYE"){
                app.engine.fields.getField('Emi').isContentHtml = true;
                app.engine.fields.getField('Emi Desc').isContentHtml = true;
            }
            else{
                app.engine.fields.getField('Tech').isContentHtml = true;
                app.engine.fields.getField('Tech Desc').isContentHtml = true;
            }


            let POSTDATA = {
                "osy-viewId": viewId,
                "osy-viewname": viewname,
                "osy-viewdesc": desc,
                "osy-viewdef": app.engine.viewDefinition
            }

            Osemosys.saveView(model.casename, POSTDATA, param)
            .then(response => {
                Message.clearMessages();
                Message.bigBoxSuccess('Model message', response.message, 3000);
                POSTDATA['osy-varId'] = param;
                model.VIEWS.push(POSTDATA);
                // Html.ddlViews(model.VIEWS[model.param]);
                //Html.ddlViews(model.VIEWS);
                app.cmbViews.itemsSource = model.VIEWS;
                $('#createView').modal('toggle');
            })
            .catch(error => {
                Message.bigBoxDanger('Error message', error, null);
            })
        });

        $("#deleteView").off('click');
        $("#deleteView").on('click', function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();
            if ( model.VIEW != 'null' &&  model.VIEW != null){

                let viewUpdate = [];
                $.each(model.VIEWS, function (id, obj) {
                
                    if(obj['osy-viewId'] == model.VIEW){
                        model.VIEWS.splice(id, 1)
                        return false;
                    }
                    if(obj['osy-varId'] == model.param){
                        viewUpdate.push(obj);
                    }
                });
                // Html.ddlViews(model.VIEWS[model.param]);
                app.cmbViews.itemsSource = model.VIEWS;
                app.cmbViews.selectedValue = 'null';
                Osemosys.updateViews(model.casename, viewUpdate, model.param)
                .then(response => {
                    app.engine.viewDefinition = model.DEFAULTVIEW;
                    app.pivotChart.header = '';
                    Message.clearMessages();
                    Message.smallBoxInfo('Model message', response.message, 3000);   
                })
                .catch(error => {
                    Message.bigBoxDanger('Error message', error, null);
                })
            }else{
                Message.smallBoxWarning('Model message', 'Default view cannot be deleted!', 3000);
            }
        });

        // NOTE: requires jszip, wijmo.xlsx, and wijmo.grid.xlsx
        $("#xlsExport").off('click');
        $('#xlsExport').on('click', function () {
            var book = wijmo.grid.xlsx.FlexGridXlsxConverter.save(app.pivotGrid, {
                includeColumnHeaders: true,
                includeRowHeaders: true
            });
            book.sheets[0].name = 'PivotGrid';
            book.save('PivotGrid.xlsx');
        });
        
        $("#pngExport").off('click');
        $('#pngExport').on('click', function () {
            app.pivotChart.saveImageToFile('FlexChart.png');
        });

        $("#showRowTotals").off('click');
        $("#showRowTotals").click(function (e) {
            app.engine.showRowTotals = e.target.checked ?
                wijmo.olap.ShowTotals.Subtotals : wijmo.olap.ShowTotals.None;
        });
        
        $("#showColumnTotals").off('click');
        $("#showColumnTotals").click(function (e) {
            app.engine.showColumnTotals = e.target.checked ?
                wijmo.olap.ShowTotals.Subtotals : wijmo.olap.ShowTotals.None;
        });

        $("#hideLegend").off('click');
        $("#hideLegend").click(function (e) {
            app.pivotChart.showLegend = e.target.checked ?
                'Never' : 'Auto';
        });

        $("#showLog").off('click');
        $("#showLog").click(function (e) {
            e.preventDefault();
            $('#definition').html(`${DEF[model.group][model.param].definition}`);
            $('#definition').toggle('slow');
        });
    }

    static updateParam(param, app, model, view=null){
        Message.clearMessages();
        Message.loaderStart('Preparing pivot data...')
        model.group = model.VARGROUPS[param]['group'];
        model.param = param;
        Osemosys.getResultData(model.casename, model.group+'.json')
        .then(DATA => {
            //console.log('DATA ', DATA, model.group)
            if (DATA !== null && model.param in DATA && Object.getOwnPropertyNames(DATA[model.param]).length != 0){
                let pivotData = DataModelResult.getPivot(DATA, model.genData, model.VARIABLES, model.group, model.param);
                model.pivotData = pivotData;
                app.engine.itemsSource = model.pivotData;


                //console.log('pivot source ok')
                if (model.group == 'R'){
                    app.engine.columnFields.push('Optimal');
                    app.engine.rowFields.push('Case');
                    app.engine.valueFields.push('Value');
                }
                else if(model.group == 'RY' ){
                    app.engine.rowFields.push('Case','Year');
                    app.engine.valueFields.push('Value');
                }
                else if(model.group == 'RYE' ){
                    app.engine.columnFields.push('Emi');
                    app.engine.rowFields.push('Case','Year');
                    app.engine.valueFields.push('Value');
                }
                else if(model.group == 'RYCn' ){
                    app.engine.columnFields.push('Con');
                    app.engine.rowFields.push('Case','Year');
                    app.engine.valueFields.push('Value');
                }
                else if(model.group == 'RYS' ){
                    app.engine.columnFields.push('Stg');
                    app.engine.rowFields.push('Case','Year');
                    app.engine.valueFields.push('Value');
                }
                else if (model.group == 'RYCTs' || model.group == 'RYC'){
                    app.engine.columnFields.push( 'Comm');
                    app.engine.rowFields.push('Case','Year');
                    app.engine.valueFields.push('Value');
                }

                else if(model.group == "RYTC" || model.group == 'RYTCMTs' ){
                    //console.log(app.engine.columnFields)
                    app.engine.columnFields.push('Comm');
                    //console.log('com tech added')
                    app.engine.rowFields.push('Case','Year');
                    app.engine.valueFields.push('Value');
                }
                else{
                    //console.log('else')
                    app.engine.columnFields.push('Tech');
                    app.engine.rowFields.push('Case', 'Year');
                    app.engine.valueFields.push('Value');
                }

                                //decimal points
                //console.log('field ', field)
                // app.engine.fields.forEach(function (field) {
                //     if (field.header === 'Value') {
                //         // Set the format to display numbers with 2 decimal places
                //         field.format = decimalpoints;
                //     }
                // });

                //console.log('app.engine.valueFields ', app.engine.valueFields, model.stgDecimalPoints)
                // app.engine.valueFields.format =  model.stgDecimalPoints;
                // app.engine.refresh();
                app.engine.fields.getField('Value').format = model.stgDecimalPoints;

                //console.log('fields ok')
                //update defaul model
                model.DEFAULTVIEW = JSON.parse(JSON.stringify(app.engine.viewDefinition));
                //model.DEFAULTVIEW = app.engine.viewDefinition;
                app.pivotChart.header = ''; 

                if(view != null){
                    Html.title(model.casename, model.VARNAMES[model.group][model.param], model.group+' - '+view['osy-viewname'] +' view');
                    app.engine.viewDefinition = view['osy-viewdef'];
                    app.pivotChart.header = view['osy-viewname'];
                }
                else{
                    model.TriggerUpdate = false;
                    app.cmbViews.selectedValue = 'null';
                    model.VIEW = 'null';
                    model.TriggerUpdate = true;
                    Html.title(model.casename, model.VARNAMES[model.group][model.param], model.group+' - Default view');
                }
                //console.log('view ok')
                app.engine.fields.getField('Unit').isContentHtml = true;
                if(model.group != "RYS" && model.group != "RYCTs" && model.group != "RYC" && model.group != "RYE" && model.group != "RYCn" && model.group != "R"  && model.group != "RY"){
                    app.engine.fields.getField('Tech').isContentHtml = true;
                    app.engine.fields.getField('Tech Desc').isContentHtml = true;
                }
                if(model.group == "RYTC" || model.group == "RYCTs" || model.group == "RYTCMTs" || model.group == "RYC"){
                    app.engine.fields.getField('Comm').isContentHtml = true;
                    app.engine.fields.getField('Comm Desc').isContentHtml = true;
                }
                if(model.group == "RYTE" || model.group == "RYTEM" || model.group == "RYE"){
                    app.engine.fields.getField('Emi').isContentHtml = true;
                    app.engine.fields.getField('Emi Desc').isContentHtml = true;
                }
                if(model.group == "RYS"){
                    app.engine.fields.getField('Stg').isContentHtml = true;
                    app.engine.fields.getField('Stg Desc').isContentHtml = true;
                }
                if(model.group == "RYCn"){
                    app.engine.fields.getField('Con').isContentHtml = true;
                    app.engine.fields.getField('Con Desc').isContentHtml = true;
                }

                Message.loaderEnd();
            }
            else{
                Message.dangerOsy("Results do not contain values for variable <b>"+model.VARNAMES[model.group][model.param] + "</b> please check input data and rerun the model.")
                Message.loaderEnd();
            }

        })
        .catch(error => {
            Message.danger(error.message);
        }); 
    }

    static updateView(viewId, app, model){
        model.VIEW = viewId;
        if(model.VIEW == 'null'){
            app.engine.viewDefinition = model.DEFAULTVIEW;
            app.pivotChart.header = '';
            if(model.group != "RYS" && model.group != "RYCTs"){
                app.engine.fields.getField('Tech').isContentHtml = true;
                app.engine.fields.getField('Tech Desc').isContentHtml = true;
            }
            if(model.group == "RYTC" || model.group == "RYCTs" || model.group == "RYTCMTs"){
                app.engine.fields.getField('Comm').isContentHtml = true;
                app.engine.fields.getField('Comm Desc').isContentHtml = true;
            }
            if(model.group == "RYTE" || model.group == "RYTEM"){
                app.engine.fields.getField('Emi').isContentHtml = true;
                app.engine.fields.getField('Emi Desc').isContentHtml = true;
            }
            if(model.group == "RYS"){
                app.engine.fields.getField('Stg').isContentHtml = true;
                app.engine.fields.getField('Stg Desc').isContentHtml = true;
            }
            Html.title(model.casename, model.VARNAMES[model.group][model.param], model.group+' Default view');
        }
        else{
            $.each(model.VIEWS, function (id, obj) {
                if(obj['osy-viewId'] == model.VIEW){
                    let param = obj['osy-varId'];
                    // console.log('model.VIEW ', model.VIEW)
                    // console.log('model.VIEWS ', model.VIEWS)
                    // console.log('obj ', obj)
                    // console.log('param ', param)
                    if (model.VAR_IDS.includes(param)){

                        if(param != model.param){
                            model.TriggerUpdate = false;
                            app.cmbParams.selectedValue = param;
                            model.TriggerUpdate = true;
                            Pivot.updateParam(param, app, model, obj);
                        }
                        else{
                            //console.log('OVDJE RADI HTML!!!')
                            app.engine.viewDefinition = obj['osy-viewdef'];
                            app.pivotChart.header = obj['osy-viewname'];
                            Html.title(model.casename, model.VARNAMES[model.group][model.param], model.group+' - '+obj['osy-viewname'] +' view');
                            // app.engine.fields.getField('Unit').isContentHtml = true;
                            // app.engine.fields.getField('Tech').isContentHtml = true;
                            // app.engine.fields.getField('Tech Desc').isContentHtml = true;
                            if(model.group != "RYS" && model.group != "RYCTs"){
                                app.engine.fields.getField('Tech').isContentHtml = true;
                                app.engine.fields.getField('Tech Desc').isContentHtml = true;
                            }
                            if(model.group == "RYTC" || model.group == "RYCTs" || model.group == "RYTCMTs"){
                                app.engine.fields.getField('Comm').isContentHtml = true;
                                app.engine.fields.getField('Comm Desc').isContentHtml = true;
                            }
                            if(model.group == "RYTE" || model.group == "RYTEM"){
                                app.engine.fields.getField('Emi').isContentHtml = true;
                                app.engine.fields.getField('Emi Desc').isContentHtml = true;
                            }
                            if(model.group == "RYS"){
                                app.engine.fields.getField('Stg').isContentHtml = true;
                                app.engine.fields.getField('Stg Desc').isContentHtml = true;
                            }

                        } 
                    }
                    else{
                        model.param = param;
                        Message.dangerOsy("Selected view is not longer suported. Please delete view and create new with existing variables.")
                    }
                }
            });
        }
    }
}
