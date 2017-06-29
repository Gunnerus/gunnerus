function DayDiff(CurrentDate, compareDate) {
	var TYear=CurrentDate.getFullYear();
	var TDay=new Date(compareDate);
	TDay.getFullYear(TYear);
	var DayCount=(TDay-CurrentDate)/(1000*60*60*24);
	DayCount=Math.round(DayCount); 
	return(DayCount);
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

$(document).ready(function() {
	
var calendar = $('#calendar').calendar({
	events_source: [
		{
			"id": 293,
			"title": "Tokt 1",
			"url": "test",
			"class": "event-important",
			"start": 1485990000000, // Milliseconds
			"end": 1486162800000 // Milliseconds
		},
		{
			"id": 294,
			"title": "Tokt 2",
			"url": "test",
			"class": "event-important",
			"start": 1486335600000, // Milliseconds
			"end": 1486422000000 // Milliseconds
		},
		{
			"id": 295,
			"title": "Tokt 3",
			"url": "test",
			"class": "event-important",
			"start": 1486508400000, // Milliseconds
			"end": 1486767600000 // Milliseconds
		},
		{
			"id": 296,
			"title": "Tokt 4",
			"url": "test",
			"class": "event-important",
			"start": 1487631600000, // Milliseconds
			"end": 1487718000000 // Milliseconds
		},
		{
			"id": 297,
			"title": "Tokt 5",
			"url": "test",
			"class": "event-important",
			"start": 1487199600000, // Milliseconds
			"end": 1487286000000 // Milliseconds
		},
		{
			"id": 298,
			"title": "Tokt 6",
			"url": "test",
			"class": "event-important",
			"start": 1488150000000, // Milliseconds
			"end": 1488322800000 // Milliseconds
		}/*,
		{
			"id": 299,
			"title": "Tokt 7",
			"url": "test",
			"class": "event-important",
			"start": 1489014000000, // Milliseconds
			"end": 1489100400000 // Milliseconds
		}*/,
		{
			"id": 299,
			"title": "Tokt 10",
			"url": "test",
			"class": "event-important",
			"start": 1489014000000, // Milliseconds
			"end": 1489100400000 // Milliseconds
		},
		{
			"id": 300,
			"title": "Tokt 8",
			"url": "test",
			"class": "event-important",
			"start": 1489100400000, // Milliseconds
			"end": 1489186800000 // Milliseconds
		},
		{
			"id": 301,
			"title": "Tokt 9",
			"url": "test",
			"class": "event-important",
			"start": 1494280800000, // Milliseconds
			"end": 1494367200000 // Milliseconds
		}/*,
		{
			"id": 700,
			"title": "Testtokt",
			"url": "test",
			"class": "event-important",
			"start": 1485915632800, // Milliseconds
			"end": 1689995632700 // Milliseconds
		}*/],
		modal: "#events-modal",
		modal_type: "template",
		modal_title : function (event) { return event.title },
		view: "year",
		first_day: "1",
		onAfterViewLoad: function(view) {
			$('.dateLabel').text(this.getTitle());
			if (view == "year") {
				$(".cal-year-box .cal-cell").each(function(i) {
					if ($(this).find(".cal-data").data("availability") > 5) {
						$(this).addClass("full");
						$(this).find(".cal-events-icon").html('<span class="glyphicon glyphicon-remove" aria-hidden="true"></span>');
					} else if ($(this).find(".cal-data").data("availability") > 1) {
						$(this).addClass("almostFull");
						$(this).find(".cal-events-icon").html('<span class="glyphicon glyphicon-warning-sign" aria-hidden="true"></span> <span class="glyphicon glyphicon-user loggedIn" aria-hidden="true"></span>');
					} else if ($(this).find(".cal-data").data("availability") > 0) {
						$(this).addClass("mostlyAvailable");
						/*$(this).find(".cal-events-icon").html('<span class="glyphicon glyphicon-warning-sign" aria-hidden="true"></span>');*/
					}
				});
			}
		},
		views: {
			year: {
				slide_events: 1,
				enable: 1
			},
			month: {
				slide_events: 1,
				enable: 1
			},
			week: {
				enable: 0
			},
			day: {
				enable: 0
			}
		}
	}); 
	
	$('.calendar .calPreviousButton').click(function () {
		calendar.navigate('prev');
		return false;
	});
	$('.calendar .calNextButton').click(function () {
		calendar.navigate('next');
		return false;
	});
	$('.calendar .calTodayButton').click(function () {
		calendar.navigate('today');
		return false;
	});
	$('.calendar .calYearButton').click(function () {
		calendar.view('year');
		return false;
	});
	$('.calendar .calMonthButton').click(function () {
		calendar.view('month');
		return false;
	});
	$('.calendar .calWeekButton').click(function () {
		calendar.view('week');
		return false;
	});
	$('.calendar .calDayButton').click(function () {
		calendar.view('day');
		return false;
	});
	$('.loginButton').click(function () {
		$('body').toggleClass('loggedIn');
		return false;
	});
	$('.removeParticipant').click(function () {
		$(this).closest(".participant").hide();
		if ($(".participant:visible").length < 2) {
			$(".participant:visible").find(".removeParticipant").prop("disabled",true);
		} else {
			$(".participant:visible").find(".removeParticipant").prop("disabled",false);
		}
		return false;
	});
	$('.addParticipant').click(function () {
		$( ".participant:visible" ).first().clone().insertAfter($(".participant").last());
		$('.removeParticipant').click(function () {
			$(this).closest(".participant").hide();
			return false;
		});
		if ($(".participant:visible").length < 2) {
			$(".participant:visible").find(".removeParticipant").prop("disabled",true);
		} else {
			$(".participant:visible").find(".removeParticipant").prop("disabled",false);
		}
		return false;
	});
	
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
});