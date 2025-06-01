#!/usr/bin/env python3
"""Unit tests for GithubOrgClient class."""
import unittest
from parameterized import parameterized
from unittest.mock import patch, Mock, PropertyMock
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

    def test_public_repos_url(self) -> None:
        """Test GithubOrgClient._public_repos_url returns expected value."""
        test_payload = {"repos_url": "https://api.github.com/orgs/test/repos"}
        with patch('client.GithubOrgClient.org', new_callable=PropertyMock) as mock_org:
            mock_org.return_value = test_payload
            client = GithubOrgClient("test")
            result = client._public_repos_url
            self.assertEqual(result, test_payload["repos_url"])

    @patch('utils.get_json')
    def test_public_repos(self, mock_get_json: Mock) -> None:
        """Test GithubOrgClient.public_repos returns expected repos."""
        test_payload = [
            {"name": "repo1", "license": {"key": "apache-2.0"}},
            {"name": "repo2", "license": {"key": "mit"}},
        ]
        mock_get_json.return_value = test_payload
        
        with patch('client.GithubOrgClient._public_repos_url', new_callable=PropertyMock) as mock_url:
            mock_url.return_value = "https://api.github.com/orgs/test/repos"
            client = GithubOrgClient("test")
            
            result = client.public_repos()
            self.assertEqual(result, ["repo1", "repo2"])
            
            mock_url.assert_called_once()
            mock_get_json.assert_called_once_with("https://api.github.com/orgs/test/repos")


if __name__ == '__main__':
    unittest.main()
