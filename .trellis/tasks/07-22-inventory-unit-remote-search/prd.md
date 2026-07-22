# Inventory Unit Remote Search

## Goal

Remove the fixed 100-record ceiling from inventory document unit selectors so
operators can find any processing or receiving unit by name.

## Confirmed Facts

- The document filter page and editor modal each load processing and receiving
  units with `limit=100, skip=0`, then search only that local option array.
- Both existing list APIs already accept `name`, `is_active`, `skip`, and
  `limit`, return `{ data, count }`, and cap a single response at 100 rows.
- New and updated documents require active units in the service layer. Document
  filters must still support inactive units so historical records remain
  discoverable.

## Requirements

- Replace all four fixed unit-option loads with server-side remote search.
- On open and when the input is empty, display the first 20 matching units.
  Debounce name searches for 300 ms and load the first 20 server matches.
- Document-list filters search both active and inactive units. Document-editor
  fields search active units only.
- Use the Ant Design Select remote-search contract: disable local filtering,
  show loading and empty states, and retain the selected label during search
  transitions.
- Do not add dropdown infinite scrolling, API routes, migrations, or generated
  client edits.

## Acceptance Criteria

- [ ] A processing or receiving unit outside the initial 100 rows can be found
  and selected in document filters and the document editor.
- [ ] Empty selectors fetch 20 rows; a typed name is sent to the existing API
  after a 300 ms debounce and is not locally filtered.
- [ ] Inactive units are searchable in historical document filters but absent
  from document editor results.
- [ ] Loading, empty, failed-search, and selected-option states remain clear
  and do not show stale results after rapid input changes.
- [ ] Frontend checks and focused inventory UI verification pass against an
  isolated test environment.

## Constraints

- Preserve existing server-side active-unit validation and historical-document
  behavior. Editing a document already tied to an inactive unit remains outside
  this task because the server already rejects that update.
- Preserve unrelated untracked `hongxia/` work.
