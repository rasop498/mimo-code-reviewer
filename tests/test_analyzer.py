"""Tests for diff parser and analyzer."""

import unittest
from reviewer.analyzer import (
    parse_diff,
    detect_language,
    build_review_prompt,
    build_summary_prompt,
    DiffHunk,
)

SAMPLE_DIFF = """diff --git a/app/server.py b/app/server.py
index abc123..def456 100644
--- a/app/server.py
+++ b/app/server.py
@@ -10,6 +10,8 @@ from flask import Flask
 
 app = Flask(__name__)
 
+SECRET_KEY = "hardcoded_secret_123"
+
 @app.route("/")
 def index():
-    return "Hello"
+    return render_template("index.html")
diff --git a/app/utils.py b/app/utils.py
new file mode 100644
--- /dev/null
+++ b/app/utils.py
@@ -0,0 +1,15 @@
+import os
+import subprocess
+
+def run_command(cmd):
+    result = subprocess.call(cmd, shell=True)
+    return result
+
+def get_db_password():
+    return os.getenv("DB_PASS", "admin123")
+
+def process_items(items):
+    output = []
+    for i in items:
+        output.append(i * 2)
+    return output
"""

MULTI_LANG_DIFF = """diff --git a/src/index.ts b/src/index.ts
index 111..222 100644
--- a/src/index.ts
+++ b/src/index.ts
@@ -1,3 +1,5 @@
 const app = express();
+const password = "admin";
+app.use(cors({ origin: "*" }));
 app.listen(3000);
diff --git a/main.go b/main.go
index 333..444 100644
--- a/main.go
+++ b/main.go
@@ -5,4 +5,6 @@ func main() {
     fmt.Println("Hello")
+    db, _ := sql.Open("postgres", connStr)
+    defer db.Close()
 }
"""


class TestDetectLanguage(unittest.TestCase):
    def test_python(self):
        self.assertEqual(detect_language("app/server.py"), "python")

    def test_typescript(self):
        self.assertEqual(detect_language("src/index.ts"), "typescript")

    def test_javascript(self):
        self.assertEqual(detect_language("lib/utils.js"), "javascript")

    def test_go(self):
        self.assertEqual(detect_language("main.go"), "go")

    def test_rust(self):
        self.assertEqual(detect_language("src/main.rs"), "rust")

    def test_java(self):
        self.assertEqual(detect_language("App.java"), "java")

    def test_yaml(self):
        self.assertEqual(detect_language("config.yml"), "yaml")

    def test_unknown(self):
        self.assertEqual(detect_language("Makefile"), "text")


class TestParseDiff(unittest.TestCase):
    def test_parse_two_files(self):
        files = parse_diff(SAMPLE_DIFF)
        self.assertEqual(len(files), 2)

    def test_file_paths(self):
        files = parse_diff(SAMPLE_DIFF)
        self.assertEqual(files[0].file_path, "app/server.py")
        self.assertEqual(files[1].file_path, "app/utils.py")

    def test_language_detection(self):
        files = parse_diff(SAMPLE_DIFF)
        self.assertEqual(files[0].language, "python")
        self.assertEqual(files[1].language, "python")

    def test_additions_count(self):
        files = parse_diff(SAMPLE_DIFF)
        self.assertEqual(files[0].additions, 3)  # SECRET_KEY, empty line, render_template
        self.assertEqual(files[1].additions, 15)

    def test_deletions_count(self):
        files = parse_diff(SAMPLE_DIFF)
        self.assertEqual(files[0].deletions, 1)  # return "Hello"
        self.assertEqual(files[1].deletions, 0)

    def test_hunks_created(self):
        files = parse_diff(SAMPLE_DIFF)
        self.assertEqual(len(files[0].hunks), 1)
        self.assertEqual(len(files[1].hunks), 1)

    def test_hunk_line_numbers(self):
        files = parse_diff(SAMPLE_DIFF)
        hunk = files[0].hunks[0]
        self.assertEqual(hunk.old_start, 10)
        self.assertEqual(hunk.new_start, 10)

    def test_hunk_added_lines(self):
        files = parse_diff(SAMPLE_DIFF)
        added = files[0].hunks[0].added_lines
        self.assertTrue(any("SECRET_KEY" in l for l in added))

    def test_hunk_removed_lines(self):
        files = parse_diff(SAMPLE_DIFF)
        removed = files[0].hunks[0].removed_lines
        self.assertTrue(any("Hello" in l for l in removed))

    def test_multi_language(self):
        files = parse_diff(MULTI_LANG_DIFF)
        self.assertEqual(len(files), 2)
        self.assertEqual(files[0].language, "typescript")
        self.assertEqual(files[1].language, "go")

    def test_empty_diff(self):
        files = parse_diff("")
        self.assertEqual(len(files), 0)


class TestBuildPrompt(unittest.TestCase):
    def test_review_prompt_contains_file(self):
        files = parse_diff(SAMPLE_DIFF)
        prompt = build_review_prompt(files, "Fix login")
        self.assertIn("app/server.py", prompt)
        self.assertIn("Fix login", prompt)

    def test_review_prompt_contains_guidelines(self):
        files = parse_diff(SAMPLE_DIFF)
        prompt = build_review_prompt(files)
        self.assertIn("security", prompt.lower())
        self.assertIn("bugs", prompt.lower())

    def test_summary_prompt(self):
        files = parse_diff(SAMPLE_DIFF)
        prompt = build_summary_prompt(files, "Add utils")
        self.assertIn("app/server.py", prompt)
        self.assertIn("Add utils", prompt)

    def test_prompt_includes_code(self):
        files = parse_diff(SAMPLE_DIFF)
        prompt = build_review_prompt(files)
        self.assertIn("SECRET_KEY", prompt)
        self.assertIn("subprocess", prompt)


class TestDiffHunk(unittest.TestCase):
    def test_added_lines_property(self):
        hunk = DiffHunk(
            file_path="test.py",
            old_start=1, old_count=3,
            new_start=1, new_count=5,
            content="+new line\n context\n-old line\n+another new",
        )
        self.assertEqual(len(hunk.added_lines), 2)

    def test_removed_lines_property(self):
        hunk = DiffHunk(
            file_path="test.py",
            old_start=1, old_count=3,
            new_start=1, new_count=5,
            content="+new line\n context\n-old line\n+another new",
        )
        self.assertEqual(len(hunk.removed_lines), 1)


if __name__ == "__main__":
    unittest.main()
