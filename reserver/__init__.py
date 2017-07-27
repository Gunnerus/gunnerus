from apscheduler.schedulers.background import BackgroundScheduler

# Scheduler which executes methods at set times in the future, such as sending emails about upcoming cruises to the leader, owners and participants on certain deadlines
scheduler = BackgroundScheduler()
scheduler.start()