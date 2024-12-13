import unittest
from unittest.mock import patch, mock_open
import zlib
from visualizator import ConfigTranslator
from visualizator import (
    read_git_object,
    parse_commit_object,
    get_files_from_tree,
    save_mermaid_to_png,
    get_commits,
    parse_commits,
    generate_mermaid,
)


class TestGitFunctions(unittest.TestCase):

    def test_read_git_object(self):
        """Тест на чтение и декомпрессию объекта Git."""
        fake_data = zlib.compress(b"fake_git_object_content")

        with patch("builtins.open", mock_open(read_data=fake_data)):
            with patch("os.path.exists", return_value=True):
                result = read_git_object("/fake/repo", "abcd")
                self.assertEqual(result, b"fake_git_object_content")

    def test_save_mermaid_to_png(self):
        """Тест сохранения графа Mermaid в PNG с использованием subprocess."""
        with patch("subprocess.run") as mock_run:
            save_mermaid_to_png("graph_code", "/fake/output.png", "/path/to/mmdc")
            mock_run.assert_called_with(
                ["/path/to/mmdc", "-i", "temp.mmd", "-o", "/fake/output.png"],
                check=True
            )

    def test_parse_commits(self):
        """Тест на создание графа из коммитов."""
        commits = [
            {"hash": "abcd", "files": ["file1.txt", "file2.txt"]},
            {"hash": "efgh", "files": ["file2.txt", "file3.txt"]},
        ]
        result = parse_commits(commits)
        self.assertIn("file1.txt", result)
        self.assertIn("file2.txt", result)
        self.assertIn("file3.txt", result)
        self.assertEqual(len(result), 3)


if __name__ == "__main__":
    unittest.main()
