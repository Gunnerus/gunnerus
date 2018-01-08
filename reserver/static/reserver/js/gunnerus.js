function DayDiff(CurrentDate, compareDate) {
	var TYear=CurrentDate.getFullYear();
	var TDay=new Date(compareDate);
	TDay.getFullYear(TYear);
	var DayCount=(TDay-CurrentDate)/(1000*60*60*24);
	DayCount=Math.round(DayCount); 
	return(DayCount);
}

function postpone(fun) {
    window.setTimeout(fun, 0);
}

function showDialog(title, message, footer) {
    $('#txtModal').modal('hide');
    // demo: showDialog('Room sharing', message);
    var headerContent = title;
    var bodyContent = message;
    if (typeof footer !== "undefined") {
        footerContent = footer;
    } else {
        footerContent = '<button type="button" class="btn btn-default" data-dismiss="modal">Close</button>';
    }
    document.querySelector("#txtModal").style.marginTop = document.querySelector(".navbar-header").offsetHeight + "px";
    $('#txtModal .modal-title').html(headerContent);
    $('#txtModal .modal-body').html(bodyContent);
    $('#txtModal .modal-footer').html(footerContent);
    $('#txtModal').modal('show');
    $('#txtModal .toggleModal').click(function (ev) { modalClickHandler(ev, this); });
    document.querySelector('#txtModal').focus();
    $("#txtModal .modal-content").click();
}

function modalClickHandler(clickEvent, clickedObject) {
	clickEvent.preventDefault();
	console.log("toggle modal executed");
	console.log(clickedObject);
	var pid = $(clickedObject).data('modal');
	$.get('/modals/' + pid + '.txt', function(data){
		var headerRegex = /(?:<header>)(.|[\r\n])*(?:<\/header>)/g;
		var contentRegex = /(?:<content>)(.|[\r\n])*(?:<\/content>)/g;
		var headerContent = headerRegex.exec(data)[0];
		var bodyContent = contentRegex.exec(data)[0];
		document.querySelector("#txtModal").style.marginTop = document.querySelector(".navbar-header").offsetHeight+"px";
		$('#txtModal .modal-title').html(headerContent);
		$('#txtModal .modal-body').html(bodyContent);
		$('#txtModal').modal('show');
		$('#txtModal .toggleModal').click(function(ev){modalClickHandler(ev, this);});
		document.querySelector('#txtModal').focus();
		$("#txtModal .modal-content").click();
	});
}

var datepicker_options = {
	format: 'yyyy-mm-dd',
	todayHighlight: true,
	autoclose: true,
};

var datetimepicker_options = {
	format: 'YYYY-MM-DD HH:mm',
}

function scrollHandler() {
	if ($(document).scrollTop() > 50) {
		$("body").addClass("scrolled");
		$("#scrollUpButton").slideDown(100);
	} else {
		$("body").removeClass("scrolled");
		$("#scrollUpButton").slideUp(100);
	}
}

function add_scroll_up_button() {
	$("body").append('<a href="#" id="scrollUpButton"><i class="fa fa-arrow-circle-up" aria-hidden="true"></i></a>');
	scrollHandler();
	$(window).scroll(function() {
		clearTimeout(window.scrollFinished);
		window.scrollFinished = setTimeout(function(){
			scrollHandler();
		}, 250);
	});
}

$(document).ready(function() {
	$("#hijacked-warning").addClass("alert-warning");
	$(".django-hijack-button-bootstrap").addClass("btn-primary").removeClass("btn-sm");
	if (!document.querySelector("#hijacked-warning")) {
		$(".hijack-container").hide();
	}
	
	if (document.querySelector(".mainpage-alerts-container")) {
		$("#hijacked-warning").prependTo(".mainpage-alerts-container");
	} else if (document.querySelector(".msg-container")) {
		$("#hijacked-warning").prependTo(".msg-container");
	}
	
	/* Check if we're running in a dev environment, and throw up a warning in the header */
	if (/^dev\.rvgunnerus.no/g.test(window.location.hostname) || /^127.0.0.1/g.test(window.location.hostname)) {
		$(".navbar-brand span").addClass("label label-danger strong-warning");
		$(".navbar-brand span").prepend('<img class="icon icons8-Code" width="48" height="48" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAACaklEQVRoQ+1a0XHUMBTcrQA6IOkgqQBSAXRAqADoACoAKgA6gAoIFZAOklQAVLDMZuSbdzr5LHPy2AfWz110tvT27fppZYU48sYjjx8rgLkZXBlYJAOSTgC8A3AGwN/nbLcArgG8IPkrD2RHQpIeArgB4M8lNQd/moMoAfgC4OmSIg+xfCX5LMZWAvBzgdnvYr4leToEQAvN/n1YJLeSXmJgBTAlg/8fAzniKbNbGlvSlqRHM7ACOJCylYFDJJQ8lW1J1+5IjvJWkzBgv1QyVrlaJF0C+Bj6P5N0307rG3MqAN9SBHaIdovFJukTgOfhR1/vvk1LLN2DJHlRSELbKiTpVbLanssO8Q3JDz1ZtXyiZOwmN4AlvfT9wXu9Jvk+A9gOQMrWj8zsfSf5pJA5B75X/5KuADwO9zoh5xnIpgAsnRjsb296SjKq0X9KiDcrDwKIqyilZs9AJp1uvh3Kux9q9O9rh8ZtAmCMdAKAvfrPdN4rpZYAcqqvSZ73PLyD+s8A9EqzCYBEdV7T3f2WpKvIVqvRf2AqVrUdaTYDkECU9ssXJC2BWNsH638az0ztrWqtAfhNhet4rBr+26Vv88pDUpX+JQ1WtaYAUtZcRruV2F1blWiM/5HkNwxmq0vItAtZ0K1XSwO5JOmHO8qn2v+khJhVg7C/Ki2I7RayAKDXzNXW/1L16qlo7QHsm7xW/4sFUBtY7XXNH+LaiVtdtwI4ZEvZgoW/YcAL06MWk08wxs6e+p98vV6yCxMkc/SQ3jydDB5wZKujj5jmltNdOmLyqj98xDQ6LzPfsB6zzkzA+q8GcxNw/Az8AeBl10ARUzf1AAAAAElFTkSuQmCC"> ');
	}
	
	/* Add scroll up button, but not on the cruise form */
	if (!document.querySelector(".submitButtonsContainer") && !document.querySelector("#id_management_of_change")) {
		add_scroll_up_button();
	}
	
	$('#txtModal').modal('hide');
	$('.toggleModal').click(function(ev){modalClickHandler(ev, this);});
	
	$("#navbar.in a").not(".dropdown-toggle").click(function() { 
		$('.navbar-toggle').click();
	});
	
	$(document).click(function(event) { 
		if(!$(event.target).closest('#navbar').length) {
			if($('#navbar').is(".in")) {
				$('.navbar-toggle').click();
			}
		}        
	});
	
	$(document).ready(function() {
	  $('.panel-collapse').on('show.bs.collapse', function () {
		$(this).siblings('.panel-heading').addClass('active');
	  });

	  $('.panel-collapse').on('hide.bs.collapse', function () {
		$(this).siblings('.panel-heading').removeClass('active');
	  });
	});
	
	$('input[name="date_of_birth"], input#id_date, input#id_season_event_start_date, input#id_season_event_end_date, input#id_search_start_date, input#id_search_end_date').datepicker(datepicker_options);
	$('input#id_start_time, input#id_end_time, input#id_internal_order_event_date, input#id_external_order_event_date').datetimepicker(datetimepicker_options);
});

(function(){Date.shortMonths=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],Date.longMonths=["January","February","March","April","May","June","July","August","September","October","November","December"],Date.shortDays=["Sun","Mon","Tue","Wed","Thu","Fri","Sat"],Date.longDays=["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"];var t={d:function(){var t=this.getDate();return(t<10?"0":"")+t},D:function(){return Date.shortDays[this.getDay()]},j:function(){return this.getDate()},l:function(){return Date.longDays[this.getDay()]},N:function(){var t=this.getDay();return 0==t?7:t},S:function(){var t=this.getDate();return t%10==1&&11!=t?"st":t%10==2&&12!=t?"nd":t%10==3&&13!=t?"rd":"th"},w:function(){return this.getDay()},z:function(){var t=new Date(this.getFullYear(),0,1);return Math.ceil((this-t)/864e5)},W:function(){var t=new Date(this.valueOf()),e=(this.getDay()+6)%7;t.setDate(t.getDate()-e+3);var n=t.valueOf();t.setMonth(0,1),4!==t.getDay()&&t.setMonth(0,1+(4-t.getDay()+7)%7);var r=1+Math.ceil((n-t)/6048e5);return r<10?"0"+r:r},F:function(){return Date.longMonths[this.getMonth()]},m:function(){var t=this.getMonth();return(t<9?"0":"")+(t+1)},M:function(){return Date.shortMonths[this.getMonth()]},n:function(){return this.getMonth()+1},t:function(){var t=this.getFullYear(),e=this.getMonth()+1;return 12===e&&(t=t++,e=0),new Date(t,e,0).getDate()},L:function(){var t=this.getFullYear();return t%400==0||t%100!=0&&t%4==0},o:function(){var t=new Date(this.valueOf());return t.setDate(t.getDate()-(this.getDay()+6)%7+3),t.getFullYear()},Y:function(){return this.getFullYear()},y:function(){return(""+this.getFullYear()).substr(2)},a:function(){return this.getHours()<12?"am":"pm"},A:function(){return this.getHours()<12?"AM":"PM"},B:function(){return Math.floor(1e3*((this.getUTCHours()+1)%24+this.getUTCMinutes()/60+this.getUTCSeconds()/3600)/24)},g:function(){return this.getHours()%12||12},G:function(){return this.getHours()},h:function(){var t=this.getHours();return((t%12||12)<10?"0":"")+(t%12||12)},H:function(){var t=this.getHours();return(t<10?"0":"")+t},i:function(){var t=this.getMinutes();return(t<10?"0":"")+t},s:function(){var t=this.getSeconds();return(t<10?"0":"")+t},v:function(){var t=this.getMilliseconds();return(t<10?"00":t<100?"0":"")+t},e:function(){return Intl.DateTimeFormat().resolvedOptions().timeZone},I:function(){for(var t=null,e=0;e<12;++e){var n=new Date(this.getFullYear(),e,1).getTimezoneOffset();if(null===t)t=n;else{if(n<t){t=n;break}if(n>t)break}}return this.getTimezoneOffset()==t|0},O:function(){var t=this.getTimezoneOffset();return(-t<0?"-":"+")+(Math.abs(t/60)<10?"0":"")+Math.floor(Math.abs(t/60))+(0==Math.abs(t%60)?"00":(Math.abs(t%60)<10?"0":"")+Math.abs(t%60))},P:function(){var t=this.getTimezoneOffset();return(-t<0?"-":"+")+(Math.abs(t/60)<10?"0":"")+Math.floor(Math.abs(t/60))+":"+(0==Math.abs(t%60)?"00":(Math.abs(t%60)<10?"0":"")+Math.abs(t%60))},T:function(){var t=this.toLocaleTimeString(navigator.language,{timeZoneName:"short"}).split(" ");return t[t.length-1]},Z:function(){return 60*-this.getTimezoneOffset()},c:function(){return this.format("Y-m-d\\TH:i:sP")},r:function(){return this.toString()},U:function(){return this.getTime()/1e3}};Date.prototype.format=function(e){var n=this;return e.replace(/(\\?)(.)/g,function(e,r,a){return""===r&&t[a]?t[a].call(n):a})}}).call(this);

/* toISOString polyfill */
if (!Date.prototype.toISOString) {
  (function() {

    function pad(number) {
      if (number < 10) {
        return '0' + number;
      }
      return number;
    }

    Date.prototype.toISOString = function() {
      return this.getUTCFullYear() +
        '-' + pad(this.getUTCMonth() + 1) +
        '-' + pad(this.getUTCDate()) +
        'T' + pad(this.getUTCHours()) +
        ':' + pad(this.getUTCMinutes()) +
        ':' + pad(this.getUTCSeconds()) +
        '.' + (this.getUTCMilliseconds() / 1000).toFixed(3).slice(2, 5) +
        'Z';
    };

  }());
}

/* search field */

$.expr[":"].contains = $.expr.createPseudo(function(arg) {
return function( elem ) {
	return $(elem).text().toUpperCase().indexOf(arg.toUpperCase()) >= 0;
	};
});

function initialize_search(searchFieldSelector, containerSelector, contentSelector, clearSearchButton) {
	$(searchFieldSelector).parent().parent().append("<div class='no-results-msg'><p class='help-block'>No results match that query.</p></div>");
	$(".no-results-msg").hide();
	$(clearSearchButton).on("click", function(){
		$(searchFieldSelector).val("");
		$(searchFieldSelector).keyup();
	});
	$(searchFieldSelector).keyup(function() {
		var search = $.trim(this.value);
		if (search === "") {
			$(".no-results-msg").hide();
			$(containerSelector).show();
		}
		else {
			$(containerSelector).hide();
			$(containerSelector+" "+contentSelector+":contains('" + search + "')").closest(containerSelector).show(); // show articles that match the current search query
			if ($(containerSelector+':visible').length == 0) {
				$(".no-results-msg").show();
			} else {
				$(".no-results-msg").hide();
			}
		}
	});
}

/* http://addtocalendar.com/
 *
 *
 * @license
 The MIT License (MIT)
 Copyright (c) 2015 AddToCalendar
 Permission is hereby granted, free of charge, to any person obtaining a copy
 of this software and associated documentation files (the "Software"), to deal
 in the Software without restriction, including without limitation the rights
 to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 copies of the Software, and to permit persons to whom the Software is
 furnished to do so, subject to the following conditions:
 The above copyright notice and this permission notice shall be included in all
 copies or substantial portions of the Software.
 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 SOFTWARE.
 */
(function(w,d){var atc_url="//addtocalendar.com/atc/",atc_version="1.5";if(!Array.indexOf){Array.prototype.indexOf=function(obj){for(var i=0,l=this.length;i<l;i++){if(this[i]==obj){return i}}return-1}}if(!Array.prototype.map){Array.prototype.map=function(f){var result=[];for(var i=0,l=this.length;i<l;i++){result.push(f(this[i]))}return result}}var isArray=function(obj){return Object.prototype.toString.call(obj)==="[object Array]"};var isFunc=function(obj){return Object.prototype.toString.call(obj)==="[object Function]"};var ready=function(w,d){var inited=false,loaded=false,queue=[],done,old;function go(){if(!inited){if(!d.body)return setTimeout(go,13);inited=true;if(queue){var j,k=0;while(j=queue[k++])j.call(null);queue=null}}}function check(){if(loaded)return;loaded=true;if(d.readyState==="complete")return go();if(d.addEventListener){d.addEventListener("DOMContentLoaded",done,false);w.addEventListener("load",go,false)}else{if(d.attachEvent){d.attachEvent("onreadystatechange",done);w.attachEvent("onload",go);var k=false;try{k=w.frameElement==null}catch(j){}if(b.doScroll&&k)ie()}else{old=w.onload;w.onload=function(e){old(e);go()}}}}if(d.addEventListener){done=function(){d.removeEventListener("DOMContentLoaded",done,false);go()}}else{if(d.attachEvent){done=function(){if(d.readyState==="complete"){d.detachEvent("onreadystatechange",done);go()}}}}function ie(){if(inited)return;try{b.doScroll("left")}catch(j){setTimeout(ie,1);return}go()}return function(callback){check();if(inited){callback.call(null)}else{queue.push(callback)}}}(w,d);if(w.addtocalendar&&typeof w.addtocalendar.start=="function")return;if(!w.addtocalendar)w.addtocalendar={};addtocalendar.languages={de:"In den Kalender",en:"Add to Calendar",es:"Añadir al Calendario",fr:"Ajouter au calendrier",hi:"कैलेंडर में जोड़ें","in":"Tambahkan ke Kalender",ja:"カレンダーに追加",ko:"캘린더에 추가",pt:"Adicionar ao calendário",ru:"Добавить в календарь",uk:"Додати в календар",zh:"添加到日历"};addtocalendar.calendar_urls={};addtocalendar.loadSettings=function(element){var settings={language:"auto","show-list-on":"click",calendars:["iCalendar","Google Calendar","Outlook","Outlook Online","Yahoo! Calendar"],secure:"auto","on-button-click":function(){},"on-calendar-click":function(){}};for(var option in settings){var pname="data-"+option;var eattr=element.getAttribute(pname);if(eattr!=null){if(isArray(settings[option])){settings[option]=eattr.replace(/\s*,\s*/g,",").replace(/^\s+|\s+$/g,"").split(",");continue}if(isFunc(settings[option])){var fn=window[eattr];if(isFunc(fn)){settings[option]=fn}else{settings[option]=eval("(function(mouseEvent){"+eattr+"})")}continue}settings[option]=element.getAttribute(pname)}}return settings};addtocalendar.load=function(){var calendarsUrl={iCalendar:"ical","Google Calendar":"google",Outlook:"outlook","Outlook Online":"outlookonline","Yahoo! Calendar":"yahoo"};var utz=-(new Date).getTimezoneOffset().toString();var languages=addtocalendar.languages;var dom=document.getElementsByTagName("*");for(var tagnum=0;tagnum<dom.length;tagnum++){var tag_class=dom[tagnum].className;if(tag_class&&tag_class.length&&tag_class.split(" ").indexOf("addtocalendar")!=-1){var settings=addtocalendar.loadSettings(dom[tagnum]);var protocol="http:";if(settings["secure"]=="auto"){protocol=location.protocol=="https:"?"https:":"http:"}else if(settings["secure"]=="true"){protocol="https:"}var tag_id=dom[tagnum].id;var atc_button_title=languages["en"];if(settings["language"]=="auto"){var user_lang="no_lang";if(typeof navigator.language==="string"){user_lang=navigator.language.substr(0,2)}else if(typeof navigator.browserLanguage==="string"){user_lang=navigator.browserLanguage.substr(0,2)}if(languages.hasOwnProperty(user_lang)){atc_button_title=languages[user_lang]}}else if(languages.hasOwnProperty(settings["language"])){atc_button_title=languages[settings["language"]]}var url_paramteres=["utz="+utz,"uln="+navigator.language,"vjs="+atc_version];var addtocalendar_div=dom[tagnum].getElementsByTagName("var");var event_number=-1;for(var varnum=0;varnum<addtocalendar_div.length;varnum++){var param_name=addtocalendar_div[varnum].className.replace("atc_","").split(" ")[0];var param_value=addtocalendar_div[varnum].innerHTML;if(param_name=="event"){event_number++;continue}if(param_name==addtocalendar_div[varnum].className){if(param_name=="atc-body"){atc_button_title=param_value}continue}if(event_number==-1){continue}url_paramteres.push("e["+event_number+"]["+param_name+"]"+"="+encodeURIComponent(param_value))}var atcb_link_id_val=tag_id==""?"":tag_id+"_link";var atcb_list=document.createElement("ul");atcb_list.className="atcb-list";var menu_links="";for(var cnum in settings["calendars"]){if(!calendarsUrl.hasOwnProperty(settings["calendars"][cnum])){continue}var cal_id=calendarsUrl[settings["calendars"][cnum]];var atcb_cal_link_id=tag_id==""?"":'id="'+tag_id+"_"+cal_id+'_link"';menu_links+='<li class="atcb-item"><a '+atcb_cal_link_id+' class="atcb-item-link" href="'+(cal_id=="ical"&&/iPad|iPhone|iPod/.test(navigator.userAgent)&&!window.MSStream?"webcal:":protocol)+atc_url+cal_id+"?"+url_paramteres.join("&")+'" target="_blank" rel="nofollow">'+settings["calendars"][cnum]+"</a></li>"}atcb_list.innerHTML=menu_links;var atcb_link;if(dom[tagnum].querySelector(".atcb-link")==undefined){atcb_link=document.createElement("a");atcb_link.className="atcb-link";atcb_link.innerHTML=atc_button_title;atcb_link.id=atcb_link_id_val;atcb_link.tabIndex=1;dom[tagnum].appendChild(atcb_link);dom[tagnum].appendChild(atcb_list)}else{atcb_link=dom[tagnum].querySelector(".atcb-link");atcb_link.parentNode.appendChild(atcb_list);atcb_link.tabIndex=1;if(atcb_link.id==""){atcb_link.id=atcb_link_id_val}}if(atcb_link.addEventListener){atcb_link.addEventListener("click",settings["on-button-click"],false)}else{atcb_link.attachEvent("onclick",settings["on-button-click"])}var item_links=dom[tagnum].querySelectorAll("atcb-item-link");for(var varnum=0;varnum<item_links.length;varnum++){var item_link=item_links[varnum];if(item_link.addEventListener){item_link.addEventListener("click",settings["on-calendar-click"],false)}else{item_link.attachEvent("onclick",settings["on-calendar-click"])}}}}};addtocalendar.load()})(window,document);