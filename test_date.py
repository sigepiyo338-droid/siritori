import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'siritori_project.settings')
django.setup()

from django.template import Template, Context
from django.contrib.auth.models import User

u = User.objects.first()
t = Template('''{{
u.date_joined|date:"Y年m月d日 H:i" }}''')
c = Context({'u': u})
print("RENDERED:", repr(t.render(c)))
