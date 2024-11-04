from http import HTTPStatus

from django.test import Client, TestCase
from django.urls import reverse


class HealthCheckTests(TestCase):
    def setUp(self):
        """Set up test client."""
        self.client = Client()

    def test_health_check_endpoint(self):
        """Test that the application is up and running."""
        response = self.client.get(reverse('health'))

        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertEqual(
            response.json(),
            {'status': 'healthy'},
        )

    def test_database_connection(self):
        """Test that the database connection is working."""
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            row = cursor.fetchone()
            self.assertEqual(row[0], 1)

    def test_admin_page_loads(self):
        """Test that Django admin interface is accessible."""
        response = self.client.get('/admin/login/')
        self.assertEqual(response.status_code, HTTPStatus.OK)
