.PHONY: docs build bump-minor bump-major publish publish-test

build:
	rm -rf dist/
	uv build

bump-minor:
	uv version --bump minor
	git add . && git commit
	@read -p "Push to remote? [y/N] " confirm && [ "$$confirm" = "y" ] && git push || echo "Skipped push."

bump-major:
	uv version --bump major
	git add . && git commit
	@read -p "Push to remote? [y/N] " confirm && [ "$$confirm" = "y" ] && git push || echo "Skipped push."

publish:
	uv publish

publish-test:
	uv publish --publish-url https://test.pypi.org/legacy/
