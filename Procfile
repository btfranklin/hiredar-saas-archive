web: gunicorn hiredar.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 4
worker:  python manage.py qcluster
release: npm run build:css && python manage.py migrate && python manage.py collectstatic --noinput