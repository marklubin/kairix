# Bugs Found in knowledge_db_demo.py

During test development, the following bugs were identified in the original script:

## 1. Unit vs SemanticUnit field mismatch
- **Location**: Line 231 in `dedupe_semantic_unit()`
- **Issue**: Unit model has `id` field but code tries to access `unit.uid`
- **Fix**: Change `unit.uid` to `unit.id` or add uid property to Unit

## 2. Typo in SemanticUnit field name
- **Location**: Line 235 in `dedupe_semantic_unit()`
- **Issue**: Code uses `maybe_unit.description` but SemanticUnit has `descriptions` (plural)
- **Fix**: Change to `maybe_unit.descriptions`

## 3. Using built-in id function instead of unit.id
- **Location**: Line 240 in `dedupe_semantic_unit()`
- **Issue**: Code uses `embedder.encode(id)` which passes Python's built-in id function
- **Fix**: Change to `embedder.encode(unit.id)`

## 4. Wrong index for vector search score
- **Location**: Line 244 in `dedupe_semantic_unit()`
- **Issue**: Code uses `matches[0][0]` but based on vector_search return format, score is at index 1
- **Fix**: Change to `matches[0][1]`

## 5. Wrong field access pattern
- **Location**: Line 246 in `dedupe_semantic_unit()`
- **Issue**: Code uses `matches[0][0].type` but matches[0][0] is the content string, not an object
- **Fix**: Need to restructure vector search to return objects or change logic

## 6. Typo in variable name
- **Location**: Line 250 in `dedupe_semantic_unit()`
- **Issue**: Code uses `embedding(emedding.to_list())` - typo in 'emedding'
- **Fix**: Change to `embedding`

## 7. Process knowledge bug
- **Location**: Line 273-274 in `process_knowledge()`
- **Issue**: Break happens before processing extractions, so data is never persisted
- **Fix**: Move the break after the extraction processing loop

## 8. Undefined variable
- **Location**: Line 258 in `dedupe_semantic_unit()`
- **Issue**: Uses undefined variable `id` instead of `unit.id`
- **Fix**: Change to `unit.id`

## 9. Wrong relationship property access
- **Location**: Line 291 in `process_knowledge()`
- **Issue**: Uses `rel.relationship_description` but Relation model has `relationship_descriptor`
- **Fix**: Change to `rel.relationship_descriptor`

## 10. Module-level execution issue
- **Location**: Line 303
- **Issue**: `asyncio.run(process_knowledge(10))` is outside the `if __name__ == "__main__":` block
- **Fix**: Move inside the if block or remove

These bugs prevent the script from running correctly and were discovered through comprehensive unit testing.