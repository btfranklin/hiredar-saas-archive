web: gunicorn hiredar.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 4
release: python manage.py migrate && python manage.py collectstatic --noinput