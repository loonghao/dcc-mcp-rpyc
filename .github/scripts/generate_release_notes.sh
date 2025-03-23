#!/bin/bash

# Exit on error
set -e

# Get version from tag
VERSION=${1:-${GITHUB_REF#refs/tags/}}

# Remove 'v' prefix if present
VERSION=${VERSION#v}

echo "Generating release notes for version: $VERSION"

# Try to find the version in CHANGELOG.md
if [ -f CHANGELOG.md ]; then
  # Try with format: ## 0.1.0 (date)
  CHANGES=$(grep -A 100 "## $VERSION (" CHANGELOG.md | grep -B 100 -m 2 "^## " | grep -v "^## $VERSION (" | grep -v "^## " | sed '/^$/d' || true)

  # If not found, try with brackets format: ## [0.1.0]
  if [ -z "$CHANGES" ]; then
    CHANGES=$(grep -A 100 "## \[$VERSION\]" CHANGELOG.md | grep -B 100 -m 2 "^## " | grep -v "^## \[$VERSION\]" | grep -v "^## " | sed '/^$/d' || true)
  fi

  # If still not found
  if [ -z "$CHANGES" ]; then
    CHANGES="No specific changelog entry found for version $VERSION"
  fi
else
  CHANGES="No CHANGELOG.md file found"
fi

echo "Found changes:"
echo "$CHANGES"

# Load template and replace variables
if [ -f .github/release-template.md ]; then
  TEMPLATE=$(cat .github/release-template.md)
  # Replace variables
  TEMPLATE="${TEMPLATE//\$RELEASE_VERSION/$VERSION}"
  TEMPLATE="${TEMPLATE//\$CHANGES/$CHANGES}"

  # Create a temporary file for the release notes
  echo "$TEMPLATE" > release-notes.md
  echo "Release notes generated successfully at release-notes.md"
else
  echo "Error: Template file .github/release-template.md not found"
  exit 1
fi
