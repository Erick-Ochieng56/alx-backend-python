#!/usr/bin/env python3
"""Unit tests for GithubOrgClient class."""
import unittest
from parameterized import parameterized
from unittest.mock import patch, Mock
from client import GithubOrgClient


class TestGithubOrgClient(unittest.TestCase):
    """Unit tests for GithubOrgClient class."""
    
    @parameterized.expand([
        ("google",),
        ("abc",),
    ])
    @patch('utils.get_json')
    def test_org(self, org_name: str, mock_get_json: Mock) -> None:
        """Test GithubOrgClient.org returns correct value."""
        test_payload = {"repos_url": f"https://api.github.com/orgs/{org_name}/repos"}
        mock_get_json.return_value = test_payload
        
        client = GithubOrgClient(org_name)
        result = client.org
        
        mock_get_json.assert_called_once_with(f"https://api.github.com/orgs/{org_name}")
        self.assertEqual(result, test_payload)


if __name__ == '__main__':
    unittest.main()
