function onClickGoToChild(d) {
    var uri = '/atk_object?dn='+d['path'];
    window.location.assign(encodeURI(uri))
}
function show_object(data) {
    var attributes = data['attributes'];
    var properties = data['properties'];
    var children = data['children'];

    var attr_key = d3.keys(attributes).sort();

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
            .attr('value', function (d) {return encodeURI('/atk_object?dn=' + d['dn']);})
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
            .text(function (d) {return capitalize(d['class']) + ': ' + d['name'];})
            .attr('href', function (d) {
                return '/atk_object?dn=' + d['dn'];
            });

    }
    view = d3.select(".atk_object_view");

    view.selectAll('div').remove();

    view.append('hr');

    props = view.append('div')
        .attr('class', 'subspan11')
        .attr('id','obj_properties');

    //var prop_key = d3.keys(properties).sort();
    //props.selectAll('p')
    //    .data(prop_key).enter()
    //    .append('p')
    //    .text(function(d) {return capitalize(d)+': '+properties[d];});

    rel_parent = view.append('div')
        .attr('class', 'subspan12')

    rel_parent.append('p')
        .datum(properties)
        .text('Current: ')
        .append('a')
        .text(function(d) {return capitalize(properties['class'])+': '+properties['name'];})
        .attr('href',function(d) { return '/atk_object?dn='+properties['dn'];});

    if (data['parent']) {
        simpleLink('Parent: ', [data['parent']], rel_parent);
    }
    // rel_child = view.append('div')
    //    .attr('class', 'subspan12')

    var children_classes = d3.keys(children);
    if (children_classes.length > 0) {
        childLink = rel_parent.append('p')
            .text('Children: ');

        childDropDown1 = childLink.append('select')
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

        childDropDown2 = childLink.append('select')
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
        childDropDown = rel_parent.append('p')
            .text('Children: None');
    }

    // show relationships to other objects in the next column
    var relation_view = view.append('div')
                    .attr('class', 'subspan12');

    var relations = data['relations'];

    var rel_keys = d3.keys(relations).sort();

    for (var index in rel_keys) {
        var rel_key = rel_keys[index];
        var rel_data = relations[rel_key].sort(alphabetical);
        if (rel_data.length == 1) {
            simpleLink(capitalize(rel_key)+': ', rel_data,relation_view );
        } else {
            var relDropDown = relation_view.append('p')
                .text(capitalize(rel_key) + ': ')
                .append('select')
                .attr('class', 'atk-select')
                .attr('id', 'children_dropdown')
                .attr('onchange', "window.location.assign(this.value);");


            relDropDown.selectAll('option')
                .data(rel_data).enter()
                .append('option')
                .attr('value', function (d) {
                    return encodeURI('/atk_object?dn=' + d['dn']);
                })
                .text(function (d) {
                    return capitalize(d['class']) + ': ' + d['name'];
                });

            relDropDown.insert("option", ":first-child")
                .text('Select 1 of ' + rel_data.length);
        }
    }
    table = view.append('div')
        .attr("class", "attr-table")
        .attr('id','attr_table')
        .append('hr');

    table.append('div')
        .html('Attributes');

    table = table.append("table")
        .attr('border', '1');

    table_row = table.selectAll('tr')
        .data(attr_key).enter()
        .append("tr");

    table_row.append("td")
        .attr('style', 'text-align:right;font-weight: bold')
        .text(function (d) { return d; });

    table_row.append("td")
        .text(function (d) {return ' ' + attributes[d];});
}
