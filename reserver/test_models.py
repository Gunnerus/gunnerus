from models import Event, Organization, EmailNotification, Timeevent, UserData, UserPreferences, 
								Season, Cruises, InvoiceInformation, Equipment, Document, Participant, CruiseDay, 
								WebPageText, SystemSettings, GeographicalArea, ListPrice
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, date

def create_event(name, start_time, end_time):
	x = Event(name=name, start_time=start_time, end_time=end_time)
	x.save()
	return x

def create_organization(name, is_NTNU):
	x = Organization(name=name, is_NTNU=is_NTNU)
	x.save()
	return x

def create_email_notification(event, title, message, time_before, is_active, is_muteable, date)
	x = EmailNotification(event=event, title=title, message=message, time_before=time_before, is_active=is_active, is_muteable=is_muteable)
	x.save()
	return x
	
def create_user_data(organization, user, role, phone_number, nationality, identity_document_types, is_crew, date_of_birth):
	x = UserData(organization=organization, user=user, role=role, phone_number=phone_number, nationality=nationality, identity_document_types=identity_document_types, is_crew=is_crew, date_of_birth=date_of_birth)
	x.save()
	return x
	
def create_user_preferences(user):
	x = UserPreferences(user=user)
	x.save()
	return x
	
def create_season(name, season_event, external_order_event, internal_order_event, long_education_price, long_research_price, long_boa_price, long_external_price, short_education_price, short_research_price, short_boa_price, short_external_price):
	x = Season(name=name, season_event=season_event, external_order_event=external_order_event, internal_order_event=internal_order_event, long_education_price=long_education_price, long_research_price=long_research_price, long_boa_price=long_boa_price, long_external_price=long_external_price, short_education_price=short_education_price, short_research_price=short_research_price, short_boa_price=short_boa_price, short_external_price=short_external_price)
	x.save()
	return x
	
def create_cruise(cruise_leader, organization, cruise_owner, cruise_name, cruise_description, is_submitted, terms_accepted, cruise_approved, last_edit_date, submit_date, student_participation_ok, no_student_reason, management_of_change, safety_clothing_and_equipment, safety_analysis_requirements, equipment_description, meals_on_board):
	x = Cruise(cruise_leader=cruise_leader, organization=organization, cruise_owner=cruise_owner, cruise_name=cruise_name, cruise_description=cruise_description, is_submitted=is_submitted, terms_accepted=terms_accepted, cruise_approved, cruise_approved, last_edit_date=last_edit_date, submit_date=submit_date, student_participation_ok=student_participation_ok, no_student_reason=no_student_reason, management_of_change=management_of_change, safety_clothing_and_equipment=safety_clothing_and_equipment, safety_analysis_requirements=safety_analysis_requirements, equipment_description=equipment_description, meals_on_board=meals_on_board)
	x.save()
	return x
	
def create_invoice_information(cruise, default_invoice_information_for, title, business_req_num, invoice_address, accounting_place, project_number, invoice_mark, contact_name, contact_email):
	x = InvoiceInformation(cruise=cruise, default_invoice_information_for=default_invoice_information_for, title=title, business_req_num=business_req_num, invoice_address=invoice_address, accounting_place=accounting_place, project_number=project_number, invoice_mark=invoice_mark, contact_name=contact_name, contact_email=contact_email)
	x.save()
	return x
	
def create_equipment(cruise, name, is_on_board, weight, size):
	x = Equipment(cruise=cruise, name=name, is_on_board=is_on_board, weight=weight, size=size)
	x.save()
	return x
	
def create_document(cruise, name, file):
	x = Document(cruise=cruise, name=name, file=file)
	x.save()
	return x
	
def create_participant(cruise, name, email, nationality, date_of_birth, identity_document_types):
	x = Participant(cruise=cruise, name=name, email=email, nationality=nationality, date_of_birth=date_of_birth, identity_document_types=identity_document_types)
	x.save()
	return x
	
def create_cruise_day(cruise, event, season, is_long_day, description, breakfast_count, lunch_count, dinner_count, overnight_count):
	x = CruiseDay(cruise=cruise, event=event, season=season, is_long_day=is_long_day, description=description, breakfast_count=breakfast_count, lunch_count=lunch_count, dinner_count=dinner_count, overnight_count=overnight_count)
	x.save()
	return x
	
def create_web_page_text(name, description, text):
	x = WebPageText(name=name, description=description, text=text)
	x.save()
	return x
	
def create_system_settings(work_in_progress):
	x = SystemSettings(work_in_progress=work_in_progress)
	x.save()
	return x
	
def create_geographical_area(cruise_day, name, description, latitude, longitude):
	x = GeographicalArea(cruise_day=cruise_day, name=name, description=description, latitude=latitude, longitude=longitude)
	x.save()
	return x
	
def create_list_price(invoice, name, price):
	x = ListPrice(invoice=invoice, name=name, price=price)
	x.save()
	return x
	
def create_test_models():
	#Creating organizations
	org1 = create_organization('Fakultet for klovnekunst', True)
	org2 = create_organization('Fakultet for typografi', True)
	org3 = create_organization('Statgass', False)
	org4 = create_organization('Institutt for pingvinvitenskap', True)
	org5 = create_organization('NASA', False)
	org6 = create_organization('Ila barnehage', False)
	org7 = create_organization('The Researcher\'s Night\'s watch', False)
	
	#Creating events
	ev1 = create_event('Cruise created', date(2017, 6, 30))
	ev2 = create_event('Cruise start', date(2017, 7, 28))
	ev3 = create_event('Cruise end', date(2017, 7, 30))
	ev4 = create_event('Summer 2017', datetime(2017, 4, 1), datetime(2017, 10, 1))
	ev5 = create_event('Internal order summer 2017', datetime(2017, 1, 1))
	ev6 = create_event('External order summer 2017', datetime(2017, 2, 1))
	ev7 = create_event('Winter 2017/2018', datetime(2017, 10, 1), datetime(2018, 4, 1))
	ev8 = create_event('Internal order winter 2017/2018', datetime(2017, 7, 1))
	ev9 = create_event('External order winter 2017/2018', datetime(2017, 8, 1))
	ev10 = create_event('Cruise day 1', date(2017, 11, 3))
	ev11 = create_event('Cruise day 2', date(2017, 11, 4))
	ev12 = create_event('Cruise day 3', date(2017, 11, 5))
	ev13 = create_event('Cruise day 4', date(2017, 11, 6))
	
	#Creating email notifications
	em_no1 = create_email_notification(ev2, 'Cruise in 4 weeks', 'A cruise you are participating in is in 4 weeks', timedelta(days=28), True, False)
	em_no2 = create_email_notification(ev2, 'Cruise in 3 weeks', 'A cruise you are participating in is in 3 weeks', timedelta(days=21), True, False)
	em_no3 = create_email_notification(ev2, 'Cruise in 2 weeks', 'A cruise you are participating in is in 2 weeks', timedelta(days=14), True, False)
	em_no4 = create_email_notification(ev2, 'Cruise in 1 week', 'A cruise you are participating in is in 1 week', timedelta(days=7), True, False)
	em_no5 = create_email_notification(ev2, 'Cruise missing information', 'A cruise departing in 4 weeks needs more information', timedelta(days=28), True, False)
	em_no6 = create_email_notification(ev2, 'Cruise missing information', 'A cruise departing in 3 weeks needs more information', timedelta(days=21), True, False)
	em_no7 = create_email_notification(ev1, 'New cruise created', 'You have been set as an owner of a cruise', timedelta(days=0), True, False)
	
	#Creating user data
	u1 = create_user_data(org7, User.objects.create_user(username='jon_snow', email='jon.snow@nightswatch.net', password='knows some things'), 'internal', '0000', 'The North', 'Driver\'s license', False, date(281, 2, 15))
	u2 = create_user_data(org1, User.objects.create_user(username='hot_pie', email='hawtpie@orphan.org', password='winterhell'), 'external', '1111', 'The Crownlands', 'Passport, looks supsiciously like a pice of bread', False, date(287, 6, 3))
	u3 = create_user_data(org5, User.objects.create_user(username='jorah_da_explorah', email='jorah.mormont@mereen.com', password='khaleeeeeeesi'), 'not_approved', '1234', 'The North', 'Driver\'s license', True, date(269, 8, 24))
	u4 = create_user_data(org6, User.objects.create_user(username='arry', email='noone@faceless.se', password='the hound merryn trant queen cersei joffrey the tickler the mountain'), 'internal', '5432', 'The North', '5 fake passports with different identities', True, date(288, 5, 5))
	u5 = create_user_data(org4, User.objects.create_user(username='bran_not_the_builder', email='brandon.stark@winterfell.gov', password='rip legs now i fly'), 'internal', '7345', 'The North', 'Visa', False, date(290, 1, 1))
	#u6 = create_user_data(org1, User.objects.create_user(username='jon_snow', email='jon.snow@nightswatch.net', password='kissed by fire'), 'not_approved', '0000', 'The North', 'Driver\'s license', False, date(281, 2, 15))
	#u7 = create_user_data(org1, User.objects.create_user(username='jon_snow', email='jon.snow@nightswatch.net', password='kissed by fire'), 'not_approved', '0000', 'The North', 'Driver\'s license', False, date(281, 2, 15))
	
	#Creating user preferences
	u1 = create_user_preferences(u1)
	u2 = create_user_preferences(u2)
	u3 = create_user_preferences(u3)
	u4 = create_user_preferences(u4)
	u5 = create_user_preferences(u5)
	
	#Creating seasons
	s1 = create_season('Summer 2017', ev4, ev5, ev6, 2000, 2400, 2600, 4000, 1000, 1200, 1300, 2000)
	s2 = create_season('Winter 2017/2018', ev7, ev8, ev9, 2200, 2600, 2800, 4200, 1100, 1300, 1400, 2100)
	
	#Creating cruises
	cruise1 = create_cruise(cruise_leader=u1, organization=org7, cruise_name='Save wildlings at Hardhome', 'We\'re going to Hardhome to pick up some wildlings before the White Walkers get them and add them to their army of the dead', last_edit_date=datetime.now(), None, True, equipment_description='Swords, food, blankets, etc.')
	
	#Creating invoice information
	
	
	#Creating equipment
	equip1 = create_equipment(cruise1, 'Dragon glass/obsidian, 50 pieces', False)
	
	#Creating documents
	
	
	#Creating participants
	part1 = create_participant(cruise1, 'Tormund "Horn-blower", "Husband to bears", "Father of hosts" Giantsbane', 'tormund.giantsbane@freefolk.net', 'Beyond the Wall', None, 'Carries ancient, gilded horn')
	part2 = create_participant(cruise1, 'Eddison "Dolororus Edd" Tollett', 'edd.tollett@nightswatch.net', 'The Vale', None, '')
	
	#Creating cruise days
	c_day1 = create_cruise_day(cruise1, ev10, s2, True, 'Setting out from East Watch by the Sea', 200, 200, 200, 200)
	c_day2 = create_cruise_day(cruise1, ev11, s2, True, 'Arriving at Hardhome, begin putting wildlings on ships', 200, 200, 10000, 10000)
	c_day3 = create_cruise_day(cruise1, ev12, s2, True, 'Finish up at Hardhome and set sail again', 11000, 13000, 15000, 15000)
	c_day4 = create_cruise_day(cruise1, ev13, s2, True, 'Arrive at East Watch by the Sea', 15000, 5000, 100, 0)
	
	#Creating web page text
	
	
	#Creating system settings
	
	
	#Creating geographical areas
	
	
	#Creating list prices
	