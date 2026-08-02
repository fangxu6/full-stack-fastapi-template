# Inventory Excel Frontend Implementation Plan

1. Add typed importer scope and complete export filtering in the inventory
   router, importer, and service; cover atomic validation and filtered rows.
2. Regenerate the frontend OpenAPI client and review only generated output.
3. Add shared XLSX download/import/error primitives without feature vocabulary.
4. Compose the primitives in the inventory document page and pass the raw and
   finished workflow configuration from the two thin wrapper pages.
5. Add focused browser/unit tests and update Trellis frontend/backend Excel
   specifications.
6. Run backend/frontend checks, the quality hooks, and review all diffs before
   proposing the required generated-client synchronization commit.
