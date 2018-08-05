import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE","settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

from database.models import *
"""
print(Federation.objects.all())
fed = Federation("1","2")
fed.save()
"""
comp = Competition(id=1,clear_name="1")
comp.federation_id = "1"
print(comp)
#comp.save()

#print(Competition.objects.all())
#comp = Competition.objects.get(id=1)
#print(comp.federation)