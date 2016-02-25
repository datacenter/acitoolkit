/*
################################################################################
################################################################################
#                                                                              #
# Copyright (c) 2015 Cisco Systems                                             #
# All Rights Reserved.                                                         #
#                                                                              #
#    Licensed under the Apache License, Version 2.0 (the "License"); you may   #
#    not use this file except in compliance with the License. You may obtain   #
#    a copy of the License at                                                  #
#                                                                              #
#         http://www.apache.org/licenses/LICENSE-2.0                           #
#                                                                              #
#    Unless required by applicable law or agreed to in writing, software       #
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT #
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the  #
#    License for the specific language governing permissions and limitations   #
#    under the License.                                                        #
#                                                                              #
################################################################################
*/
function onClickGoToChild(d) {
    var uri = '/acitoolkitsearchview?dn='+d['uid'];
    window.location.assign(encodeURI(uri))
}
function show_object(data) {

    function buildChildInstanceSelect() {
        var d = childDropDown1.node().value;
        var selectWidget = d3.select("#children_instance");

        if (d=='None') {
            selectWidget
                .attr('onclick', null)
                .attr('onchange',null)
                .selectAll('option').remove();

            selectWidget.append("option")
                .text('select class first');

            return;
        }
        var childInstances = children[d].sort(alphabetical);
        selectWidget.selectAll('option').remove();

        selectWidget.selectAll('option')
            .data(childInstances).enter()
            .append('option')
            .attr('value', function (d) {return encodeURI('/acitoolkitsearchview?dn=' + d['dn']);})
            .text(function (d, i) {return (parseInt(i)+1)+'. '+d['name'];});

        if (childInstances.length > 1) {
            selectWidget.insert("option", ":first-child")
                .text('Select 1 of ' + childInstances.length);
            selectWidget.attr('onchange', "window.location.assign(this.value);");
        } else {
            selectWidget.attr('onclick', "window.location.assign(this.value);");
        }
    }

    function capitalize(d) {
        return d.charAt(0).toUpperCase() + d.slice(1);
    }

    function alphabetical(a, b) {
        // case insensitive sort on the name field
         var A = a['name'].toLowerCase();
         var B = b['name'].toLowerCase();
         if (A < B){
            return -1;
         }else if (A > B){
           return  1;
         }else{
           return 0;
         }
    }

    function simpleLink(label, linkdata, location) {
        location.append('p')
            .data(linkdata)
            .text(label)
            .append('a')
            .text(function (d) {return d['class'] + ': ' + d['name'];})
            .attr('href', function (d) {
                return '/acitoolkitsearchview?dn=' + d['dn'];
            });

    }

    var properties = data['properties'];
    var children = data['children'];

    var view = d3.select(".atk_object_view");
    view.selectAll('div').remove();
    view.append('hr');

    var props = view.append('div')
        .attr('class', 'subspan11')
        .attr('id','obj_properties')
        .append('h2')
        .attr('align', 'center')
        .text(function(d) {return properties['class']+': '+properties['name'];});

    // Indicate what object this is
    var rel_parent = view.append('div')
        .attr('class', 'subspan12')

    // show parent object with link
    if (data['parent']) {
        simpleLink('Parent: ', [data['parent']], rel_parent);
    }

    // show children with links
    var children_classes = d3.keys(children);
    if (children_classes.length > 0) {
        var childLink = rel_parent.append('p')
            .text('Children: ');

        var childDropDown1 = childLink.append('select')
            .attr('class', 'atk-select')
            .attr('id', 'children_dropdown');

        childDropDown1.selectAll('option')
            .data(children_classes).enter()
            .append('option')
            .attr('value', function (d) {
                return d;
            })
            .text(function (d) {
                return d
            });

        var childDropDown2 = childLink.append('select')
            .attr('class','atk-select')
            .attr('id', 'children_instance');

        if (children_classes.length > 1) {
            childDropDown1.insert("option", ":first-child")
                .attr('value', 'None')
                .text('class');

            childDropDown1.on('change', buildChildInstanceSelect);

            childDropDown2.append("option")
                .text('select class first');

        } else {
            childDropDown1.node().value = children_classes[0];
            buildChildInstanceSelect();
        }


    } else {
        var childDropDown = rel_parent.append('p')
            .text('Children: None');
    }

    // show relationships to other objects in the next column
    var relation_view = view.append('div')
                    .attr('class', 'subspan12');

    var relations = data['relations'];

    var rel_keys = d3.keys(relations).sort();

    for (var index=0, tot=rel_keys.length; index< tot; index++) {
        var rel_key = rel_keys[index];
        var rel_data = relations[rel_key].sort(alphabetical);
        if (rel_data.length == 1) {
            simpleLink(rel_key+': ', rel_data,relation_view );
        } else {
            var relDropDown = relation_view.append('p')
                .text(rel_key + ': ')
                .append('select')
                .attr('class', 'atk-select')
                .attr('id', 'children_dropdown')
                .attr('onchange', "window.location.assign(this.value);");


            relDropDown.selectAll('option')
                .data(rel_data).enter()
                .append('option')
                .attr('value', function (d) {
                    return encodeURI('/acitoolkitsearchview?dn=' + d['dn']);
                })
                .text(function (d) {
                    return d['class'] + ': ' + d['name'];
                });

            relDropDown.insert("option", ":first-child")
                .text('Select 1 of ' + rel_data.length);
        }
    }

    // show all the attributes
    var attributes = data['attributes'];
    var attr_key = d3.keys(attributes).sort();
    var table = view.append('div')
        .attr("class", "attr-table")
        .attr('id','attr_table')
        .append('hr');

    table.append('div')
        .attr('align', 'center')
        .append('h4')
        .text('Attributes');

    table = table.append("table")
        .attr('border', '1')
        .attr('align','center');

    var table_row = table.selectAll('tr')
        .data(attr_key).enter()
        .append("tr");

    table_row.append("td")
        .attr('style', 'text-align:right;font-weight: bold')
        .text(function (d) { return d; });

    table_row.append("td")
        .text(function (d) {if (typeof attributes[d] == 'string')
                                {return ' ' + attributes[d];}
                            else {return ' '+attributes[d].join(", ")}});
}
