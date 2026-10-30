export class JqxSources {

    static srcTech(techs) {
        var srcTech = {
            localdata: techs,
            datatype: "json",
            datafields:
                [
                    // name - determines the field's name.
                    // value - the field's value in the data source.
                    // values - specifies the field's values.
                    // values.source - specifies the foreign source. The expected value is an array.
                    // values.value - specifies the field's value in the foreign source. 
                    // values.name - specifies the field's name in the foreign source. 
                    // When the adapter is loaded, each record will have a field call
                    //The "Country" for each record comes from the countriesAdapter where the record's "countryCode" from gridAdapter 
                    //matches to the "value" from countriesAdapter. 
                    { name: 'TechId', type: 'string' },
                    { name: 'Tech', type: 'string' },
                    { name: 'Desc', type: 'string' },
                    { name: 'TG', type: 'array' },
                    { name: 'CapUnitId', type: 'string' },
                    { name: 'ActUnitId', type: 'string' },
                    { name: 'IAR', type: 'array' },
                    { name: 'OAR', type: 'array' },
                    { name: 'INCR', type: 'array' },
                    { name: 'ITCR', type: 'array' },
                    { name: 'EAR', type: 'array' }
                ],
        }
        return srcTech;
    }

    static srcActTech(techs) {
        var srcTech = {
            localdata: techs,
            datatype: "json",
            datafields:
                [
                    { name: 'TechId', type: 'string' },
                    { name: 'Tech', type: 'string' }
                ],
        }
        return srcTech;
    }

    static srcTechGroup(groups) {
        var srcTechGroup = {
            localdata: groups,
            datatype: "json",
            datafields:
                [
                    { name: 'TechGroupId', type: 'string' },
                    { name: 'TechGroup', type: 'string' },
                    { name: 'Desc', type: 'string' }
                ],
        }
        return srcTechGroup;
    }

    static srcSe(seasons) {
        var srcSe = {
            localdata: seasons,
            datatype: "json",
            datafields:
                [
                    { name: 'SeId', type: 'string' },
                    { name: 'Se', type: 'number' },
                    { name: 'Desc', type: 'string' }
                ],
        }
        return srcSe;
    }

    static srcDt(daytypes) {
        var srcDt = {
            localdata: daytypes,
            datatype: "json",
            datafields:
                [
                    { name: 'DtId', type: 'string' },
                    { name: 'Dt', type: 'number' },
                    { name: 'Desc', type: 'string' }
                ],
        }
        return srcDt;
    }

    static srcDtb(dailytimebrackets) {
        var srcDtb = {
            localdata: dailytimebrackets,
            datatype: "json",
            datafields:
                [
                    { name: 'DtbId', type: 'string' },
                    { name: 'Dtb', type: 'number' },
                    { name: 'Desc', type: 'string' }
                ],
        }
        return srcDtb;
    }

    static srcTs(timeslices) {
        var srcTs = {
            localdata: timeslices,
            datatype: "json",
            datafields:
                [
                    { name: 'TsId', type: 'string' },
                    { name: 'Ts', type: 'string' },
                    { name: 'Desc', type: 'string' },
                    { name: 'SE', type: 'string' },
                    { name: 'DT', type: 'string' },
                    { name: 'DTB', type: 'string' },
                ],
        }
        return srcTs;
    }

    static srcComm(commodities, daBalanceLevels) {
        var srcComm = {
            localdata: commodities,
            datatype: "json",
            datafields:
                [
                    { name: 'CommId', type: 'string' },
                    { name: 'Comm', type: 'string' },
                    { name: 'Desc', type: 'string' },
                    { name: 'BalanceLevel', type: 'string' },
                    { name: 'BalanceLevelName', value: 'BalanceLevel', values: { source: daBalanceLevels, value: 'id', name: 'name' } },
                    { name: 'UnitId', type: 'string' }
                ],
        }
        return srcComm;
    }

    
    static srcBalanceLevel(levels) {
        var srcLevels = {
            localdata: levels,
            datatype: "json",
            datafields:
                [
                    { name: 'id', type: 'string' },
                    { name: 'name', type: 'string' }
                ],
        };
        return srcLevels;
    }

    static srcEmi(emissions) {
        var srcEmi = {
            localdata: emissions,
            datatype: "json",
            datafields:
                [
                    { name: 'EmisId', type: 'string' },
                    { name: 'Emis', type: 'string' },
                    { name: 'Desc', type: 'string' },
                    { name: 'UnitId', type: 'string' }
                ],
        }
        return srcEmi;
    }

    static srcUnit(units) {
        var srcUnits = {
            localdata: units,
            datatype: "json",
            datafields:
                [
                    { name: 'id', type: 'string' },
                    { name: 'name', type: 'string' },
                    { name: 'group', type: 'string' }
                ],
        };
        return srcUnits;
    }

    static srcTag(tags) {
        var srcTags = {
            localdata: tags,
            datatype: "json",
            datafields:
                [
                    { name: 'id', type: 'number' },
                    { name: 'name', type: 'string' },
                ],
        };
        return srcTags;
    }

    static srcStorageOperations(operations) {
        var srcTags = {
            localdata: operations,
            datatype: "json",
            datafields:
                [
                    { name: 'id', type: 'number' },
                    { name: 'name', type: 'string' },
                ],
        };
        return srcTags;
    }

    static srcStorage(storages) {
        var srcStorage = {
            localdata: storages,
            datatype: "json",
            datafields:
                [
                    { name: 'StgId', type: 'string' },
                    { name: 'Stg', type: 'string' },
                    { name: 'Desc', type: 'string' },
                    { name: 'TTS', type: 'string' },
                    { name: 'TFS', type: 'string' },
                    { name: 'UnitId', type: 'string' },
                    { name: 'Operation', type: 'string' }
                ],
        }
        return srcStorage;
    }

    static srcScenario(scenarios) {
        var srcScenario = {
            localdata: scenarios,
            datatype: "json",
            datafields:
                [
                    { name: 'ScenarioId', type: 'string' },
                    { name: 'Scenario', type: 'string' },
                    { name: 'Desc', type: 'string' }
                ],
        }
        return srcScenario;
    }

    static srcConstraint(cons, daTags) {

        var srcConstraint = {
            localdata: cons,
            datatype: "json",
            datafields:
                [
                    { name: 'ConId', type: 'string' },
                    { name: 'Con', type: 'string' },
                    { name: 'Desc', type: 'string' },
                    { name: 'TagName', value: 'Tag', values: { source: daTags, value: 'id', name: 'name' } },
                    { name: 'Tag', type: 'number' },
                    { name: 'CM', type: 'array' }
                ],
        }
        return srcConstraint;
    }

    static srcIndicators(indicators, daTypes) {
        var srcIndicators = {
            localdata: indicators,
            datatype: "json",
            datafields:
                [
                    { name: 'IndicatorId', type: 'string' },
                    { name: 'Indicator', type: 'string' },
                    { name: 'Desc', type: 'string' },
                    { name: 'TypeName', value: 'IndicatorTypeId', values: { source: daTypes, value: 'id', name: 'value' } },
                    { name: 'IndicatorTypeId', type: 'string' },
                    { name: 'Techs', type: 'array' },
                    { name: 'Comms', type: 'array' }
                ],
        }
        return srcIndicators;
    }

    static srcIndType(tags) {
        var srcTags = {
            localdata: tags,
            datatype: "json",
            datafields:
                [
                    { name: 'id', type: 'string' },
                    { name: 'value', type: 'string' },
                ],
        };
        return srcTags;
    }

    static techGridColumns(daComms) {
        var ddlComms = function (row, value, editor) {
            editor.jqxDropDownList({ source: daComms, displayMember: 'Comm', valueMember: 'CommId', checkboxes: true });
        }

        var initeditor = function (row, cellvalue, editor, celltext, pressedkey) {
            // set the editor's current value. The callback is called each time the editor is displayed.
            var items = editor.jqxDropDownList('getItems');
            editor.jqxDropDownList('uncheckAll');
            if (Array.isArray(cellvalue)) {
                var values = cellvalue;
            } else {
                var values = cellvalue.split(/,\s*/);
            }

            for (var j = 0; j < values.length; j++) {
                for (var i = 0; i < items.length; i++) {
                    if (items[i].label === values[j]) {
                        editor.jqxDropDownList('checkIndex', i);
                    }
                }
            }
        }

        var getEditorValue = function (row, cellvalue, editor) {
            // return the editor's value.
            return editor.val();
        }

        var validation_1 = function (cell, value) {
            var validationResult = true;
            var rows = $('#osy-gridTech').jqxGrid('getboundrows');
            var currentRowId = String($('#osy-gridTech').jqxGrid('getrowid', cell.row));
            for (var i = 0; i < rows.length; i++) {
                if (rows[i].Tech.trim() == value.trim() && String(rows[i].uid) !== currentRowId) {
                    validationResult = false;
                    break;
                }
            };

            if (validationResult == false) {
                Message.smallBoxWarning("Input message", "Technology name should be unique!", 3000);
                return { result: false, message: "" };
            }
            return true;
        }

        var cellsrendererbutton = function (row, column, value) {
            var id = $("#osy-gridTech").jqxGrid('getrowid', row);
            if (id == 0) {
                return '';
            }
            return '<span style="padding:10px; width:100%; border:none" class="btn btn-default deleteTech" data-id=' + id + '><i class="fa  fa-minus-circle danger"></i>Delete</span>';
        }

        let columnsTech = [
            { text: 'techId', datafield: 'TechId', hidden: true },
            { text: 'Technology', datafield: 'Tech', width: '13%', align: 'center', cellsalign: 'left', validation: validation_1 },
            { text: 'Description', datafield: 'Desc', width: '15%', align: 'center', cellsalign: 'left' },
            { text: 'IAR', datafield: 'IAR', width: '10%', columntype: 'dropdownlist', createeditor: ddlComms, align: 'center', cellsalign: 'center', initeditor: initeditor, geteditorvalue: getEditorValue },
            { text: 'OAR', datafield: 'OAR', width: '10%', columntype: 'dropdownlist', createeditor: ddlComms, align: 'center', cellsalign: 'center', initeditor: initeditor, geteditorvalue: getEditorValue },
            { text: 'EAR', datafield: 'EAR', width: '10%', columntype: 'dropdownlist', createeditor: ddlComms, align: 'center', cellsalign: 'center', initeditor: initeditor, geteditorvalue: getEditorValue },
            { text: '', datafield: 'Delete', width: '10%', cellsrenderer: cellsrendererbutton, editable: false },
        ];

        return columnsTech;
    }
}
