from models import Event, Organization, EmailNotification, TimeInterval, UserData, UserPreferences, 
								Season, Cruises, InvoiceInformation, Equipment, Document, Participant, CruiseDay, 
								WebPageText, SystemSettings, GeographicalArea, ListPrice
from django.db import models
from django.utils import timezone
from datetime import timedelta

def create_events(models.Model, name):
	x = Event(name=name)
	x.save()
	return x

def create_organization(models.Model, name, is_NTNU):
	x = Organization(name=name, is_NTNU=is_NTNU)
	x.save()
	return x

def create_email_notification(models.Model, event, title, message, time_before, is_active, is_muteable, date)
	x = EmailNotification(event=event, title=title, message=message, time_before=time_before, is_active=is_active, is_muteable=is_muteable)
	x.save()
	return x
	
def create_time_interval(models.Model, event, name, start_time, end_time):
	x = TimeInterval(event=event, name=name, start_time=start_time, end_time=end_time)
	x.save()
	return x
	
def create_user_Data(models.Model, organization, user, role, phone_number, nationality, identity_document_types, is_crew, date_of_birth):
	x = UserData(organization=organization, user=user, role=role, phone_number=phone_number, nationality=nationality, identity_document_types=identity_document_types, is_crew=is_crew, date_of_birth=date_of_birth)
	x.save()
	return x
	
def create_user_preferences(models.Model, user):
	x = UserPreferences(user=user)
	x.save()
	return x
	
def create_season(models.Model, name, season_interval, external_order_interval, internal_order_interval, long_education_price, long_research_price, long_boa_price, long_external_price, short_education_price, short_research_price, short_boa_price, short_external_price):
	x = Season(name=name, season_interval=season_interval, external_order_interval=external_order_interval, internal_order_interval=internal_order_interval, long_education_price=long_education_price, long_research_price=long_research_price, long_boa_price=long_boa_price, long_external_price=long_external_price, short_education_price=short_education_price, short_research_price=short_research_price, short_boa_price=short_boa_price, short_external_price=short_external_price)
	x.save()
	return x
	
def create_cruise(models.Model, cruise_leader, organization, cruise_owner, cruise_name, cruise_description, is_submitted, terms_accepted, cruise_approved, last_edit_date, submit_date, student_participation_ok, no_student_reason, management_of_change, safety_clothing_and_equipment, safety_analysis_requirements, equipment_description, meals_on_board):
	x = Cruise(cruise_leader=cruise_leader, organization=organization, cruise_owner=cruise_owner, cruise_name=cruise_name, cruise_description=cruise_description, is_submitted=is_submitted, terms_accepted=terms_accepted, cruise_approved, cruise_approved, last_edit_date=last_edit_date, submit_date=submit_date, student_participation_ok=student_participation_ok, no_student_reason=no_student_reason, management_of_change=management_of_change, safety_clothing_and_equipment=safety_clothing_and_equipment, safety_analysis_requirements=safety_analysis_requirements, equipment_description=equipment_description, meals_on_board=meals_on_board)
	x.save()
	return x
	
def create_invoice_information(models.Model, cruise, default_invoice_information_for, title, business_req_num, invoice_address, accounting_place, project_number, invoice_mark, contact_name, contact_email):
	x = InvoiceInformation(cruise=cruise, default_invoice_information_for=default_invoice_information_for, title=title, business_req_num=business_req_num, invoice_address=invoice_address, accounting_place=accounting_place, project_number=project_number, invoice_mark=invoice_mark, contact_name=contact_name, contact_email=contact_email)
	x.save()
	return x
	
def create_equipment(models.Model, cruise, name, is_on_board, weight, size):
	x = Equipment(cruise=cruise, name=name, is_on_board=is_on_board, weight=weight, size=size)
	x.save()
	return x
	
def create_document(models.Model, cruise, name, file):
	x = Document(cruise=cruise, name=name, file=file)
	x.save()
	return x
	
def create_participant(models.Model, cruise, name, email, nationality, date_of_birth, identity_document_types):
	x = Participant(cruise=cruise, name=name, email=email, nationality=nationality, date_of_birth=date_of_birth, identity_document_types=identity_document_types)
	x.save()
	return x
	
def create_cruise_day(models.Model, cruise, event, season, is_long_day, description, breakfast_count, lunch_count, dinner_count, overnight_count):
	x = CruiseDay(cruise=cruise, event=event, season=season, is_long_day=is_long_day, description=description, breakfast_count=breakfast_count, lunch_count=lunch_count, dinner_count=dinner_count, overnight_count=overnight_count)
	x.save()
	return x
	
def create_web_page_text(models.Model, name, description, text):
	x = WebPageText(name=name, description=description, text=text)
	x.save()
	return x
	
def create_system_settings(models.Model, work_in_progress):
	x = SystemSettings(work_in_progress=work_in_progress)
	x.save()
	return x
	
def create_geographical_area(models.Model, cruise_day, name, description, latitude, longitude):
	x = GeographicalArea(cruise_day=cruise_day, name=name, description=description, latitude=latitude, longitude=longitude)
	x.save()
	return x
	
def create_list_price(models.Model, invoice, name, price):
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
	
	#Creating events
	ev1 = create_event('Cruise departure')
	ev2 = create_event('Cruise created')
	
	#Creating email notifications with events
	em_no1 = create_email_notification(ev1, 'Cruise in 4 weeks', 'A cruise you are participating in is in 4 weeks', timedelta(days=28), True, False)
	em_no2 = create_email_notification(ev1, 'Cruise in 3 weeks', 'A cruise you are participating in is in 3 weeks', timedelta(days=21), True, False)
	em_no3 = create_email_notification(ev1, 'Cruise in 2 weeks', 'A cruise you are participating in is in 2 weeks', timedelta(days=14), True, False)
	em_no4 = create_email_notification(ev1, 'Cruise in 1 week', 'A cruise you are participating in is in 1 week', timedelta(days=7), True, False)
	em_no5 = create_email_notification(ev1, 'Cruise missing information', 'A cruise departing in 4 weeks needs more information', timedelta(days=28), True, False)
	em_no6 = create_email_notification(ev1, 'Cruise missing information', 'A cruise departing in 3 weeks needs more information', timedelta(days=21), True, False)
	em_no7 = create_email_notification(ev2, 'New cruise created', 'You have been set as an owner of a cruise', timedelta(days=0), True, False)