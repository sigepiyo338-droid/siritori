import os
import sys
import django
from django.test import Client

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'siritori_project.settings')
django.setup()

c = Client(SERVER_NAME='localhost')
print("Testing /twotakukun/ ...")
try:
    response = c.get('/twotakukun/')
    print('Status code:', response.status_code)
    # print('Content:', response.content.decode('utf-8')[:200])
except Exception as e:
    print('Error on /twotakukun/:', e)

print("\nTesting /twotakukun/api/questions ...")
try:
    response = c.get('/twotakukun/api/questions')
    print('Status code:', response.status_code)
    print('Content:', response.content.decode('utf-8'))
except Exception as e:
    print('Error on /twotakukun/api/questions:', e)

print("\nTesting /twotakukun/api/personalities ...")
try:
    response = c.get('/twotakukun/api/personalities')
    print('Status code:', response.status_code)
    print('Content:', response.content.decode('utf-8'))
except Exception as e:
    print('Error on /twotakukun/api/personalities:', e)
