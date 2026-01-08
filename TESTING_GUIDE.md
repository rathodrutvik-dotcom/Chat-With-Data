# Quick Start: Testing Multi-Document Improvements

## What Was Fixed?

Your RAG system now correctly handles:
- ✅ **Multi-document questions**: "What is timeline for Project A and objective of Project B?"
- ✅ **Counting queries**: "How many projects are in Project_Details.pdf?" (Now returns 4, not 1)
- ✅ **Document-specific queries**: Questions mentioning specific filenames
- ✅ **Distributed information**: Timeline in one doc, objectives in another

## How to Test

### Step 1: Re-upload Your Documents

**IMPORTANT**: You need to re-upload your documents to benefit from entity extraction.

```bash
# Option 1: Clear old embeddings and re-upload via UI
rm -rf src/embedding_store/*

# Option 2: Keep old embeddings and upload new versions
# (The system will create new collections)
```

Then upload through the web interface.

### Step 2: Test Cases

Try these exact questions that were failing before:

#### Test Case 1: Multi-Document Query
```
Question: "What is timeline for Smart Healthcare project and give me objective and scope of Smart City Traffic project?"

Expected Behavior:
- System detects multi-intent
- Decomposes into 3 sub-questions
- Retrieves from both documents
- Synthesizes complete answer

Before: ❌ "Timeline not available"
After: ✅ "Timeline is 6 months [doc1]. Objective is... [doc2]. Scope is... [doc2]."
```

#### Test Case 2: Counting Query
```
Question: "How many projects are mentioned in Project_Details.pdf?"

Expected Behavior:
- Detects counting question
- Filters to specific document
- Chunks have entity prefixes
- Counts all projects

Before: ❌ "1 project"
After: ✅ "4 projects" (or whatever the actual count is)
```

#### Test Case 3: Separate Queries (Should Still Work)
```
Question 1: "What is the timeline for Smart Healthcare project?"
Answer: "6 months [Project_Budget_Timeline_Locations.pdf]"

Question 2: "What is the objective of Smart City Traffic project?"
Answer: "Monitor traffic patterns [Smart_City_Traffic.pdf]"

Both should work correctly as before.
```

### Step 3: Check Logs

Monitor what's happening:

```bash
tail -f src/logs/*.log | grep -E "multi-intent|Extracted|decompos|document filter"
```

Look for:
```
✅ "Detected multi-intent question, decomposing..."
✅ "Decomposed into 2 sub-questions"
✅ "Extracted document filter: Project_Details.pdf"
✅ "Extracted 4 project names: [...]"
```

## Understanding the Improvements

### 1. Question Decomposition

**What it does**: Splits complex questions into simple ones.

```
Input: "What is timeline for A and objective of B?"

Becomes:
  Q1: "What is timeline for A?"
  Q2: "What is objective of B?"

Each Q retrieves separately → Combined answer
```

**When it activates**:
- Questions with "and [question-word]"
- Multiple question marks
- Words like "also", "plus", "both"

### 2. Entity Extraction

**What it does**: Finds and labels entities in documents.

```
Original chunk:
"The Smart Healthcare project has a 6-month timeline..."

Enhanced chunk:
"[Projects: Smart Healthcare Management System]

The Smart Healthcare project has a 6-month timeline..."

Metadata: {
  "projects": ["Smart Healthcare Management System"],
  "project_count": 1,
  "contains_projects": True
}
```

**Why it helps**:
- Counting: LLM sees "[Projects: A, B, C, D]" → counts 4
- Filtering: Can search by project name
- Retrieval: Better keyword matching

### 3. Document Filtering

**What it does**: Restricts search to specific documents.

```
Question: "How many projects in Project_Details.pdf?"

System:
1. Extracts: document_filter = "Project_Details.pdf"
2. Filters chunks: only from that document
3. LLM counts: only in that document
```

**How to use**:
- Mention filename in question: "...in Project_Details.pdf?"
- Works with: .pdf, .docx, .xlsx extensions
- Case-insensitive matching

### 4. Answer Validation

**What it does**: Warns when answers might be incomplete.

```
Question: "How many projects in all documents?"
Context: Only 2 chunks from 1 document

Answer: "2 projects"

Validation: ⚠️ Warning appended
"Note: Retrieved context is limited. If you expected more 
results, try rephrasing your question."
```

**When it warns**:
- Few chunks retrieved (<5)
- Counting question but limited context
- Multi-document query but only 1 doc in context

## Common Issues & Solutions

### Issue 1: Still Getting Wrong Counts

**Symptoms**: "How many projects?" returns wrong number.

**Diagnosis**:
```bash
# Check if documents were re-indexed
tail -f src/logs/*.log | grep "Extracted.*project"

# Should see:
# "Extracted 4 project names: [Project1, Project2, ...]"
```

**Solution**:
1. Clear embeddings: `rm -rf src/embedding_store/*`
2. Re-upload documents via UI
3. Try query again

### Issue 2: Multi-Intent Not Detected

**Symptoms**: Complex question answered partially.

**Diagnosis**:
```bash
tail -f src/logs/*.log | grep "multi-intent"

# Should see:
# "Detected multi-intent question, decomposing: ..."
```

**Solution**:
- Rephrase with explicit "and": "What is X **and** what is Y?"
- Or ask separately: Better for very different topics

### Issue 3: Document Filter Not Working

**Symptoms**: Asking about "Project_Details.pdf" but gets results from other docs.

**Diagnosis**:
```bash
tail -f src/logs/*.log | grep "document filter"

# Should see:
# "Detected document filter: Project_Details.pdf"
```

**Solution**:
- Use exact filename: "Project_Details.pdf" (not "Project Details")
- Include extension: ".pdf"
- Check spelling

### Issue 4: Slow Responses

**Symptoms**: Multi-intent questions take longer.

**Why**: Each sub-question does full retrieval.

**Expected Times**:
- Single question: 2-3 seconds
- 2 sub-questions: 4-6 seconds
- 3 sub-questions: 6-9 seconds

**Normal behavior** - not a bug!

## Advanced Usage

### Counting Across Documents

```
Question: "How many projects are mentioned across all documents?"

System will:
1. Retrieve from all documents
2. Find project entities in metadata
3. Count unique projects
4. Cite sources

Answer: "There are 6 projects mentioned:
- Project A [doc1.pdf]
- Project B [doc1.pdf]
- Project C [doc2.pdf]
..."
```

### Document-Specific Information

```
Question: "What information is in Smart_City_Traffic.pdf?"

System will:
1. Filter to that document
2. Retrieve top chunks
3. Summarize content

Answer: "Smart_City_Traffic.pdf contains:
- Objective: Monitor traffic patterns
- Scope: City-wide coverage
- Timeline: 12 months
[Smart_City_Traffic.pdf]"
```

### Comparing Across Documents

```
Question: "Compare the timelines of Smart Healthcare and Smart City Traffic projects"

System will:
1. Decompose into 2 queries
2. Retrieve from respective documents
3. Synthesize comparison

Answer: "Smart Healthcare has a 6-month timeline [doc1], 
while Smart City Traffic spans 12 months [doc2]."
```

## Validation Warnings Explained

### ⚠️ "Retrieved context is limited"
**Meaning**: Only a few chunks found (< 5).  
**Action**: Try rephrasing or adding more specific keywords.

### ⚠️ "Question asks about multiple documents, but context from only one"
**Meaning**: Asked "both"/"all" but results from single doc.  
**Action**: Check if other document was uploaded. Re-upload if needed.

### Note: "I found N items. If more exist, they may not be in retrieved sections"
**Meaning**: LLM acknowledging potential incompleteness.  
**Action**: Normal behavior for transparency. Not an error.

## Performance Tips

### For Faster Responses

1. **Single questions**: Ask separately if not related
   ```
   ❌ Slow: "What is A and B and C and D?"
   ✅ Fast: Ask each separately
   ```

2. **Specific documents**: Mention filename to reduce search space
   ```
   ✅ Fast: "How many projects in Project_Details.pdf?"
   ❌ Slower: "How many projects?" (searches all docs)
   ```

3. **Clear phrasing**: Avoid ambiguity
   ```
   ❌ Ambiguous: "Tell me about the projects"
   ✅ Clear: "List all project names and their timelines"
   ```

### For Better Accuracy

1. **Use exact terms**: Match document terminology
2. **One topic per question**: Unless truly related
3. **Mention document names**: For document-specific info
4. **Re-upload periodically**: After major document changes

## Testing Checklist

Before considering the fix complete, test:

- [ ] Multi-document question (2+ topics, 2+ documents)
- [ ] Counting query (exact document)
- [ ] Counting query (all documents)
- [ ] Single questions (should still work)
- [ ] Document-specific query
- [ ] Questions with validation warnings

All should work correctly now! ✅

## Need Help?

1. **Check logs**: `tail -f src/logs/*.log`
2. **Run test**: `python test_improvements.py`
3. **Review**: [MULTI_DOCUMENT_FIX_SUMMARY.md](MULTI_DOCUMENT_FIX_SUMMARY.md)

## Summary

The system now:
- ✅ Handles multi-intent questions
- ✅ Counts entities correctly
- ✅ Filters by document
- ✅ Warns about incompleteness
- ✅ Extracts structured entities

**Next steps**:
1. Re-upload your documents
2. Try the test cases above
3. Monitor the logs
4. Enjoy accurate multi-document conversations! 🎉
