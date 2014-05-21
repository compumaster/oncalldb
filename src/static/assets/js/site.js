//  Copyright 2014 Sinan Ussakli. All rights reserved.
//   Use of this source code is governed by a BSD-style license that can be found in the LICENSE file.

﻿(function($,len,createRange,duplicate){
	$.fn.caret=function(options,opt2){
		var start,end,t=this[0];

		if(typeof options==="object" && typeof options.start==="number" && typeof options.end==="number") {
			start=options.start;
			end=options.end;
		} else if(typeof options==="number" && typeof opt2==="number"){
			start=options;
			end=opt2;
		} else if(typeof options==="string"){
			if((start=t.value.indexOf(options))>-1) end=start+options[len];
			else start=null;
		} else if(Object.prototype.toString.call(options)==="[object RegExp]"){
			var re=options.exec(t.value);
			if(re != null) {
				start=re.index;
				end=start+re[0][len];
			}
		}
		if(typeof start!="undefined"){
			if(browser){
				var selRange = this[0].createTextRange();
				selRange.collapse(true);
				selRange.moveStart('character', start);
				selRange.moveEnd('character', end-start);
				selRange.select();
			} else {
				this[0].selectionStart=start;
				this[0].selectionEnd=end;
			}
			this[0].focus();
			return this
		} else {
           if(typeof t.selectionStart == "number" && typeof t.selectionEnd == "number"){
               	var s=t.selectionStart,
					e=t.selectionEnd;
           }
           else
           {
				var selection=document.selection;
                if (this[0].tagName.toLowerCase() != "textarea") {
                    var val = this.val(),
                    range = selection[createRange]()[duplicate]();
                    range.moveEnd("character", val[len]);
                    var s = (range.text == "" ? val[len]:val.lastIndexOf(range.text));
                    range = selection[createRange]()[duplicate]();
                    range.moveStart("character", -val[len]);
                    var e = range.text[len];
                } else {
                    var range = selection[createRange](),
                    stored_range = range[duplicate]();
                    stored_range.moveToElementText(this[0]);
                    stored_range.setEndPoint('EndToEnd', range);
                    var s = stored_range.text[len] - range.text[len],
                    e = s + range.text[len]
                }
			}
			var te=t.value.substring(s,e);
			return {start:s,end:e,text:te,replace:function(st){
				return t.value.substring(0,s)+st+t.value.substring(e,t.value[len])
			}}
		}
	}
})(jQuery,"length","createRange","duplicate");

function hen(d, a, b) {
    var o = document.getElementById(d);
    var tmp = o.scrollTop;
    o.focus();
    if (document.selection && !window.opera) {
        var rg = document.selection.createRange();
        if (rg.parentElement() == o) {
            rg.text = a + rg.text + b;
            rg.select();
        } else alert("please select some text to process");
    }
    else if (o.selectionStart || o.selectionStart == '0') {
        var s = o.value;
        var end = o.selectionEnd;
        var start = o.selectionStart;
        o.value = s.substring(0, start) + a + s.substring(start, end) + b + s.substring(end);
        end += a.length + b.length;
        o.setSelectionRange(end, end);
    } else o.value += a + b;
    o.scrollTop = tmp;
    return true;
}
function initTrip()
{
    var triplog = 0;
    switch (endpoint)
    {
        case "home":
            triplog = [
                {
                    sel: $("#latest-tab"),
                    position: "e",
                    content: "This tab shows call records you have entered, <br/>most recent first. <br/><br/>The number in parenthesis shows number of <br/>records found. Maximum shown is 100.",
                    delay : -1,
                    showNavigation: true
                },
                {
                    sel: $("#flagged-tab"),
                    position: "s",
                    content: "This tab shows flagged calls. <br/><br/>Flagging a call is to create a reminder <br/>about that call, like a bookmark. <br/>Only you can see your own flagged calls.",
                    delay : -1,
                    showNavigation: true
                },
                {
                    sel: $("#commented-tab"),
                    position: "s",
                    content: "This tab shows your calls that are <br/>commented by you or others. <br/>Sorted by most recent comment first.",
                    delay : -1,
                    showNavigation: true
                },
                {
                    sel: $("#comment-header"),
                    position: "n",
                    content: "This icon means comments. <br/>This column shows a number if there are <br/>any comments entered to this call.",
                    delay : -1,
                    showNavigation: true
                }

            ];
            break;
        case "search":
            triplog = [
                {
                    sel: $("#q"),
                    position: "s",
                    content: "Search query, what you enter here should be different on different search methods. <br/>" +
                        "By default, query mode is simple. Just enter keywords without any operators.<br/>" +
                        "Operators like NOT, -, +, parenthesis are not supported on simple mode. <br/>" +
                        "Sometimes you don't need to enter anything here.",

                    delay : -1,
                    showNavigation: true
                },
                {
                    sel: $("#meta"),
                    position: "s",
                    content: "If selected, searches in meta-data section.<br/>" +
                        "Meta-data includes everything <span style='text-decoration: underline;'>except</span>: <br/>" +
                        "<ul><li>Relevant Information</li>" +
                        "<li>Action Taken</li>" +
                        "<li>Follow Up</li></ul>",
                    delay : -1,
                    showNavigation: true
                },
                {
                    sel: $("#body"),
                    position: "s",
                    content: "If selected, searches in body section.<br/>" +
                        "Body section includes: <br/>" +
                        "<ul><li>Relevant Information</li>" +
                        "<li>Action Taken</li>" +
                        "<li>Follow Up</li></ul>",
                    delay : -1,
                    showNavigation: true
                },
                {
                    sel: $("#adv"),
                    position: "s",
                    content: "If selected, changes search mode to advanced.<br/>" +
                        "Advanced query is very strict, uses boolean operators.<br/>" +
                        "To search for: one of term1 or term2, and term3, but not term4<br/>" +
                        "You should enter (term1 | term2) &amp; term3 &amp; ! term4<br/>" +
                        "These operators are allowed:<br/>" +
                        "<ul><li>Parenthesis: ( ): used for grouping</li>" +
                        "<li>&amp;: this is the AND operator.</li>" +
                        "<li>|: this is the OR operator.</li>" +
                        "<li>!: this is the NOT operator.</li></ul>",
                    delay : -1,
                    showNavigation: true
                },
                {
                    sel: $("#s2id_hosp"),
                    position: "e",
                    content: "To filter by hospital, select one from list.",
                    delay : -1,
                    showNavigation: true
                },
                {
                    sel: $("#s2id_resident"),
                    position: "e",
                    content: "To filter by resident, select one from list.",
                    delay : -1,
                    showNavigation: true
                },
                {
                    sel: $("#s2id_class"),
                    position: "e",
                    content: "To filter by classification, select one from list.",
                    delay : -1,
                    showNavigation: true
                },
                {
                    sel: $("#todt"),
                    position: "e",
                    content: "To filter results between 2 dates, select a date range.",
                    delay : -1,
                    showNavigation: true
                },
                {
                    sel: $("#s2id_recenttype"),
                    position: "e",
                    content: "To filter results for a recency, enter a time span value (number), and select the type.",
                    delay : -1,
                    showNavigation: true
                },
                {
                    sel: $("#s2id_sortby"),
                    position: "e",
                    content: "Select to override the sort.<br/>" +
                        "By default, results are sorted with most logical way.<br/>" +
                        "<ul><li>when there is a query, by relevance, </li>" +
                        "<li>when there is no query but recent is selected, by date, etc.</li></ul>",
                    delay : -1,
                    showNavigation: true
                },
                {
                    sel: $("#search-button"),
                    position: "n",
                    content: "Once you search, there will be [Print these records] button.<br/>" +
                        "Pressing that will take you to a new page, <br/>" +
                        "which allows you to print results in bulk.",
                    delay : -1,
                    showNavigation: true
                }
            ];
            break;
        case "new":
            triplog = [
                {
                    sel: $("#date_of_call"),
                    position: "s",
                    content: "A valid date in MM/DD/YYYY format is required in this field.",
                    delay : -1,
                    showNavigation: true
                },
                {
                    sel: $("#time_of_call"),
                    position: "s",
                    content: "A valid time in HH:MM format (24 h) is required in this field.",
                    delay : -1,
                    showNavigation: true
                },
                {
                    sel: $("#specific_request"),
                    position: "s",
                    content: "Try to capitalize this field with 'Sentence case, where only the first letter is capital'",
                    delay : -1,
                    showNavigation: true
                },
                {
                    sel: $("#relevant_info"),
                    position: "n",
                    content: "These body fields can hold VERY large text.",
                    delay : -1,
                    showNavigation: true
                },
                {
                    sel: $("#relevant-call-shortcut"),
                    position: "n",
                    content: "Body fields contains these buttons.<br/>" +
                        "LinkTo creates '(call: )' shortcut.<br/>" +
                        "If you want to link to a different call just type it's ID, <br/>" +
                        "highlight the ID, and press this button.<br/>" +
                        "For example: (call: 12345) will create a link to call #12345.",
                    delay : -1,
                    showNavigation: true
                },
                {
                    sel: $("#relevant-pmid-shortcut"),
                    position: "n",
                    content: "PMID creates '(pmid: )' shortcut.<br/>" +
                        "If you want to create a reference to a PUBMED article, <br/>" +
                        "link it with this shortcut. This will create a hyperlink<br/>" +
                        "to the PUBMED article.",
                    delay : -1,
                    showNavigation: true
                },
                {
                    sel: $("#relevant-templates-shortcut"),
                    position: "n",
                    content: "You can define as many templates as you would like.<br/>" +
                        "You can name these templates, and if you star them, <br/>" +
                        "they will be visible at this drop down. <br/>" +
                        "The More... selection is to define new templates.",
                    delay : -1,
                    showNavigation: true
                },
                {
                    sel: $("#tag"),
                    position: "w",
                    content: "The database contains some predefined tags.<br/>" +
                        "Feel free to use them and ask for more.<br/>" +
                        "To tag an entry, type it's name. Autocomplete<br/>" +
                        "will help you find a tag. Hit enter to accept<br/>" +
                        "autocomplete, hit enter again to add the tag.</br>" +
                        "Once added, you can remove a tag by hitting <br/>" +
                        "x near the tag.",
                    delay : -1,
                    showNavigation: true
                }
            ];
            break;
        case "list":
            triplog = [
                {
                    sel: $("#header-comment"),
                    position: "w",
                    content: "Shows number of comments for this entry.",
                    delay : -1,
                    showNavigation: true
                },
                {
                    sel: $("#header-edit"),
                    position: "w",
                    content: "If you have rights to edit this entry,<br/>" +
                        "there will be a link in this column.",
                    delay : -1,
                    showNavigation: true
                },
                {
                    sel: $("#pagination"),
                    position: "n",
                    content: "We have pagination.",
                    delay : -1,
                    showNavigation: true
                }
            ];
            break;
        case "tags":
            triplog = [
                {
                    sel: $("#tags-list"),
                    position: "s",
                    content: "These are the defined tags in the system. Clicking each of them will take you <br/>" +
                        "to a new page that shows the entries tagged with that particular tag.",
                    delay : -1,
                    showNavigation: true
                }
            ];
        case "users":
            triplog = [
                {
                    sel: $("#header-users"),
                    position: "e",
                    content: "All of the users defined in this system are listed here.<br/>" +
                        "Clicking on username will take you to a page that has more information about that user. <br/>" +
                        "Please update your information by either clicking your username on this page or at top right corner.",
                    delay : -1,
                    showNavigation: true
                },
                {
                    sel: $("#hide-users-button"),
                    position: "n",
                    content: "Inactive users are grouped here.",
                    delay : -1,
                    showNavigation: true
                }
            ];
            break;
        default:
            break;
    }

    if (triplog)
    {
        var trip = new Trip(triplog,
            {
            tripTheme : "black",
            onTripStart : function() {
                console.log("onTripStart");
            },
            onTripEnd : function() {
                console.log("onTripEnd");
            },
            onTripStop : function() {
                console.log("onTripStop");
            },
            onTripChange : function(index, tripBlock) {
                console.log("onTripChange");
            },
            backToTopWhenEnded : true,
            delay : 2000
        });
        $("#start-tour").click(function()
        {
            trip.start();
        });
        window.trip = trip;
    }
}

function flag(id, flag)
{
    flag = typeof flag !== 'undefined' ? flag : $("#flagrecord").data("flag");

    $.ajax({
        type: "GET",
        cache: false,
        url: "ajax?action=flag&id=" + id + "&flag=" + flag,
        success: function(data) {
            $("#flagrecord").removeClass("btn-success").removeClass("btn-warning").removeClass("btn-danger").removeClass("btn-info");
            if (data == '0') {
                $("#flagrecord").find('span').html('Flag this record');
            }
            else
            {
                $("#flagrecord").find('span').html('This record is flagged');
                $("#flagrecord").data("flag", data);
                switch (data) {
                    case '1':
                        $("#flagrecord").addClass("btn-success");
                        break;
                    case '2':
                        $("#flagrecord").addClass("btn-warning");
                        break;
                    case '4':
                        $("#flagrecord").addClass("btn-danger");
                        break;
                    case '8':
                        $("#flagrecord").addClass("btn-info");
                        break;
                    default:
                        break;
                };
            }
        }
    });
}