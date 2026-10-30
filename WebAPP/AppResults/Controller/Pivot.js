import { Message } from "../../Classes/Message.Class.js";
import { Base } from "../../Classes/Base.Class.js";
import { Html, escapeHtml } from "../../Classes/Html.Class.js";
import { Model } from "../Model/Pivot.Model.js";
import { Osemosys } from "../../Classes/Osemosys.Class.js";
import { DEF } from "../../Classes/Definition.Class.js";
import { MessageSelect } from "../../App/Controller/MessageSelect.js"
import { DataModelResult } from "../../Classes/DataModelResult.Class.js";
import { DefaultObj } from "../../Classes/DefaultObj.Class.js";
import { ResultAggregator } from "../../Classes/ResultAggregator.Class.js";
import { ResultGrid } from "../../Classes/ResultGrid.Class.js";
import { ResultLayoutState } from "../../Classes/ResultLayoutState.Class.js";
import { ResultPanel } from "../../Classes/ResultPanel.Class.js";
import { ResultFieldSettings } from "../../Classes/ResultFieldSettings.Class.js";

const ECHARTS_URL = 'References/echarts/echarts-6.1.0.min.js';

// Chart plots at most 100 series/categories, one per Columns/Rows value: Wijmo's PivotChart.MAX_SERIES and MAX_POINTS
const CHART_MAX_SERIES = 100;
const CHART_MAX_POINTS = 100;

// Longest unit label the value axis will carry; past this the axis says "Multiple units"
// and the full list moves below the chart, as MUIO does.
const UNIT_LABEL_MAX_CHARS = 40;
// Height of the unit footer strip drawn under the legend.
const UNIT_FOOTER_HEIGHT = 18;

// Legend chip metrics, used both to measure the legend and to draw it.
const LEGEND_FONT_SIZE = 9;
const LEGEND_ROW_HEIGHT = 17;
const LEGEND_ITEM_SIZE = 8;
const LEGEND_ITEM_GAP = 8;

export default class Pivot {
    static loadECharts() {
        if (window.echarts) return Promise.resolve(window.echarts);
        return new Promise((resolve, reject) => {
            let script = document.getElementById('ogc-echarts-runtime');
            if (script) {
                script.addEventListener('load', () => resolve(window.echarts), { once: true });
                script.addEventListener('error', () => reject('Charts could not be loaded.'), { once: true });
                return;
            }
            script = document.createElement('script');
            script.id = 'ogc-echarts-runtime';
            script.src = ECHARTS_URL;
            script.async = true;
            script.addEventListener('load', () => resolve(window.echarts), { once: true });
            script.addEventListener('error', () => {
                script.remove();
                reject('Charts could not be loaded.');
            }, { once: true });
            document.head.appendChild(script);
        });
    }

    // Strip markup from value, turning <sup> digits into Unicode superscripts.
    static plainText(value) {
        const superscript = { '0':'⁰', '1':'¹', '2':'²', '3':'³', '4':'⁴', '5':'⁵', '6':'⁶', '7':'⁷', '8':'⁸', '9':'⁹', '+':'⁺', '-':'⁻' };
        const entities = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: '\u00a0' };
        return (value == null ? '' : String(value)).replace(/<sup>(.*?)<\/sup>/gi, (_, text) =>
            [...text].map(character => superscript[character] || character).join(''))
            .replace(/<[^>]*>/g, '')
            .replace(/&(amp|lt|gt|quot|apos|nbsp);/gi, (_, name) => entities[name.toLowerCase()]);
    }

    // Field each result group puts in Columns by default; null means no column field. Others default to Tech.
    static GROUP_COLUMNS = Object.freeze({
        R: 'Optimal', RY: null, RYE: 'Emi', RYCn: 'Con', RYS: 'Stg',
        RYCTs: 'Comm', RYC: 'Comm', RYTC: 'Comm', RYTCM: 'Comm', RYTCMTs: 'Comm'
    });

    // List the fields in the pivot records, splitting camel case into the headers saved views refer to.
    static fieldCatalogue(items) {
        const sample = (items || [])[0] || {};
        return Object.keys(sample).map(name => ({
            field: name,
            header: name.replace(/([a-z])([A-Z])/g, '$1 $2'),
            isMeasure: name == 'Value',
            isNumeric: (items || []).some(item => typeof item[name] == 'number' && Number.isFinite(item[name]))
        }));
    }

    // Reset the layout to the fields the given result group opens with.
    static applyDefaultLayout(state, group) {
        const column = Object.prototype.hasOwnProperty.call(Pivot.GROUP_COLUMNS, group)
            ? Pivot.GROUP_COLUMNS[group] : 'Tech';
        return state.defer(current => {
            current.resetFieldSettings();
            ['rows', 'columns', 'filters', 'values'].forEach(area => current.getAreas()[area].splice(0));
            // Clear filters too, or one variable's filter would silently restrict the next.
            Object.keys(current.filters).forEach(name => current.setFilter(name, null));
            Object.keys(current.conditionFilters).forEach(name => current.setConditionFilter(name, null));
            Object.keys(current.descending).forEach(name => current.setDescending(name, false));
            current.assignField('Case', 'rows');
            if (group != 'R') current.assignField('Year', 'rows');
            if (column) current.assignField(column, 'columns');
            current.assignField('Value', 'values');
        });
    }

    // Fill a native select from a list of records, keeping the current value when it still exists.
    static fillSelect(selector, items, valueKey, labelKey, selected) {
        const control = document.querySelector(selector);
        if (!control) return;
        control.innerHTML = (items || []).map(item => {
            const option = document.createElement('option');
            option.value = item[valueKey];
            option.textContent = Pivot.plainText(item[labelKey]);
            return option.outerHTML;
        }).join('');
        // Set the value directly: outerHTML above serializes the selected attribute, not the property.
        if (selected != null) control.value = selected;
    }

    // Distinct units among the records the active filters keep, so the label follows what is plotted.
    static getFilteredUnits(items, configuration) {
        const filters = ResultAggregator.filterDefinitions((configuration || {}).filters || []);
        const units = new Set();
        (items || []).forEach(item => {
            const unit = item.Unit;
            if (!unit || units.has(unit)) return;
            if (ResultAggregator.matchesFilters(item, filters)) units.add(unit);
        });
        return units;
    }

    // Largest value the axis must label. Stacked charts show the column total, so a single
    // series maximum would badly understate it. Padded for the tick ECharts rounds up to.
    static getValueExtent(series, categories, stacking, percent) {
        if (percent) return 100;
        let extent = 0;
        if (stacking) {
            for (let index = 0; index < categories; index++) {
                let positive = 0, negative = 0;
                series.forEach(itemSeries => {
                    const value = itemSeries.values[index];
                    if (value == null) return;
                    if (value >= 0) positive += value; else negative += value;
                });
                extent = Math.max(extent, positive, Math.abs(negative));
            }
        } else {
            series.forEach(itemSeries => itemSeries.values.forEach(value => {
                if (value != null) extent = Math.max(extent, Math.abs(value));
            }));
        }
        return extent * 1.1;
    }

    // Rows the legend needs at the current width; the footer sits directly on top of them.
    static legendRows(series) {
        const host = document.getElementById('pivotChart');
        const width = host && host.clientWidth ? host.clientWidth : 1200;
        const longest = series.reduce((count, item) => Math.max(count, String(item.name || '').length), 8);
        const entryWidth = LEGEND_ITEM_SIZE + 6 + longest * LEGEND_FONT_SIZE * 0.6 + LEGEND_ITEM_GAP;
        const perRow = Math.max(1, Math.floor(width / entryWidth));
        return Math.max(1, Math.ceil(series.length / perRow));
    }

    // Join the units into one readable label, with superscripts as Unicode.
    static getUnitLabel(units) {
        return Array.from(units || []).filter(Boolean)
            .map(unit => Pivot.plainText(unit)).join(', ');
    }

    // Unit list drawn inside the chart so exports carry it, sitting above the legend on the left.
    static unitFooter(text, above = 0) {
        return text ? [{
            type: 'text', left: 8, bottom: above + 4, silent: true,
            style: { text: text, fontSize: 11, fill: '#4b5563' }
        }] : [];
    }

    // Turn the aggregated result into the categories, series and labels the chart options are built from.
    static getChartModel(app) {
        const result = app.aggregateResult;
        if (!result) return { categories: [], categoryLabels: [], series: [], rowFields: [], categoryTuples: [] };

        // Rows become categories and columns become series, both already in the aggregator's order.
        const rowKeys = result.rowKeys.slice(0, CHART_MAX_POINTS);
        const columnKeys = result.columnKeys.slice(0, CHART_MAX_SERIES);
        const categoryTuples = rowKeys.map(key => key.map(value => Pivot.plainText(value)));
        const rowIndexes = new Map(rowKeys.map((key, index) => [ResultAggregator.keyID(key), index]));
        const columnIndexes = new Map(columnKeys.map((key, index) => [ResultAggregator.keyID(key), index]));
        const valueField = result.valueFields.length ? result.valueFields[0].field : 'Value';
        const series = columnKeys.map(key => ({
            name: Pivot.plainText(key.join(' - ')) || valueField,
            values: Array(rowKeys.length).fill(null)
        }));

        // Fill each series from the cells; totals are excluded because the aggregator stores them separately.
        result.cells.forEach(cell => {
            const row = rowIndexes.get(ResultAggregator.keyID(cell.rowKey));
            const column = columnIndexes.get(ResultAggregator.keyID(cell.columnKey));
            if (row == null || column == null) return;
            const value = cell.values[valueField];
            series[column].values[row] = Number.isFinite(value) ? value : null;
        });

        const rowFieldNames = result.rowFields.slice();
        // Case is dropped from the visible label because the grouped axis already shows it as a bracket.
        const displayedFields = rowFieldNames.map((_, index) => index)
            .filter(index => rowFieldNames[index] != 'Case');
        if (!displayedFields.length && rowFieldNames.length) displayedFields.push(rowFieldNames.length - 1);
        // categories are the unique keys, categoryLabels the shorter text shown under each bar.
        const categories = categoryTuples.map(values => values.join(' - ') || 'Value');
        const categoryLabels = categoryTuples.map(values =>
            displayedFields.map(index => values[index]).join(' - ') || 'Value');

        return { categories, categoryLabels, series, rowFields: rowFieldNames, categoryTuples };
    }

    // Rendered width of one label, measured rather than estimated so the levels can be packed tightly.
    // Results repeat the same few labels down a column, so measurements are cached by text and size.
    static textWidth(text, fontSize) {
        const cache = Pivot.textWidths || (Pivot.textWidths = new Map());
        const key = `${fontSize}:${text}`;
        let width = cache.get(key);
        if (width === undefined) {
            const context = Pivot.measureContext
                || (Pivot.measureContext = document.createElement('canvas').getContext('2d'));
            context.font = `${fontSize}px sans-serif`;
            width = context.measureText(text).width;
            cache.set(key, width);
        }
        return width;
    }

    // Distance from the plot to each grouped level of a rotated chart, so long labels cannot collide.
    static getLevelOffsets(chartModel) {
        const tuples = chartModel.categoryTuples || [];
        const leafIndex = (chartModel.rowFields || []).length - 1;
        // Widest label at one level, in pixels, plus padding. The leaf axis draws larger than the brackets.
        const levelWidth = index => tuples.reduce((longest, tuple) => {
            const label = Pivot.plainText(tuple[index] == null ? '' : tuple[index]);
            return Math.max(longest, Pivot.textWidth(label, index == leafIndex ? 12 : 10));
        }, 0) + 14;
        const offsets = [];
        // Each level clears every level inside it, so offsets accumulate outwards from the leaf.
        let used = leafIndex >= 0 ? levelWidth(leafIndex) : 0;
        for (let field = leafIndex - 1; field >= 0; field--) {
            offsets[field] = used;
            used += levelWidth(field);
        }
        // total is the space all levels need, which the grid uses as its left margin.
        return { offsets, total: used };
    }

    // Build the category axis: one axis labelling each bar, plus a bracket axis per outer row field.
    static getCategoryAxis(chartModel, horizontal, levelOffsets) {
        const tuples = chartModel.categoryTuples || [];
        const fieldCount = (chartModel.rowFields || []).length;
        const leafIndex = fieldCount - 1;
        const host = document.getElementById('pivotChart');
        const chartWidth = Math.max(host && host.clientWidth ? host.clientWidth : 0, 640) - 120;
        const categoryWidth = chartModel.categories.length ? chartWidth / chartModel.categories.length : chartWidth;
        const longestLeaf = tuples.reduce((width, tuple) => {
            const label = leafIndex >= 0 ? Pivot.plainText(tuple[leafIndex]) : '';
            return Math.max(width, Pivot.textWidth(label, 12));
        }, 0);
        // Tilt the bar labels only when they are wider than the space each bar gets.
        const leafRotated = !horizontal && longestLeaf > Math.max(categoryWidth, 24);
        const leafAngle = leafRotated ? 45 : 0;
        const leafHeight = leafRotated
            ? Math.min(160, Math.ceil(longestLeaf * Math.sin(Math.PI / 4)) + 14)
            : 24;
        const leafAxis = {
            type: 'category',
            data: chartModel.categories,
            axisLabel: {
                hideOverlap: true,
                rotate: leafAngle,
                formatter: (_, index) => {
                    const tuple = tuples[index] || [];
                    const value = leafIndex >= 0 ? tuple[leafIndex] : null;
                    return Pivot.plainText(value != null && value !== '' ? value : chartModel.categoryLabels[index]);
                }
            }
        };
        if (fieldCount < 2 || tuples.length != chartModel.categories.length) return leafAxis;

        // Height of one bracket row, and how far each level sits from the plot when the chart is rotated.
        const step = 22;
        const axes = [leafAxis];
        for (let field = 0; field < leafIndex; field++) {
            // A bracket starts wherever this field or any field outside it changes value.
            const starts = [];
            tuples.forEach((tuple, index) => {
                if (index == 0) { starts.push(index); return; }
                const previous = tuples[index - 1] || [];
                for (let outer = 0; outer <= field; outer++) {
                    if (previous[outer] != tuple[outer]) { starts.push(index); return; }
                }
            });
            // Label each bracket once, at the category in the middle of its span.
            const midLabel = new Map();
            starts.forEach((start, groupIndex) => {
                const end = (groupIndex + 1 < starts.length ? starts[groupIndex + 1] : tuples.length) - 1;
                midLabel.set(Math.floor((start + end) / 2), Pivot.plainText((tuples[start] || [])[field]));
            });
            const boundaries = new Set(starts);
            const rank = leafIndex - field;
            axes.push({
                type: 'category',
                data: chartModel.categories,
                position: horizontal ? 'left' : 'bottom',
                offset: horizontal ? levelOffsets.offsets[field] : leafHeight + (rank - 1) * step,
                // Ticks divide the groups; the axis line is off because it would run through them all.
                axisLine: { show: false },
                axisTick: {
                    show: true,
                    alignWithLabel: false,
                    length: step,
                    interval: index => boundaries.has(index),
                    lineStyle: { color: '#c4cad4' }
                },
                axisLabel: {
                    interval: 0,
                    hideOverlap: true,
                    fontSize: 10,
                    color: '#333',
                    formatter: (_, index) => midLabel.get(index) || ''
                }
            });
        }
        return axes;
    }

    // Height to reserve for the legend: every row, capped at half the chart minus reserved.
    static getLegendHeight(series, reserved = 0) {
        const host = document.getElementById('pivotChart');
        const width = host && host.clientWidth ? host.clientWidth : 1200;
        const height = host && host.clientHeight ? host.clientHeight : 400;
        // Two rows spare: ECharts leaves padding under a bottom-anchored legend that is not part of the rows.
        return Math.min((Pivot.legendRows(series) + 2) * LEGEND_ROW_HEIGHT,
            Math.max(24, Math.floor(height / 2) - reserved));
    }

    // Rescale each series so every category totals 100, for the percentage-stacked chart.
    static getPercentSeries(series) {
        if (!series.length) return [];
        const totals = series[0].values.map((_, index) => series.reduce((sum, current) => {
            const value = current.values[index];
            return sum + (value == null ? 0 : Math.abs(value));
        }, 0));
        return series.map(itemSeries => ({
            name: itemSeries.name,
            values: itemSeries.values.map((value, index) => {
                if (value == null) return null;
                return totals[index] ? value / totals[index] * 100 : 0;
            })
        }));
    }

    static formatChartValue(value, format, percent = false, currency = 'USD') {
        if (value == null || value === '' || !Number.isFinite(Number(value))) return '';
        const match = /^(n|c|p)(\d*)(,*)$/i.exec(format || '');
        const decimals = match && match[2] !== '' ? Number(match[2]) : 2;
        const scaled = Number(value) / Math.pow(1000, match ? match[3].length : 0);
        const options = { minimumFractionDigits: decimals, maximumFractionDigits: decimals };
        if (!percent && match && match[1].toLowerCase() == 'c') {
            options.style = 'currency';
            options.currency = currency;
        } else if (!percent && match && match[1].toLowerCase() == 'p') options.style = 'percent';
        const formatted = scaled.toLocaleString(undefined, options);
        return percent ? `${formatted}%` : formatted;
    }

    static formatAxisTooltip(params, format, percent, currency) {
        const items = Array.isArray(params) ? params : [params];
        if (!items.length) return '';
        const lines = [escapeHtml(Pivot.plainText(items[0].axisValueLabel || items[0].name))];
        items.forEach(item => {
            const value = Array.isArray(item.value) ? item.value[item.value.length - 1] : item.value;
            lines.push(`${item.marker}${escapeHtml(Pivot.plainText(item.seriesName))}: ${Pivot.formatChartValue(value, format, percent, currency)}`);
        });
        return lines.join('<br>');
    }

    static updatePieSeriesControl(app, series) {
        const control = document.getElementById('cmbPieSeries');
        if (!control) return;
        control.hidden = app.pivotChart.chartType != 'pie' || series.length < 2;
        const fallback = series.find(item => item.values.some(value => value != null && value > 0)) || series[0];
        const selectedName = series.some(item => item.name == app.pivotChart.pieSeries) ?
            app.pivotChart.pieSeries : (fallback ? fallback.name : '');
        app.pivotChart.pieSeries = selectedName;
        control.innerHTML = series.map(item => {
            const option = document.createElement('option');
            option.value = item.name;
            option.textContent = item.name;
            return option.outerHTML;
        }).join('');
        // outerHTML serializes the selected attribute, not the property, so set the live value here.
        control.value = selectedName;
    }

    static getChartOption(app, model) {
        const chartModel = Pivot.getChartModel(app);
        const chartType = app.pivotChart.chartType;
        const percent = app.pivotChart.stacking == 'percent';
        const stacking = app.pivotChart.stacking != 'none';
        const valueField = app.aggregateResult && app.aggregateResult.valueFields[0];
        const valueFormat = valueField ? valueField.format : model.stgDecimalPoints;
        const currency = model.genData['osy-currency'] || 'USD';
        const chartSeries = percent ? Pivot.getPercentSeries(chartModel.series) : chartModel.series;
        Pivot.updatePieSeriesControl(app, chartSeries);
        const unitLabel = Pivot.getUnitLabel(Pivot.getFilteredUnits(model.pivotData, app.resultConfiguration));

        if (chartType == 'pie') {
            // A pie has no value axis, so its units go in the footer.
            const pieNote = unitLabel ? `Units: ${unitLabel}` : '';
            const pieLegendHeight = app.pivotChart.showLegend
                ? Pivot.legendRows(chartModel.categories.map(name => ({ name }))) * LEGEND_ROW_HEIGHT : 0;
            const selectedSeries = chartSeries.find(item => item.name == app.pivotChart.pieSeries) || chartSeries[0];
            const pieData = selectedSeries ? chartModel.categories
                .map((name, index) => ({ name, value: selectedSeries.values[index] }))
                .filter(item => item.value != null && item.value > 0) : [];
            return {
                color: model.ColorSchemes.osyScheme,
                aria: { enabled: true },
                tooltip: {
                    trigger: 'item',
                    confine: true,
                    formatter: item => `${item.marker}${escapeHtml(Pivot.plainText(item.name))}: ${Pivot.formatChartValue(item.value, valueFormat, percent, currency)}`
                },
                legend: {
                show: app.pivotChart.showLegend,
                // 'plain' lists every entry at once; 'scroll' would page them and hide most from the export.
                type: 'plain',
                bottom: 0,
                selectedMode: false,
                icon: 'rect',
                itemWidth: LEGEND_ITEM_SIZE,
                itemHeight: LEGEND_ITEM_SIZE,
                itemGap: LEGEND_ITEM_GAP,
                textStyle: { fontSize: LEGEND_FONT_SIZE }
            },
                graphic: Pivot.unitFooter(pieNote, pieLegendHeight).concat(pieData.length ? [] : [{
                    type: 'text',
                    left: 'center',
                    top: 'middle',
                    style: { text: 'No positive data is available for this series.', fill: '#666' }
                }]),
                series: selectedSeries ? [{
                    name: selectedSeries.name,
                    type: 'pie',
                    center: ['50%', '50%'],
                    radius: ['25%', '65%'],
                    avoidLabelOverlap: true,
                    label: { show: true, position: 'outside', distanceToLabelLine: 3 },
                    labelLine: { show: true, length: 12, length2: 8 },
                    emphasis: { scale: true, scaleSize: 15 },
                    stillShowZeroSum: false,
                    data: pieData
                }] : []
            };
        }

        const horizontal = chartType == 'bar';
        const itemTooltip = chartType == 'column' || chartType == 'bar';
        const type = itemTooltip ? 'bar' : chartType == 'area' ? 'line' : chartType;
        // Measured once here: both the bracket axes and the grid's left margin are derived from it.
        const levelOffsets = horizontal ? Pivot.getLevelOffsets(chartModel) : null;
        const categoryAxis = Pivot.getCategoryAxis(chartModel, horizontal, levelOffsets);
        const grouped = Array.isArray(categoryAxis);
        const levels = grouped ? categoryAxis.length - 1 : 0;
        // Space the bracket rows need below the plot; the legend gets what is left of its half.
        const axisHeight = !horizontal && grouped ? levels * 22 + 6 : 6;
        const legendHeight = app.pivotChart.showLegend ? Pivot.getLegendHeight(chartSeries, axisHeight) : 12;
        // Upright charts have little room beside the value axis, so a long list moves to the footer.
        // Rotated charts keep the full label, which reads along the width.
        const unitOverflow = !horizontal && unitLabel.length > UNIT_LABEL_MAX_CHARS;
        const unitNote = unitOverflow ? `Y-axis units: ${unitLabel}` : '';
        const noteHeight = unitNote ? UNIT_FOOTER_HEIGHT : 0;
        // The bracket rows are offset axes that containLabel does not measure, so reserve them here.
        const bottomHeight = legendHeight + axisHeight + noteHeight;
        // Clear the widest value label, which grows with the magnitude plotted: 250,000.00 needs far
        // more room than 25.00, and a fixed gap would sit the unit name on top of the numbers.
        const extent = Pivot.getValueExtent(chartSeries, chartModel.categories.length, stacking, percent);
        const valueLabelWidth = Pivot.textWidth(
            Pivot.formatChartValue(extent, valueFormat, percent, currency), 12);
        const axisValue = {
            type: 'value',
            name: unitOverflow ? 'Multiple units' : unitLabel,
            nameLocation: 'middle',
            nameRotate: horizontal ? 0 : 90,
            nameGap: horizontal ? 26 : Math.ceil(valueLabelWidth) + 14,
            nameTextStyle: { fontSize: 11, color: '#4b5563' },
            axisLabel: { formatter: value => Pivot.formatChartValue(value, valueFormat, percent, currency) }
        };

        return {
            color: model.ColorSchemes.osyScheme,
            aria: { enabled: true },
            tooltip: {
                trigger: itemTooltip ? 'item' : 'axis',
                confine: true,
                extraCssText: 'max-width: 320px; max-height: 70%; overflow-y: auto;',
                formatter: params => {
                    if (!itemTooltip) return Pivot.formatAxisTooltip(params, valueFormat, percent, currency);
                    const value = Array.isArray(params.value) ? params.value[params.value.length - 1] : params.value;
                    return `${params.marker}${escapeHtml(Pivot.plainText(params.seriesName))}<br>` +
                        `${escapeHtml(Pivot.plainText(params.name))}: ${Pivot.formatChartValue(value, valueFormat, percent, currency)}`;
                }
            },
            legend: {
                show: app.pivotChart.showLegend,
                // 'plain' lists every entry at once; 'scroll' would page them and hide most from the export.
                type: 'plain',
                bottom: 0,
                selectedMode: false,
                icon: 'rect',
                itemWidth: LEGEND_ITEM_SIZE,
                itemHeight: LEGEND_ITEM_SIZE,
                itemGap: LEGEND_ITEM_GAP,
                textStyle: { fontSize: LEGEND_FONT_SIZE }
            },
            grid: {
                top: 35,
                right: 30,
                // containLabel already fits the axis labels, so only legend and brackets are added here.
                bottom: bottomHeight,
                // Stacked bracket levels are measured here, so containLabel would reserve that width twice.
                left: horizontal && grouped ? Math.max(75, levelOffsets.total) : 75,
                containLabel: !(horizontal && grouped)
            },
            graphic: Pivot.unitFooter(unitNote,
                app.pivotChart.showLegend ? Pivot.legendRows(chartSeries) * LEGEND_ROW_HEIGHT : 0),
            xAxis: horizontal ? axisValue : categoryAxis,
            yAxis: horizontal ? categoryAxis : axisValue,
            series: chartSeries.map(itemSeries => ({
                name: itemSeries.name,
                type,
                data: itemSeries.values,
                stack: app.pivotChart.stacking == 'none' ? undefined : 'results',
                areaStyle: chartType == 'area' ? {} : undefined,
                connectNulls: false,
                emphasis: { focus: 'series' }
            }))
        };
    }

    static renderChart(app, model) {
        if (Pivot.activeApp != app || !window.echarts) return;
        const host = document.getElementById('pivotChart');
        if (!host) return;
        const option = Pivot.getChartOption(app, model);

        if (!option.series.length) {
            Pivot.disposeChart();
            host.textContent = 'No chart data is available for this view.';
            host.classList.add('pivot-chart-empty');
            return;
        }

        host.classList.remove('pivot-chart-empty');
        if (!Pivot.chart || Pivot.chart.isDisposed()) {
            host.textContent = '';
            Pivot.chart = window.echarts.init(host, null, { renderer: 'svg' });
        }
        Pivot.chart.setOption(option, true);
        Pivot.chart.resize();
    }

    static disposeChart() {
        if (Pivot.chart && !Pivot.chart.isDisposed()) Pivot.chart.dispose();
        Pivot.chart = null;
    }

    // Re-aggregate the model data for the active layout and refresh the grid.
    static renderResultGrid(app, model) {
        const configuration = app.state.configuration();
        app.resultConfiguration = configuration;
        app.aggregateResult = ResultAggregator.aggregate(model.pivotData, configuration);
        app.resultGrid.render(app.aggregateResult, app.state.numberFormat);
    }

    // Unique values of one field, used to populate the filter list in the field settings dialog.
    static fieldValues(items, field) {
        const values = new Map();
        (items || []).forEach(item => {
            const value = ResultAggregator.keyValue(item[field]);
            values.set(ResultAggregator.keyID([value]), value);
        });
        return Array.from(values.values());
    }

    // Redraw grid and chart together, skipping the call while a variable change is still in flight.
    static renderResults(app, model) {
        if (Pivot.activeApp != app || app.updatingParam) return;
        Pivot.renderResultGrid(app, model);
        Pivot.renderChart(app, model);
    }

    // Tear down the grid and its listeners when leaving the page or rebuilding it.
    static disposeResultGrid(app = Pivot.activeApp) {
        if (app && app.resultGrid) app.resultGrid.destroy();
    }

    // Tear down the field panel and the settings dialog it opens.
    static disposeResultPanel(app = Pivot.activeApp) {
        if (app && app.panel) app.panel.destroy();
        ResultFieldSettings.destroy();
    }

    // Warn the user about settings a saved view asked for that this layout cannot reproduce.
    static reportLayoutWarnings(state) {
        if (state.warnings.length) {
            Message.smallBoxWarning('Saved view', state.warnings.map(warning => escapeHtml(warning)).join('<br>'), 6000);
        }
    }

    // Remember what this model was left on. Held in memory, so navigating keeps it but a reload starts clean.
    static saveSnapshot(model) {
        Pivot.lastSnapshot = { casename: model.casename, group: model.group, param: model.param, view: model.VIEW };
    }

    // The remembered start point for this model, used to open the right variable instead of the default.
    static startPoint(casename) {
        const last = Pivot.lastSnapshot;
        return last && last.casename == casename ? last : null;
    }

    // The variable is already open by now, so only a saved view is left to reapply.
    static restoreSnapshot(model) {
        const last = Pivot.startPoint(model.casename);
        if (!last) return;
        // 'null' is the Default view entry, and a view can since have been deleted; neither needs reapplying.
        const hasView = last.view && last.view != 'null' &&
            (model.VIEWS || []).some(item => item['osy-viewId'] == last.view);
        if (hasView) $('#cmbViews').val(last.view).trigger('change');
    }

    // Show or hide the results table below the chart.
    static setTableHidden(app, hidden) {
        const grid = document.querySelector('#pivotGrid');
        if (!grid) return;
        app.pivotChart.hideTable = hidden === true;
        grid.style.display = app.pivotChart.hideTable ? 'none' : '';
        // Tabulator measures nothing while the table is display:none, so it needs a redraw once shown again.
        if (!app.pivotChart.hideTable && app.resultGrid && app.resultGrid.table && app.resultGrid.tableReady) {
            app.resultGrid.table.redraw(true);
        }
    }

    // Tick or clear the totals checkboxes to match the layout currently in effect.
    static syncTotalsControls(state) {
        const rowTotals = document.querySelector('#showRowTotals');
        const columnTotals = document.querySelector('#showColumnTotals');
        if (rowTotals) rowTotals.checked = state.totals.rows != ResultAggregator.ShowTotals.None;
        if (columnTotals) columnTotals.checked = state.totals.columns != ResultAggregator.ShowTotals.None;
    }

    // Resize the chart with the window and dispose it when the page unloads.
    static bindChartLifecycle(app, model) {
        $(window).off('.muiopivot');
        $(window).on('resize.muiopivot', () => {
            if (Pivot.chart && !Pivot.chart.isDisposed()) Pivot.chart.resize();
        });
        $(window).on('hashchange.muiopivot', () => {
            if (window.location.hash == '#/Pivot') return;
            Pivot.saveSnapshot(model);
            Pivot.disposeChart();
            Pivot.disposeResultGrid(app);
            Pivot.disposeResultPanel(app);
            if (Pivot.activeApp == app) Pivot.activeApp = null;
            $(window).off('.muiopivot');
        });
    }

    // Download the chart as SVG, named after the case and variable.
    static exportChart(model) {
        if (!Pivot.chart || Pivot.chart.isDisposed()) return;
        const safeName = `${model.casename}-${model.param}`.replace(/[^a-z0-9_-]+/gi, '-').toLowerCase();
        const link = document.createElement('a');
        link.download = `muiogo-${safeName}.svg`;
        link.href = Pivot.chart.getDataURL({ type: 'svg', pixelRatio: 2, backgroundColor: '#ffffff' });
        link.click();
    }

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
                    const INDICATORS = Osemosys.getParamFile('Indicators.json');
                    promise.push(INDICATORS);
                    const DUALS = Osemosys.getParamFile('Duals.json');
                    promise.push(DUALS);
                    const VIEWS = Osemosys.getResultData(casename,'viewDefinitions.json');
                    promise.push(VIEWS);
                    // Load the remembered variable's group straight away, so nothing is rendered and thrown away.
                    const start = Pivot.startPoint(casename);
                    const DATA = Osemosys.getResultData(casename, (start ? start.group : 'RYT') + '.json');
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
                let [casename, genData, resData, VARIABLES, INDICATORS, DUALS, VIEWS, DATA] = data;
                let model = new Model(casename, genData, resData, VARIABLES, INDICATORS, DUALS, DATA, VIEWS,
                    Pivot.startPoint(casename));
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
        const start = Pivot.startPoint(casename);
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
                const INDICATORS = Osemosys.getParamFile('Indicators.json');
                promise.push(INDICATORS);
                const DUALS = Osemosys.getParamFile('Duals.json');
                promise.push(DUALS);
                const VIEWS = Osemosys.getResultData(casename, 'viewDefinitions.json');
                promise.push(VIEWS);
                const DATA = Osemosys.getResultData(casename, (start ? start.group : 'RYT') + '.json');
                promise.push(DATA);
                return Promise.all(promise);
            })
            .then(data => {
                let [casename, genData, resData, VARIABLES, INDICATORS, DUALS, VIEWS, DATA] = data;
                let model = new Model(casename, genData, resData, VARIABLES, INDICATORS, DUALS, DATA, VIEWS,
                    start);
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

        if (model.refreshPage) {
            Pivot.disposeResultPanel();
            Pivot.disposeResultGrid();
        }
        Pivot.disposeChart();

        let app = {};
        app.state = new ResultLayoutState(Pivot.fieldCatalogue(model.pivotData), model.stgDecimalPoints);
        Pivot.applyDefaultLayout(app.state, model.group);
        model.DEFAULTVIEW = app.state.definition();

        app.panel = new ResultPanel('#pivotPanel', app.state, {
            plainText: value => Pivot.plainText(value),
            currency: model.genData['osy-currency'] || 'USD',
            fieldValues: field => Pivot.fieldValues(model.pivotData, field),
            onApply: () => {
                Pivot.syncTotalsControls(app.state);
                Pivot.renderResults(app, model);
            }
        });
        Pivot.syncTotalsControls(app.state);

        app.resultGrid = new ResultGrid('#pivotGrid', {
            plainText: value => Pivot.plainText(value),
            currency: model.genData['osy-currency'] || 'USD',
            getDetail: context => ResultAggregator.getDetail(
                model.pivotData,
                app.resultConfiguration,
                context.rowKey,
                context.columnKey
            ),
            removeField: fieldName => app.state.assignField(fieldName, null),
            editField: fieldName => ResultFieldSettings.open(fieldName, app.state, {
                plainText: value => Pivot.plainText(value),
                currency: model.genData['osy-currency'] || 'USD',
                fieldValues: field => Pivot.fieldValues(model.pivotData, field)
            }),
            // Only Year offers a sort toggle; reversing any other dimension is not meaningful here.
            sortableFields: ['Year'],
            toggleFieldSort: fieldName => app.state.setDescending(fieldName, !app.state.descending[fieldName])
        });
        app.pivotChart = { header: '', chartType: 'column', stacking: 'normal', showLegend: true, pieSeries: '', hideTable: false };
        Pivot.activeApp = app;
        // Rebuilding the page keeps the old element, so clear any hiding left over from the previous app.
        Pivot.setTableHidden(app, false);
        Pivot.renderResults(app, model);
        Pivot.bindChartLifecycle(app, model);

        Pivot.fillSelect('#cmbParams', model.VARIABLEOBJECT, 'value', 'name', model.param);
        $('#cmbParams').off('change').on('change', function () {
            if (this.value != null && model.TriggerUpdate) Pivot.updateParam(this.value, app, model);
        });

        $('#cmbChartType').html(model.ChartTypes.map(type =>
            `<option value="${type.value}">${type.name}</option>`).join(''));
        $('#cmbChartType').off('change').on('change', function () {
            app.pivotChart.chartType = this.value;
            Pivot.renderChart(app, model);
        });
        $('#cmbStackedChart').off('change').on('change', function () {
            app.pivotChart.stacking = this.value;
            Pivot.renderChart(app, model);
        });
        $('#cmbPieSeries').off('change').on('change', function () {
            app.pivotChart.pieSeries = this.value;
            Pivot.renderChart(app, model);
        });

        Pivot.fillSelect('#cmbViews', model.VIEWS, 'osy-viewId', 'osy-viewname', 'null');
        $('#cmbViews').off('change').on('change', function () {
            if (model.TriggerUpdate) Pivot.updateView(this.value, app, model);
        });

        Pivot.loadECharts()
            .then(() => {
                if (Pivot.activeApp != app) return;
                Pivot.renderChart(app, model);
            })
            .catch(error => Message.dangerOsy(error));

        this.initEvents(model, app);
        Pivot.restoreSnapshot(model);
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

            let POSTDATA = {
                "osy-viewId": viewId,
                "osy-viewname": viewname,
                "osy-viewdesc": desc,
                "osy-viewdef": app.state.definition()
            }

            Osemosys.saveView(model.casename, POSTDATA, param)
            .then(response => {
                Message.clearMessages();
                Message.bigBoxSuccess('Model message', response.message, 3000);
                POSTDATA['osy-varId'] = param;
                model.VIEWS.push(POSTDATA);
                // Html.ddlViews(model.VIEWS[model.param]);
                //Html.ddlViews(model.VIEWS);
                Pivot.fillSelect('#cmbViews', model.VIEWS, 'osy-viewId', 'osy-viewname', document.querySelector('#cmbViews').value);
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
                Pivot.fillSelect('#cmbViews', model.VIEWS, 'osy-viewId', 'osy-viewname', 'null');
                Osemosys.updateViews(model.casename, viewUpdate, model.param)
                .then(response => {
                    app.state.apply(model.DEFAULTVIEW);
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

        $("#csvExport").off('click');
        $('#csvExport').on('click', function () {
            app.resultGrid.downloadCSV('PivotGrid.csv');
        });
        
        $("#svgExport").off('click');
        $('#svgExport').on('click', function () {
            Pivot.exportChart(model);
        });

        $("#showRowTotals").off('click');
        $("#showRowTotals").click(function (e) {
            app.state.setTotals('rows', e.target.checked ?
                ResultAggregator.ShowTotals.Subtotals : ResultAggregator.ShowTotals.None);
        });
        
        $("#showColumnTotals").off('click');
        $("#showColumnTotals").click(function (e) {
            app.state.setTotals('columns', e.target.checked ?
                ResultAggregator.ShowTotals.Subtotals : ResultAggregator.ShowTotals.None);
        });

        $("#hideLegend").off('click');
        $("#hideLegend").click(function (e) {
            app.pivotChart.showLegend = !e.target.checked;
            Pivot.renderChart(app, model);
        });

        $("#hideTable").off('click');
        $("#hideTable").click(function (e) {
            Pivot.setTableHidden(app, e.target.checked);
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
        app.updatingParam = true;
        model.group = model.VARGROUPS[param]['group'];
        model.param = param;
        Osemosys.getResultData(model.casename, model.group+'.json')
        .then(DATA => {
            //console.log('DATA ', DATA, model.group)
            if (DATA !== null && model.param in DATA && Object.getOwnPropertyNames(DATA[model.param]).length != 0){
                let pivotData = DataModelResult.getPivot(DATA, model.genData, model.VARIABLES, model.group, model.param);
                model.pivotData = pivotData;
                // Load the new variable's fields, then open it on its group's default layout.
                app.state.setFields(Pivot.fieldCatalogue(model.pivotData));
                Pivot.applyDefaultLayout(app.state, model.group);
                app.state.setNumberFormat(model.stgDecimalPoints);
                model.DEFAULTVIEW = app.state.definition();
                app.pivotChart.header = '';

                if (view != null) {
                    Html.title(model.casename, model.VARNAMES[model.group][model.param], model.group+' - '+view['osy-viewname'] +' view');
                    app.state.apply(view['osy-viewdef']);
                    app.pivotChart.header = view['osy-viewname'];
                }
                else {
                    model.TriggerUpdate = false;
                    document.querySelector('#cmbViews').value = 'null';
                    model.VIEW = 'null';
                    model.TriggerUpdate = true;
                    Html.title(model.casename, model.VARNAMES[model.group][model.param], model.group+' - Default view');
                }
                // Drop filter values the new variable does not have, so nothing filters on a stale value.
                app.state.pruneFilterValues(model.pivotData);
                Pivot.reportLayoutWarnings(app.state);

                app.updatingParam = false;
                Pivot.renderResults(app, model);
                Message.loaderEnd();
            }
            else{
                app.updatingParam = false;
                Message.dangerOsy("Results do not contain values for variable <b>"+model.VARNAMES[model.group][model.param] + "</b> please check input data and rerun the model.")
                Message.loaderEnd();
            }

        })
        .catch(error => {
            app.updatingParam = false;
            Message.loaderEnd();
            Message.danger(error.message);
        }); 
    }

    static updateView(viewId, app, model){
        model.VIEW = viewId;
        if(model.VIEW == 'null'){
            app.state.apply(model.DEFAULTVIEW);
            app.state.pruneFilterValues(model.pivotData);
            app.pivotChart.header = '';
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
                            document.querySelector('#cmbParams').value = param;
                            model.TriggerUpdate = true;
                            Pivot.updateParam(param, app, model, obj);
                        }
                        else{
                            //console.log('OVDJE RADI HTML!!!')
                            app.state.apply(obj['osy-viewdef']);
                            app.state.pruneFilterValues(model.pivotData);
                            Pivot.reportLayoutWarnings(app.state);
                            app.pivotChart.header = obj['osy-viewname'];
                            Html.title(model.casename, model.VARNAMES[model.group][model.param], model.group+' - '+obj['osy-viewname'] +' view');
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
