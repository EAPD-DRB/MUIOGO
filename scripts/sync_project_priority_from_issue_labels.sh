#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "GITHUB_TOKEN is required." >&2
  echo "Token needs read/write access to issues and projects." >&2
  exit 1
fi

REPO_SLUG="${1:-}"
PROJECT_TITLE="${2:-Project Management}"
PRIORITY_FIELD_NAME="${PRIORITY_FIELD_NAME:-Priority}"
DRY_RUN="${DRY_RUN:-false}"
ISSUE_NUMBER_INPUT="${3:-${ISSUE_NUMBER:-}}"

if [[ -z "$REPO_SLUG" ]]; then
  origin_url="$(git config --get remote.origin.url || true)"
  if [[ "$origin_url" =~ github\.com[:/]([^/]+)/([^/.]+)(\.git)?$ ]]; then
    REPO_SLUG="${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
  else
    echo "Could not infer owner/repo from git remote. Pass it as first arg: owner/repo" >&2
    exit 1
  fi
fi

OWNER="${REPO_SLUG%%/*}"
REPO="${REPO_SLUG##*/}"

# Trim potential leading/trailing whitespace from CLI inputs.
OWNER="$(printf '%s' "$OWNER" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')"
REPO="$(printf '%s' "$REPO" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')"

if [[ -n "$ISSUE_NUMBER_INPUT" ]] && ! [[ "$ISSUE_NUMBER_INPUT" =~ ^[0-9]+$ ]]; then
  echo "Issue number must be a positive integer (got: \"$ISSUE_NUMBER_INPUT\")." >&2
  exit 1
fi

graphql() {
  local query="$1"
  local variables="${2-}"
  if [[ -z "$variables" ]]; then
    variables='{}'
  fi
  local payload response

  if ! echo "$variables" | jq -e . >/dev/null 2>&1; then
    echo "Internal error: invalid GraphQL variables JSON:" >&2
    echo "$variables" >&2
    return 1
  fi

  payload="$(
    jq -cn \
      --arg query "$query" \
      --argjson variables "$variables" \
      '{query:$query, variables:$variables}'
  )"

  response="$(
    curl -sS -X POST "https://api.github.com/graphql" \
      -H "Authorization: Bearer ${GITHUB_TOKEN}" \
      -H "Content-Type: application/json" \
      --data "$payload"
  )"

  if echo "$response" | jq -e '.message? and ((.data // null) == null)' >/dev/null; then
    echo "GitHub API error: $(echo "$response" | jq -r '.message')" >&2
    echo "$response" | jq -r '.documentation_url? // empty' >&2
    return 1
  fi

  if echo "$response" | jq -e '.errors and (.errors | length > 0)' >/dev/null; then
    echo "GraphQL errors:" >&2
    echo "$response" | jq -r '.errors[]?.message' >&2
    return 1
  fi

  echo "$response"
}

AUTH_QUERY='
query {
  viewer { login }
}
'
auth_resp="$(graphql "$AUTH_QUERY" '{}')"
viewer_login="$(echo "$auth_resp" | jq -r '.data.viewer.login // empty')"
if [[ -z "$viewer_login" ]]; then
  echo "Authentication failed: could not resolve authenticated viewer login." >&2
  echo "Check that GITHUB_TOKEN is valid and authorized for the target org." >&2
  exit 1
fi
echo "Authenticated as: $viewer_login"

PROJECT_QUERY='
query($owner: String!, $repo: String!) {
  repository(owner: $owner, name: $repo) {
    owner {
      __typename
      login
      ... on Organization {
        projectsV2(first: 100) {
          nodes { id title }
        }
      }
      ... on User {
        projectsV2(first: 100) {
          nodes { id title }
        }
      }
    }
    projectsV2(first: 100) {
      nodes { id title }
    }
  }
  viewer {
    login
    ... on User {
      projectsV2(first: 100) {
        nodes { id title }
      }
    }
  }
}
'

project_vars="$(jq -cn --arg owner "$OWNER" --arg repo "$REPO" '{owner:$owner, repo:$repo}')"
project_resp="$(graphql "$PROJECT_QUERY" "$project_vars")"

PROJECT_ID="$(
  echo "$project_resp" | jq -r --arg title "$PROJECT_TITLE" '
    [
      (.data.repository.owner.projectsV2.nodes // []),
      (.data.repository.projectsV2.nodes // []),
      (.data.viewer.projectsV2.nodes // [])
    ]
    | add
    | unique_by(.id)
    | (
        first(.[] | select(.title == $title))
        // first(.[] | select((.title | ascii_downcase) == ($title | ascii_downcase)))
      )
    | .id // empty
  '
)"

PROJECT_ID="${PROJECT_ID_OVERRIDE:-$PROJECT_ID}"

if [[ -z "$PROJECT_ID" ]]; then
  echo "Available projects visible to token (repo-owner/repo/viewer):" >&2
  echo "$project_resp" | jq -r '
    [
      (.data.repository.owner.projectsV2.nodes // []),
      (.data.repository.projectsV2.nodes // []),
      (.data.viewer.projectsV2.nodes // [])
    ]
    | add
    | unique_by(.id)
    | .[]?.title
  ' >&2
  echo "Repository owner: $(echo "$project_resp" | jq -r '.data.repository.owner.__typename // "unknown"') $(echo "$project_resp" | jq -r '.data.repository.owner.login // "unknown"')" >&2
  echo "Authenticated viewer: $(echo "$project_resp" | jq -r '.data.viewer.login // "unknown"')" >&2
  echo "Hint: ensure token can access Projects for this org/repo and includes project read/write permissions." >&2
  echo "If project title differs, run again with exact title:" >&2
  echo "  $0 $OWNER/$REPO \"<Exact Project Title>\"" >&2
  echo "Or set explicit project ID and rerun:" >&2
  echo "  PROJECT_ID_OVERRIDE='PVT_xxx' $0 $OWNER/$REPO \"$PROJECT_TITLE\"" >&2
  echo "" >&2
  echo "Discovered project titles:" >&2
  echo "$project_resp" | jq -r '
    [
      (.data.repository.owner.projectsV2.nodes // []),
      (.data.repository.projectsV2.nodes // []),
      (.data.viewer.projectsV2.nodes // [])
    ]
    | add
    | unique_by(.id)
    | .[]? | "- \(.title) [\(.id)]"
  ' >&2
  echo "Project not found for owner=$OWNER title=\"$PROJECT_TITLE\"" >&2
  exit 1
fi

FIELDS_QUERY='
query($projectId: ID!) {
  node(id: $projectId) {
    ... on ProjectV2 {
      id
      title
      fields(first: 100) {
        nodes {
          __typename
          ... on ProjectV2FieldCommon {
            id
            name
          }
          ... on ProjectV2SingleSelectField {
            options {
              id
              name
            }
          }
        }
      }
    }
  }
}
'

fields_vars="$(jq -cn --arg projectId "$PROJECT_ID" '{projectId:$projectId}')"
fields_resp="$(graphql "$FIELDS_QUERY" "$fields_vars")"

priority_field_json="$(
  echo "$fields_resp" | jq -c --arg field "$PRIORITY_FIELD_NAME" '
    .data.node.fields.nodes[]
    | select((.name | ascii_downcase) == ($field | ascii_downcase))
  ' | head -n 1
)"

if [[ -z "$priority_field_json" ]]; then
  echo "Field \"$PRIORITY_FIELD_NAME\" not found in project \"$PROJECT_TITLE\"." >&2
  exit 1
fi

priority_field_type="$(echo "$priority_field_json" | jq -r '.__typename')"
if [[ "$priority_field_type" != "ProjectV2SingleSelectField" ]]; then
  echo "Field \"$PRIORITY_FIELD_NAME\" is not a single-select field." >&2
  exit 1
fi

PRIORITY_FIELD_ID="$(echo "$priority_field_json" | jq -r '.id')"
PRIORITY_OPTIONS_JSON="$(echo "$priority_field_json" | jq -c '.options')"

ISSUES_QUERY='
query($owner: String!, $repo: String!, $cursor: String) {
  repository(owner: $owner, name: $repo) {
    issues(first: 100, after: $cursor, states: [OPEN, CLOSED]) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        id
        number
        title
        labels(first: 30) {
          nodes { name }
        }
        projectItems(first: 20) {
          nodes {
            id
            project { id }
          }
        }
      }
    }
  }
}
'

SINGLE_ISSUE_QUERY='
query($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    issue(number: $number) {
      id
      number
      title
      labels(first: 30) {
        nodes { name }
      }
      projectItems(first: 20) {
        nodes {
          id
          project { id }
        }
      }
    }
  }
}
'

ADD_ITEM_MUTATION='
mutation($projectId: ID!, $contentId: ID!) {
  addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
    item { id }
  }
}
'

UPDATE_PRIORITY_MUTATION='
mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
  updateProjectV2ItemFieldValue(
    input: {
      projectId: $projectId,
      itemId: $itemId,
      fieldId: $fieldId,
      value: { singleSelectOptionId: $optionId }
    }
  ) {
    projectV2Item { id }
  }
}
'

processed=0
updated=0
added=0
skipped=0
failed=0
cursor=""

echo "Syncing labels to project field:"
echo "  repo: $OWNER/$REPO"
echo "  project: $PROJECT_TITLE ($PROJECT_ID)"
echo "  field: $PRIORITY_FIELD_NAME ($PRIORITY_FIELD_ID)"
echo "  dry_run: $DRY_RUN"
if [[ -n "$ISSUE_NUMBER_INPUT" ]]; then
  echo "  scope: issue #$ISSUE_NUMBER_INPUT"
else
  echo "  scope: all issues"
fi

process_issue() {
  local issue="$1"
  [[ -z "$issue" ]] && return 0
  processed=$((processed + 1))

  local issue_id issue_number issue_title priority_label priority_value option_id item_id add_vars add_resp update_vars

  issue_id="$(echo "$issue" | jq -r '.id')"
  issue_number="$(echo "$issue" | jq -r '.number')"
  issue_title="$(echo "$issue" | jq -r '.title')"

  priority_label="$(
    echo "$issue" | jq -r '
      ([.labels.nodes[]?.name | select(test("^Priority:[[:space:]]*"; "i"))][0]) // empty
    '
  )"

  if [[ -z "$priority_label" ]]; then
    skipped=$((skipped + 1))
    return 0
  fi

  priority_value="$(printf '%s' "$priority_label" | sed -E 's/^[Pp]riority:[[:space:]]*//')"
  if [[ -z "$priority_value" ]]; then
    skipped=$((skipped + 1))
    return 0
  fi

  option_id="$(
    echo "$PRIORITY_OPTIONS_JSON" | jq -r --arg v "$priority_value" '
      def norm:
        ascii_downcase
        | gsub("[[:space:]]+"; " ")
        | sub("^\\s+"; "")
        | sub("\\s+$"; "");
      ($v | norm) as $needle
      | (
          first(.[] | select((.name | norm) == $needle))
          // first(.[] | select((.name | norm) | startswith($needle)))
          // first(.[] | select($needle | startswith(.name | norm)))
        )
      | .id // empty
    '
  )"

  if [[ -z "$option_id" ]]; then
    echo "Skip #$issue_number: no matching option for \"$priority_value\" (issue label: \"$priority_label\")" >&2
    skipped=$((skipped + 1))
    return 0
  fi

  item_id="$(
    echo "$issue" | jq -r --arg projectId "$PROJECT_ID" '
      ([.projectItems.nodes[] | select(.project.id == $projectId) | .id][0]) // empty
    '
  )"

  if [[ -z "$item_id" ]]; then
    if [[ "$DRY_RUN" == "true" ]]; then
      echo "[DRY RUN] Would add issue #$issue_number to project."
      item_id="DRY_RUN_ITEM"
    else
      add_vars="$(jq -cn --arg projectId "$PROJECT_ID" --arg contentId "$issue_id" '{projectId:$projectId, contentId:$contentId}')"
      if ! add_resp="$(graphql "$ADD_ITEM_MUTATION" "$add_vars")"; then
        echo "Failed to add #$issue_number to project." >&2
        failed=$((failed + 1))
        return 0
      fi
      item_id="$(echo "$add_resp" | jq -r '.data.addProjectV2ItemById.item.id // empty')"
      if [[ -z "$item_id" ]]; then
        echo "Failed to add #$issue_number to project (missing item id)." >&2
        failed=$((failed + 1))
        return 0
      fi
      added=$((added + 1))
    fi
  fi

  if [[ "$DRY_RUN" == "true" ]]; then
    echo "[DRY RUN] Would set #$issue_number \"$issue_title\" => Priority \"$priority_value\""
    updated=$((updated + 1))
    return 0
  fi

  update_vars="$(
    jq -cn \
      --arg projectId "$PROJECT_ID" \
      --arg itemId "$item_id" \
      --arg fieldId "$PRIORITY_FIELD_ID" \
      --arg optionId "$option_id" \
      '{projectId:$projectId, itemId:$itemId, fieldId:$fieldId, optionId:$optionId}'
  )"

  if ! graphql "$UPDATE_PRIORITY_MUTATION" "$update_vars" >/dev/null; then
    echo "Failed to update priority for #$issue_number." >&2
    failed=$((failed + 1))
    return 0
  fi

  echo "Updated #$issue_number \"$issue_title\" -> \"$priority_value\""
  updated=$((updated + 1))
}

if [[ -n "$ISSUE_NUMBER_INPUT" ]]; then
  single_issue_vars="$(
    jq -cn \
      --arg owner "$OWNER" \
      --arg repo "$REPO" \
      --argjson number "$ISSUE_NUMBER_INPUT" \
      '{owner:$owner, repo:$repo, number:$number}'
  )"
  single_issue_resp="$(graphql "$SINGLE_ISSUE_QUERY" "$single_issue_vars")"
  issue_json="$(echo "$single_issue_resp" | jq -c '.data.repository.issue // empty')"
  if [[ -z "$issue_json" ]]; then
    echo "Issue #$ISSUE_NUMBER_INPUT not found in $OWNER/$REPO." >&2
    failed=$((failed + 1))
  else
    process_issue "$issue_json"
  fi
else
  while :; do
    if [[ -z "$cursor" ]]; then
      issues_vars="$(jq -cn --arg owner "$OWNER" --arg repo "$REPO" '{owner:$owner, repo:$repo, cursor:null}')"
    else
      issues_vars="$(jq -cn --arg owner "$OWNER" --arg repo "$REPO" --arg cursor "$cursor" '{owner:$owner, repo:$repo, cursor:$cursor}')"
    fi

    issues_resp="$(graphql "$ISSUES_QUERY" "$issues_vars")"

    while IFS= read -r issue; do
      process_issue "$issue"
    done < <(echo "$issues_resp" | jq -c '.data.repository.issues.nodes[]?')

    has_next="$(echo "$issues_resp" | jq -r '.data.repository.issues.pageInfo.hasNextPage')"
    if [[ "$has_next" != "true" ]]; then
      break
    fi
    cursor="$(echo "$issues_resp" | jq -r '.data.repository.issues.pageInfo.endCursor')"
  done
fi

echo
echo "Done."
echo "  processed: $processed"
echo "  updated:   $updated"
echo "  added:     $added"
echo "  skipped:   $skipped"
echo "  failed:    $failed"
