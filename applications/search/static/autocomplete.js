/**
 Copyright (c) 2014 BrightPoint Consulting, Inc.

 Permission is hereby granted, free of charge, to any person
 obtaining a copy of this software and associated documentation
 files (the "Software"), to deal in the Software without
 restriction, including without limitation the rights to use, 
 copy, modify, merge, publish, distribute, sublicense, and/or sell
 copies of the Software, and to permit persons to whom the
 Software is furnished to do so, subject to the following
 conditions:

 The above copyright notice and this permission notice shall be
 included in all copies or substantial portions of the Software.

 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, 
 EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
 OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
 HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, 
 WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 OTHER DEALINGS IN THE SOFTWARE.
 */
Array.prototype.extend = function (other_array) {
    /* you should include a test to check whether other_array really is an array */
    other_array.forEach(function(v) {this.push(v)}, this);
};

function SearchSplit(searchString) {
    // This will split the searchString at space boundaries
    // while respecting quotes
    words = [];
    var notInsideQuote = true;
    var start =0, end=0;
    searchString = searchString.replace(/^ /g,"");  //remove leading spaces
    for(var i=0; i<searchString.length-1; i++)
    {
        if(searchString.charAt(i)==" " && notInsideQuote)
        {
            words.push(searchString.substring(start,i).trim().replace(/^\"|\"$/g, ""));
            start = i+1;
        }
        else if(searchString.charAt(i)=='"')
            notInsideQuote=!notInsideQuote;
    }
    //todo: should preserve space at end if in the middle of a quote
    word = searchString.substring(start, searchString.length).replace(/^\"|\"$/g, "")
    if (notInsideQuote) {
        words.push(word.trim());
    } else {
        words.push(word);
    }
    //words.push(searchString.substring(start, searchString.length).replace(/^\"|\"$/g, ""));
    return words;

}

function AutoCompleteTerms(class_attr_values) {
    var class_attr_values = class_attr_values;

    this.SubTerm = function SubTerm(term_state, term_string) {
        this.state = term_state;
        this.string = term_string;
    };


    this.buildSearchTerm = function buildSearchTerm(escapeChar, str) {
        var re = new RegExp(escapeChar + '([^@=#*]+)[@=#\*]');
        var re_end = new RegExp(escapeChar + '([^@=#*]*)$');
        var term = new this.SubTerm('empty', '');
        if (re.test(str)) {
            term.state = 'complete';
            term.string = str.match(re)[1].replace(/"/g,'');
        } else if (re_end.test(str)) {
            term.state = 'incomplete';
            term.string = str.match(re_end)[1].replace(/"/g,'');
        }
        return term;
    };

    this.buildLastSearchTerm = function buildLastSearchTerm(str) {
        var re_end = new RegExp('([^@=#*]*)$');
        var term = new this.SubTerm('empty', '');
        if (re_end.test(str)) {
            term.state = 'incomplete';
            term.string = str.match(re_end)[1].replace(/"/g,'');
        }
        return term;
    };

    this.buildSearch = function buildSearch(str) {

        // a string with no escape character at the start implies * at start
        var re = new RegExp('^[#@=\*]');
        var class_term, value_term, attr_term, star_term, last_term;
        var searchStr;
        if (!re.test(str)) {
            str = '*' + str;
        }
        // begins with escape character
        class_term = this.buildSearchTerm('#', str);
        attr_term = this.buildSearchTerm('@', str);
        value_term = this.buildSearchTerm('=', str);
        star_term = this.buildSearchTerm('\\\*', str);
        last_term = this.buildLastSearchTerm(str);

        var complete = [];
        var terms = [];
        var term;
        //todo: need to complete this section
        if ((class_term.state == 'complete') && (attr_term.state == 'complete') && (value_term.state == 'complete')) {
            term = new this.Term(3, '', '');
            terms.push(term);
        } else if ((class_term.state == 'complete') && (attr_term.state == 'complete')) {
            term = new this.Term(2, last_term.string, 'value');
            term.string1 = class_term.string;
            term.type1 = 'class';
            term.string2 = attr_term.string;
            term.type2 = 'attr';
            terms.push(term);
        } else if ((class_term.state == 'complete') && (value_term.state == 'complete')) {
            term = new this.Term(2, last_term.string, 'attr');
            term.string1 = class_term.string;
            term.type1 = 'class';
            term.string2 = value_term.string;
            term.type2 = 'value';
            terms.push(term);
        } else if ((attr_term.state == 'complete') && (value_term.state == 'complete')) {
            term = new this.Term(2, last_term.string, 'class');
            term.string1 = attr_term.string;
            term.type1 = 'attr';
            term.string2 = value_term.string;
            term.type2 = 'value';
            terms.push(term);
        } else if ((class_term.state == 'complete') && (star_term.state == 'complete')) {

            if (value_term.state == 'incomplete') {
                term = new this.Term(2, last_term.string, 'value');
                term.string1 = class_term.string;
                term.type1 = 'class';
                term.string2 = star_term.string;
                term.type2 = 'attr';
                terms.push(term);
            } else if (attr_term.state == 'incomplete') {
                term = new this.Term(2, last_term.string, 'attr');
                term.string1 = class_term.string;
                term.type1 = 'class';
                term.string2 = star_term.string;
                term.type2 = 'value';
                terms.push(term);
            } else {
                term = new this.Term(2, last_term.string, 'value');
                term.string1 = class_term.string;
                term.type1 = 'class';
                term.string2 = star_term.string;
                term.type2 = 'attr';
                terms.push(term);

                term = new this.Term(2, last_term.string, 'attr');
                term.string1 = class_term.string;
                term.type1 = 'class';
                term.string2 = star_term.string;
                term.type2 = 'value';
                terms.push(term);
            }
        } else if ((attr_term.state == 'complete') && (star_term.state == 'complete')) {
            term = new this.Term(2, last_term.string, 'value');
            term.string1 = star_term.string;
            term.type1 = 'class';
            term.string2 = attr_term.string;
            term.type2 = 'attr';
            terms.push(term);

            term = new this.Term(2, last_term.string, 'class');
            term.string1 = attr_term.string;
            term.type1 = 'attr';
            term.string2 = star_term.string;
            term.type2 = 'value';
            terms.push(term);
        } else if ((value_term.state == 'complete') && (star_term.state == 'complete')) {
            term = new this.Term(2, last_term.string, 'attr');
            term.string1 = star_term.string;
            term.type1 = 'class';
            term.string2 = value_term.string;
            term.type2 = 'value';
            terms.push(term);

            term = new this.Term(2, last_term.string, 'class');
            term.string1 = star_term.string;
            term.type1 = 'attr';
            term.string2 = value_term.string;
            term.type2 = 'value';
            terms.push(term);
        } else if (class_term.state == 'complete') {
            if (attr_term.state == 'incomplete') {
                term = new this.Term(1, last_term.string, 'attr');
                term.string1 = class_term.string;
                term.type1 = 'class';
                term.string2 = class_term.string;
                term.type2 = 'class';
                terms.push(term);
            } else if (value_term.state == 'incomplete') {
                term = new this.Term(1, last_term.string, 'value');
                term.string1 = class_term.string;
                term.type1 = 'class';
                term.string2 = class_term.string;
                term.type2 = 'class';
                terms.push(term);
            } else if (star_term.state == 'incomplete') {
                term = new this.Term(1, last_term.string, 'attr');
                term.string1 = class_term.string;
                term.type1 = 'class';
                term.string2 = class_term.string;
                term.type2 = 'class';
                terms.push(term);

                term = new this.Term(1, last_term.string, 'value');
                term.string1 = class_term.string;
                term.type1 = 'class';
                term.string2 = class_term.string;
                term.type2 = 'class';
                terms.push(term);
            }
        } else if (attr_term.state == 'complete') {
            if (class_term.state == 'incomplete') {
                term = new this.Term(1, last_term.string, 'class');
                term.string1 = attr_term.string;
                term.type1 = 'attr';
                term.string2 = attr_term.string;
                term.type2 = 'attr';
                terms.push(term);
            } else if (value_term.state == 'incomplete') {
                term = new this.Term(1, last_term.string, 'value');
                term.string1 = attr_term.string;
                term.type1 = 'attr';
                term.string2 = attr_term.string;
                term.type2 = 'attr';
                terms.push(term);
            } else if (star_term.state == 'incomplete') {
                term = new this.Term(1, last_term.string, 'class');
                term.string1 = attr_term.string;
                term.type1 = 'attr';
                term.string2 = attr_term.string;
                term.type2 = 'attr';
                terms.push(term);
                term = new this.Term(1, last_term.string, 'value');
                term.string1 = attr_term.string;
                term.type1 = 'attr';
                term.string2 = attr_term.string;
                term.type2 = 'attr';
                terms.push(term);
            }
        } else if (value_term.state == 'complete') {
            if (class_term.state == 'incomplete') {
                term = new this.Term(1, last_term.string, 'class');
                term.string1 = value_term.string;
                term.type1 = 'value';
                term.string2 = value_term.string;
                term.type2 = 'value';
                terms.push(term);
            } else if (attr_term.state == 'incomplete') {
                term = new this.Term(1, last_term.string, 'attr');
                term.string1 = value_term.string;
                term.type1 = 'value';
                term.string2 = value_term.string;
                term.type2 = 'value';
                terms.push(term);
            } else if (star_term.state == 'incomplete') {
                term = new this.Term(1, last_term.string, 'class');
                term.string1 = value_term.string;
                term.type1 = 'value';
                term.string2 = value_term.string;
                term.type2 = 'value';
                terms.push(term);

                term = new this.Term(1, last_term.string, 'attr');
                term.string1 = value_term.string;
                term.type1 = 'value';
                term.string2 = value_term.string;
                term.type2 = 'value';
                terms.push(term);
            }
        } else if (star_term.state == 'complete') {
            if (class_term.state == 'incomplete') {
                term = new this.Term(1, last_term.string, 'class');
                term.string1 = star_term.string;
                term.type1 = 'value';
                term.string2 = star_term.string;
                term.type2 = 'value';
                terms.push(term);

                term = new this.Term(1, last_term.string, 'class');
                term.string1 = star_term.string;
                term.type1 = 'attr';
                term.string2 = star_term.string;
                term.type2 = 'attr';
                terms.push(term);

            } else if (attr_term.state == 'incomplete') {
                term = new this.Term(1, last_term.string, 'attr');
                term.string1 = star_term.string;
                term.type1 = 'value';
                term.string2 = star_term.string;
                term.type2 = 'value';
                terms.push(term);

                term = new this.Term(1, last_term.string, 'attr');
                term.string1 = star_term.string;
                term.type1 = 'class';
                term.string2 = star_term.string;
                term.type2 = 'class';
                terms.push(term);

            } else if (value_term.state == 'incomplete') {
                term = new this.Term(1, last_term.string, 'value');
                term.string1 = star_term.string;
                term.type1 = 'class';
                term.string2 = star_term.string;
                term.type2 = 'class';
                terms.push(term);
                term = new this.Term(1, last_term.string, 'value');
                term.string1 = star_term.string;
                term.type1 = 'attr';
                term.string2 = star_term.string;
                term.type2 = 'attr';
                terms.push(term);
            } else {
                term = new this.Term(1, last_term.string, 'class');
                term.string1 = star_term.string;
                term.type1 = 'value';
                term.string2 = star_term.string;
                term.type2 = 'value';
                terms.push(term);

                term = new this.Term(1, last_term.string, 'class');
                term.string1 = star_term.string;
                term.type1 = 'attr';
                term.string2 = star_term.string;
                term.type2 = 'attr';
                terms.push(term);

                term = new this.Term(1, last_term.string, 'attr');
                term.string1 = star_term.string;
                term.type1 = 'value';
                term.string2 = star_term.string;
                term.type2 = 'value';
                terms.push(term);

                term = new this.Term(1, last_term.string, 'attr');
                term.string1 = star_term.string;
                term.type1 = 'class';
                term.string2 = star_term.string;
                term.type2 = 'class';
                terms.push(term);

                term = new this.Term(1, last_term.string, 'value');
                term.string1 = star_term.string;
                term.type1 = 'attr';
                term.string2 = star_term.string;
                term.type2 = 'attr';
                terms.push(term);

                term = new this.Term(1, last_term.string, 'value');
                term.string1 = star_term.string;
                term.type1 = 'class';
                term.string2 = star_term.string;
                term.type2 = 'class';
                terms.push(term);

            }
        } else if (class_term.state == 'incomplete') {
            term = new this.Term(0, last_term.string, 'class');
            terms.push(term);
        } else if (attr_term.state == 'incomplete') {
            term = new this.Term(0, last_term.string, 'attr');
            terms.push(term);
        } else if (value_term.state == 'incomplete') {
            term = new this.Term(0, last_term.string, 'value');
            terms.push(term);
        } else if (star_term.state == 'incomplete') {
            term = new this.Term(0, last_term.string, 'class');
            terms.push(term);
            term = new this.Term(0, last_term.string, 'attr');
            terms.push(term);
            term = new this.Term(0, last_term.string, 'value');
            terms.push(term);
        }

        if (class_term.state == 'incomplete') {
            searchStr = class_term.string;
        } else if (value_term.state == 'incomplete') {
            searchStr = value_term.string;
        } else if (attr_term.state == 'incomplete') {
            searchStr = attr_term.string;
        } else if (star_term.state == 'incomplete') {
            searchStr = star_term.string;
        } else {
            searchStr = '';
        }

        return {'terms': terms, searchString: searchStr};
    };

    function loadMatch2(type1, type2, incompleteType, string1, string2, incompleteString) {
        /* ************************************************************************************
        * This will create a list of terms that meet the criteria of matching two completed
        * terms and a partial match of the third term.  The terms are class, attr, and value.
        * It does not matter which two are complete and which one is partial.
        *
        * Creating a list that matches one complete and one partial is accomplished by specifying
        * the same type for type1 and type2 thus effectively matching only one completed word
        * *************************************************************************************/
        var firstString, secondString, thirdString;
        var match_set = [];
        var type_map = {'class': 0, 'attr': 1, 'value': 2};
        var prefix_map = {'class': 'c', 'attr': 'a', 'value': 'v'};
        var prefix = prefix_map[incompleteType];
        var s1 = type_map[type1];
        var s2 = type_map[type2];
        var s3 = type_map[incompleteType];

        for (var i = 0, tot = class_attr_values.length; i < tot; i++) {
            firstString = class_attr_values[i][s1];
            secondString = class_attr_values[i][s2];
            thirdString = class_attr_values[i][s3];
            if ((firstString == string1) && (secondString == string2)) {
                if (thirdString.toLowerCase().indexOf(incompleteString.toLowerCase()) == 0) {
                    match_set.push(prefix + thirdString);
                }
            }
        }
        return match_set;
    }

    function loadMatch1(incompleteType, incompleteString) {
        /* ************************************************************************************
         * This will create a list of terms that meet the criteria of a partial match of one item.
         * It will match only those terms of the specified type.
         * *************************************************************************************/
        var firstString;
        var match_set = [];
        var type_map = {'class': 0, 'attr': 1, 'value': 2};
        var prefix_map = {'class': 'c', 'attr': 'a', 'value': 'v'};
        var prefix = prefix_map[incompleteType];
        var s1 = type_map[incompleteType];

        for (var i = 0, tot = class_attr_values.length; i < tot; i++) {
            firstString = class_attr_values[i][s1];
            if (firstString.toLowerCase().indexOf(incompleteString.toLowerCase()) == 0) {
                match_set.push(prefix + firstString);
            }
        }
        return match_set;
    }

    this.search = function search(terms) {

        var matches;
        //
        // what search terms to load depends upon
        // what the total search is
        //
        // if cv complete search in cav
        // if ca complete search in cav
        // if va complete search in cav
        // if c complete search in ca, cv
        // if a complete search in ca, av
        // if v complete search in cv, av
        // if none complete search in c, a, v
        //
        function onlyUnique(match_set) {
           var u = {}, a = [];
           for(var i = 0, l = match_set.length; i < l; ++i){
              if(u.hasOwnProperty(match_set[i])) {
                 continue;
              }
              a.push(match_set[i]);
              u[match_set[i]] = 1;
           }
           return a;
        }

        var match_set = [];

        for (var i = 0, tot = terms['terms'].length; i < tot; i++) {
            var term = terms['terms'][i];

            if ((term.complete == 2) || (term.complete == 1)) {
                match_set.extend(loadMatch2(term.type1,
                    term.type2,
                    term.incomplete_type,
                    term.string1,
                    term.string2,
                    term.incomplete_str));
            }
            if (term.complete == 0) {
                match_set.extend(loadMatch1(term.incomplete_type, term.incomplete_str));
            }

        }
        matches = onlyUnique(match_set);
        return matches;
    }
} //end AutoCompleteTerms

AutoCompleteTerms.prototype.Term = function (complete, incomplete_str, incomplete_type) {
    this.complete = complete;
    this.type1 = '';
    this.type2 = '';
    this.incomplete_type = incomplete_type;
    this.string1 = '';
    this.string2 = '';
    this.incomplete_str = incomplete_str;
};

function autoComplete(autoCompleteTerms, callBack) {
    var margin = {top: 20, right: 10, bottom: 10, left: 10};
    this.width = 100 - margin.left - margin.right;
    var height = 100 - margin.top - margin.bottom;
    var lastSearchString,
        selectedCallBack = callBack;
    var searchTerms = [];
    var onSpaceDone = false;
    var matches = [];
    var validTerms = []; // will track terms that are known to match actual valid terms
    var re_end = new RegExp('([^@=#*]*)$');
    function alphabetical(a, b) {
        // name field
         var A = a.substring(1);
         var B = b.substring(1);
         if (A < B){
            return -1;
         }else if (A > B){
           return  1;
         }else{
           return 0;
         }
    }

    var container = d3.select("body").select("#autoComplete");
    var enter = container.append("div")
        .attr("id", "ac")
        .attr("class", "ac")
        .append("div")
        .attr("class", "blank-row")
        .append("div")
        .attr("style", "ac-holder");

    container.attr("width", this.width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom);

    var input = enter.append("input")
        .attr("class", "ac-form-control")
        .attr("placeholder", "Search: enter one of more #<class>, @<attributes>, or =<values>")
        .attr("type", "text")
        .on("keyup", onKeyUp);

    var sButton = enter.append("input")
        .attr("type", "button")
        .attr("class", "ac-submit-control")
        .attr("value", "search")
        .on("click", sButtonSelect);

    var searching = enter.append("div").attr("class", "ac-searching")
        .text("");

    var dropDown = enter.append("div").attr("class", "ac-dropdown")
                        .style("display", "none");

    function onKeyUp() {
        var searchString = input.node().value.trim().replace(/\s\s+/g, ' ');
        //var searchString = document.getElementById("new_search").value.trim().replace(/\s\s+/g, ' ');
        //var subSearchString = searchString.split(' ').pop();
        var subSearchString = SearchSplit(searchString).pop();
        var e = d3.event;
        const ASCII_SPACE = 32;
        const ASCII_CR = 13;
        const ASCII_AMP = 38;
        const ASCII_LEFTPAR = 40;
        const ASCII_TAB = 9;
        const ASCII_RIGHT = 39;
        //console.log('new search: '+document.getElementById("new_search").value);
        //console.log('key is '+e.which);
        if (!(e.which === ASCII_AMP || e.which === ASCII_RIGHT || e.which === ASCII_CR || e.which===ASCII_SPACE)) {
            // is up/down arrow or enter
            if (!subSearchString || subSearchString === "") {
                showSearching("No results");
                hideDropDown();
                lastSearchString = "";
            } else if (isNewSearchNeeded(subSearchString, lastSearchString)) {
                lastSearchString = subSearchString;
                showSearching();
                var terms = autoCompleteTerms.buildSearch(subSearchString);
                //console.log(terms);
                onSpaceDone = false;  // allow the matched item to be added with a <sp>
                getMatchResult(searchString, terms);
                //console.log(matches);
                //matches = autoCompleteTerms.search(terms);
                //processResults(matches, terms);
                //if (matches.length === 0) {
                //    showSearching("No results");
                //}
                //else {
                //    hideSearching();
                //    showDropDown();
                //}
            }

        } else {
            if (e.which===ASCII_SPACE) {
                //console.log('Space');
                //onSpace();
            }
            if (e.which===ASCII_CR) {
                //console.log('Done');
                hideDropDown();
                showSearching("Searching...");
                spinner.spin(target);
                selectedCallBack(input.node().value);
                //searchTerms = [];
            }
            if (e.which===ASCII_RIGHT) {
                //console.log('Right Arrow');
                onRIGHT();
            }
        }

    }

    // this will search for the searchString in the portData
    // array and update the matches array with all the ones
    // that match.
    // It will anchor the search at the beginning of the string
    // Changing the comparison to 'indexOf' from == 0 to >= 0 will
    // allow the search to match anywhere.
    function showSearching(value) {
        searching.style("display", "block");
        searching.text(value);
    }

    // checks to see if the newTerm has some characters
    // and it is different from the oldTerm
    function isNewSearchNeeded(newTerm, oldTerm) {
        return newTerm.length >= 1 && newTerm != oldTerm;
    }

    function processResults(matches, terms) {

        var searchString = terms.searchString;
        var results = dropDown.selectAll(".ac-row").data(matches.sort(alphabetical), function (d) {return d;});
        results.enter()
            .append("div").attr("class", "ac-row")
            .on("click", function (d) { row_onClick(d); })
            .append("div").attr("class", "ac-title")
            .html(function (d) {
                var re = new RegExp(searchString, 'i');
                var strPart = d.substring(1).match(re)[0];

                return "<span class= 'ac-hint'>" + d[0]+ " </span>" +
                    d.substring(1).replace(re, "<span class = 'ac-highlight'>" + strPart + "</span>");

            });

        results.exit().remove();

        //Update results

        results.select(".ac-title")
            .html(function (d, i) {
                var re = new RegExp(searchString, 'i');
                var strPart = matches[i].substring(1).match(re);
                var strng = matches[i];
                var offset = 1;
                if (strng.indexOf(" ")> 0) {
                    strng = strng[0]+"\""+strng.substring(1)+"\"";
                    offset = 2;
                }
                //console.log(strng);

                if (strPart) {
                    strPart = strPart[0];
                    var response = "<span class= 'ac-hint'>" + strng[0]+ " </span>";
                    if (offset==2) {
                        response += strng[1];
                    }
                    response += strng.substring(offset)
                        .replace(re, "<span class = 'ac-highlight'>" + strPart + "</span>");
                    return response;
                }

            });
    }
    function showDropDown() {
        dropDown.style("display", "block");
    }
    function hideSearching() {
        searching.style("display", "none");
    }

    function hideDropDown() {
        dropDown.style("display", "none");
    }

    function row_onClick(d) {
        var selectedTerm = d;
        autoFill(selectedTerm);
    }

    function autoFill(selectedTerm) {
        hideDropDown();
        searchTerms = SearchSplit(input.node().value);
        var lastTerm = searchTerms.pop();

        // now need to fix-up the last term
        var pattern;
        if (selectedTerm.indexOf(" ") > -1) {
            pattern = lastTerm.replace(/[^#@=*]*$/, "\""+selectedTerm.substring(1)+"\"");
        } else {
            pattern = lastTerm.replace(/[^#@=*]*$/, selectedTerm.substring(1));
        }
        searchTerms.push(pattern);
        input.node().value = searchTerms.join(' ');
        onSpaceDone = true;


    }
    function onRIGHT() {
        if (matches.length > 0) {
            var selectedTerm = matches[0];
            autoFill(selectedTerm);
        }
    }

    function sButtonSelect() {
        //console.log("sButton selected");
        hideDropDown();
        showSearching("Searching...");
        spinner.spin(target);
        selectedCallBack(input.node().value);
        //searchTerms = [];
    }

    function getMatchResult(searchString, terms) {
        d3.json("/term_complete/terms?" + $.param({searchString}), function (error, term_string) {
            matches = term_string['result'];
            processResults(matches, terms);
            if (matches.length === 0) {
                showSearching("No results");
            }
            else {
                hideSearching();
                showDropDown();
            }

        })
    }

}

