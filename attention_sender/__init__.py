from datetime import datetime, timedelta


TIME_TRIGGER = datetime.strptime('23:00', '%H:%M').time()
MESSAGE_LIFETIME = timedelta(hours=48)
