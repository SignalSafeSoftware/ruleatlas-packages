"""Tests for ruleatlas-discovery."""

from __future__ import annotations

from ruleatlas_discovery import (
    BucketHint,
    CommentStyle,
    FileKind,
    FileTypeMapping,
    FileTypeResolver,
    aggregate_line_counts_by_file_type,
    apply_discovery_scope,
    build_directory_tree,
    classify_file_type,
    matches_any_glob,
    should_include_path,
)
from ruleatlas_discovery.constants import NO_EXTENSION
from ruleatlas_discovery.models import DiscoveryFile, DiscoveryScope


def test_package_imports() -> None:
    assert classify_file_type("src/main.py").language == "Python"


def test_file_type_classification() -> None:
    resolved = classify_file_type("infra/Dockerfile")
    assert resolved.language == "Dockerfile"
    assert resolved.file_kind == "build"


def test_custom_mapping_precedence() -> None:
    custom = FileTypeMapping(
        pattern=".custom-api-test",
        match_type="extension",
        language="Phobos API",
        language_key="config",
        display_type=".phobos-api",
        file_kind="config",
        default_bucket_hint="config",
        comment_style="hash",
        source="custom",
    )
    resolver = FileTypeResolver([custom])
    resolved = resolver.resolve("vendor/foo.custom-api-test")
    assert resolved.language == "Phobos API"
    assert resolved.mapping_source == "custom"


def test_glob_mapping_consolidation() -> None:
    resolver = FileTypeResolver()
    yml = classify_file_type("config/app.yml", resolver)
    yaml = classify_file_type("config/app.yaml", resolver)
    assert yml.language == yaml.language == "YAML"
    assert yml.extension == yaml.extension == ".yaml"

    compose_yml = classify_file_type("docker-compose.yml", resolver)
    compose_yaml = classify_file_type("docker-compose.yaml", resolver)
    assert compose_yml.language == compose_yaml.language == "Docker Compose"
    assert compose_yml.display_type == "Docker Compose"
    assert compose_yml.file_type == compose_yaml.file_type == "Docker Compose"
    assert yml.file_type == yaml.file_type == "YAML"
    assert compose_yml.file_type != yml.file_type

    license_us = classify_file_type("LICENSE", resolver)
    license_uk = classify_file_type("LICENCE", resolver)
    license_lower = classify_file_type("license", resolver)
    assert license_us.language == license_uk.language == license_lower.language == "License"

    gnu = classify_file_type("GNUMakefile", resolver)
    make = classify_file_type("Makefile", resolver)
    assert gnu.language == make.language == "Makefile"
    assert gnu.file_kind == make.file_kind == "build"


def test_eslint_config_filename_mapping() -> None:
    resolver = FileTypeResolver()
    for path in (
        "eslint.config.ts",
        "apps/web/eslint.config.ts",
    ):
        resolved = classify_file_type(path, resolver)
        assert resolved.language == "ESLint", path
        assert resolved.display_type == "ESLint config", path
        assert resolved.file_kind == FileKind.CONFIG, path


def test_env_and_dockerfile_glob_mappings() -> None:
    resolver = FileTypeResolver()
    for path in (".env", ".env.test", ".env.dist", ".env.local", "config/.env", ".env.localstack"):
        resolved = classify_file_type(path, resolver)
        assert resolved.display_type == "Environment variables", path
        assert resolved.file_type == "Environment variables", path
        assert resolved.file_kind == FileKind.CONFIG, path
        assert resolved.extension == NO_EXTENSION, path

    for path in (
        "Dockerfile",
        "Dockerfile.dev",
        "Dockerfile.prod",
        "Dockerfile.node",
        "Dockerfile.phobos-api",
        "infra/Dockerfile.ci",
    ):
        resolved = classify_file_type(path, resolver)
        assert resolved.display_type == "Dockerfile", path
        assert resolved.file_type == "Dockerfile", path
        assert resolved.file_kind == FileKind.BUILD, path
        assert resolved.extension == NO_EXTENSION, path

    env = classify_file_type(".env.test", resolver)
    docker = classify_file_type("Dockerfile.node", resolver)
    assert env.file_type != docker.file_type

    assert classify_file_type(".environment", resolver).display_type != "Environment variables"
    assert classify_file_type("Dockerfiles", resolver).display_type != "Dockerfile"


def test_sonar_project_properties_filename_mapping() -> None:
    resolver = FileTypeResolver()
    for path in ("sonar-project.properties", "backend/administration/sonar-project.properties"):
        resolved = classify_file_type(path, resolver)
        assert resolved.display_type == "Sonar project properties", path
        assert resolved.file_type == "Sonar project properties", path
        assert resolved.mapping_pattern == "sonar-project.properties", path

    assert classify_file_type("gradle.properties", resolver).display_type == "Java properties"


def test_tsconfig_glob_mapping() -> None:
    resolver = FileTypeResolver()
    for path in (
        "tsconfig.json",
        "tsconfig.node.json",
        "apps/web/tsconfig.json",
        "apps/web/tsconfig.app.json",
    ):
        resolved = classify_file_type(path, resolver)
        assert resolved.display_type == "TypeScript config", path
        assert resolved.file_type == "TypeScript config", path
        assert resolved.file_kind == FileKind.CONFIG, path
        assert resolved.mapping_pattern == "tsconfig*(.*).json", path

    json_data = classify_file_type("data.json", resolver)
    tsconfig = classify_file_type("tsconfig.json", resolver)
    assert json_data.file_type != tsconfig.file_type

    assert classify_file_type("package.json", resolver).display_type == "npm package manifest"
    assert classify_file_type("jsconfig.json", resolver).display_type != "TypeScript config"


def test_typescript_test_glob_does_not_match_regular_ts() -> None:
    resolver = FileTypeResolver()
    api = classify_file_type("frontend/workspace/src/domains/training/api.ts", resolver)
    unit_test = classify_file_type("frontend/workspace/src/foo.test.ts", resolver)
    assert api.display_type == "TypeScript source"
    assert api.file_type == ".ts"
    assert unit_test.display_type == "TypeScript unit test"
    assert unit_test.file_type == "TypeScript unit test"
    assert api.file_type != unit_test.file_type


def test_react_test_tsx_glob_mapping() -> None:
    resolver = FileTypeResolver()
    for path in (
        "src/App.test.tsx",
        "components/Button.test.tsx",
    ):
        resolved = classify_file_type(path, resolver)
        assert resolved.language == "TSX", path
        assert resolved.display_type == "React test", path
        assert resolved.file_type == "React test", path
        assert resolved.file_kind == FileKind.TEST, path

    assert classify_file_type("src/App.tsx", resolver).display_type == "React TSX"


def test_vite_config_filename_mapping() -> None:
    resolver = FileTypeResolver()
    for path in (
        "vite.config.ts",
        "DeliveryPlus/frontend/workspace/vite.config.ts",
    ):
        resolved = classify_file_type(path, resolver)
        assert resolved.language == "Vite", path
        assert resolved.display_type == "Vite config", path
        assert resolved.file_kind == FileKind.CONFIG, path
        assert resolved.mapping_pattern == "vite.config.ts", path


def test_python_test_glob_mapping() -> None:
    resolver = FileTypeResolver()
    for path in (
        "test_administration_coverage_gaps.py",
        "apps/api/tests/test_common.py",
        "test_working.py",
    ):
        resolved = classify_file_type(path, resolver)
        assert resolved.language == "Python", path
        assert resolved.display_type == "Python test", path
        assert resolved.file_type == "Python test", path
        assert resolved.file_kind == FileKind.TEST, path

    assert classify_file_type("conftest.py", resolver).display_type == "Python source"
    assert classify_file_type("permissions.py", resolver).display_type == "Python source"


def test_csharp_php_and_tsx_language_classification() -> None:
    resolver = FileTypeResolver()
    cases = {
        "src/Services/OrderService.cs": ("C#", "csharp", FileKind.CODE, ".cs"),
        "OrderServiceTests.cs": ("C#", "csharp", FileKind.TEST, ".cs"),
        "Services/OrderService.Tests.cs": ("C#", "csharp", FileKind.TEST, ".cs"),
        "app/Http/Controllers/UserController.php": ("PHP", "php", FileKind.CODE, ".php"),
        "tests/Unit/UserTest.php": ("PHP", "php", FileKind.TEST, ".php"),
        "src/App.tsx": ("TSX", "tsx", FileKind.CODE, ".tsx"),
        "src/App.test.tsx": ("TSX", "tsx", FileKind.TEST, ".tsx"),
        "src/App.spec.tsx": ("TSX", "tsx", FileKind.TEST, ".tsx"),
        "src/main.ts": ("TypeScript", "typescript", FileKind.CODE, ".ts"),
        "src/main.py": ("Python", "python", FileKind.CODE, ".py"),
        "features/login.feature": ("Gherkin", "gherkin", FileKind.TEST, ".feature"),
    }
    for path, (language, language_key, file_kind, extension) in cases.items():
        resolved = classify_file_type(path, resolver)
        assert resolved.language == language, path
        assert resolved.language_key == language_key, path
        assert resolved.file_kind == file_kind, path
        assert resolved.extension == extension, path


def test_path_role_overlay_does_not_overwrite_language() -> None:
    resolver = FileTypeResolver()
    generated_cs = classify_file_type("src/generated/OrderService.cs", resolver)
    assert generated_cs.language == "C#"
    assert generated_cs.language_key == "csharp"
    assert generated_cs.extension == ".cs"
    assert generated_cs.file_kind == FileKind.GENERATED
    assert generated_cs.default_bucket_hint == BucketHint.GENERATED_VENDOR
    assert generated_cs.display_type == "Generated output"
    assert generated_cs.comment_style == CommentStyle.SLASH

    generated_php = classify_file_type("generated/src/User.php", resolver)
    assert generated_php.language == "PHP"
    assert generated_php.language_key == "php"
    assert generated_php.file_kind == FileKind.GENERATED

    generated_tsx = classify_file_type("build/generated/Widget.tsx", resolver)
    assert generated_tsx.language == "TSX"
    assert generated_tsx.language_key == "tsx"
    assert generated_tsx.file_kind == FileKind.GENERATED

    # Role detection must not rewrite a non-generated production language match.
    production = classify_file_type("src/Services/OrderService.cs", resolver)
    assert production.language == "C#"
    assert production.file_kind == FileKind.CODE
    assert production.default_bucket_hint == BucketHint.PRODUCTION


def test_line_count_aggregation() -> None:
    files = [
        DiscoveryFile(path="a.py", code_lines=10, comment_lines=2, blank_lines=1, line_count=13),
        DiscoveryFile(path="b.py", code_lines=5, comment_lines=1, blank_lines=0, line_count=6),
    ]
    rows = aggregate_line_counts_by_file_type(files)
    assert rows
    assert sum(row.code_lines for row in rows) == 15


def test_directory_tree() -> None:
    files = [
        DiscoveryFile(path="src/a.py", display_path="src/a.py", line_count=10, code_lines=8),
        DiscoveryFile(path="src/lib/b.py", display_path="src/lib/b.py", line_count=5, code_lines=4),
    ]
    tree = build_directory_tree(files)
    assert len(tree) == 1
    assert tree[0].kind == "folder"
    assert tree[0].files_count == 2
    lib_folder = next(child for child in tree[0].children if child.name == "lib")
    assert lib_folder.kind == "folder"
    assert lib_folder.folders_count == 0
    nested_file = lib_folder.children[0]
    assert nested_file.kind == "file"
    assert nested_file.name == "b.py"
    assert tree[0].folders_count == 1


def test_directory_tree_aggregates_token_count() -> None:
    files = [
        DiscoveryFile(
            path="src/a.py",
            display_path="src/a.py",
            size_bytes=400,
            token_count=42,
            line_count=10,
            code_lines=8,
        ),
        DiscoveryFile(
            path="src/lib/b.py",
            display_path="src/lib/b.py",
            size_bytes=100,
            token_count=None,
            line_count=5,
            code_lines=4,
        ),
    ]
    tree = build_directory_tree(files)
    assert tree[0].token_count == 67  # 42 + ceil(100 / 4)
    lib_folder = next(child for child in tree[0].children if child.name == "lib")
    assert lib_folder.token_count == 25
    assert lib_folder.children[0].token_count == 25


def test_directory_tree_root_file() -> None:
    tree = build_directory_tree([DiscoveryFile(path="README.md", display_path="README.md", line_count=3)])
    assert len(tree) == 1
    assert tree[0].kind == "file"
    assert tree[0].name == "README.md"


def test_glob_matching() -> None:
    assert matches_any_glob("vendor/foo/bar.json", ["**/bar.json"])
    assert not should_include_path("vendor/foo.py", [], ["**/*.py"])
    scoped = apply_discovery_scope(
        [DiscoveryFile(path="keep.py"), DiscoveryFile(path="skip.log")],
        DiscoveryScope(include_globs=["**/*.py"], exclude_globs=[]),
    )
    assert [row.path for row in scoped] == ["keep.py"]


def test_bare_extension_glob_matches_nested_paths() -> None:
    # RA-02-002: fnmatch '*' spans '/', so a bare '*.json' matches nested files too (not basename-only).
    assert matches_any_glob("a/b/c.json", ["*.json"])
    assert matches_any_glob("top.json", ["*.json"])
    assert not should_include_path("vendor/foo.json", [], ["*.json"])
