# Job Extraction False Positives - Fix Summary

## Problem
The job scraper was extracting non-job content as jobs because keyword matching was too broad.

### Examples from Production Logs

From `hyphadev.io/careers`:
- ❌ "What Is Inbound Marketing?" (blog article)
- ❌ "What Is Content Marketing?" (blog article)
- ❌ "Inbound Marketing & Strategic Content" (article title)
- ❌ "Apply Today" (generic CTA)

From `clearpivot.com/team`:
- ❌ "Episode 57: Why The Smartest Marketing Teams..." (podcast title)
- ❌ "Watch On Youtube" (social media link)
- ❌ "Apple Podcasts Listen On Apple Podcasts" (social media link)
- ❌ "Spotify Listen On Spotify" (social media link)
- ✅ "Solutions Architect" (actual job - was extracted correctly)

From `huble.com/careers`:
- ❌ "Marketing & Creative" (department category)
- ❌ "Sales & Revenue" (department category)

From `revblack.com`:
- Found 17 total extractions, but 0 actual jobs (all false positives)

## Root Cause

The `_is_job_like()` function used simple substring matching:
```python
# OLD CODE - Too permissive
TITLE_HINTS = ["developer", "engineer", "marketing", "sales", "product", "apply", ...]
def _is_job_like(text):
    return any(hint in text.lower() for hint in TITLE_HINTS)
```

Problems:
1. Matched generic words like "marketing", "sales" that appear in blog posts
2. Matched "engineering" when looking for "engineer" (substring match)
3. No filtering for questions, social media links, or CTAs
4. No minimum length validation

## Solution

### 1. Categorized Keywords
```python
# Role-specific keywords that indicate actual job titles
TITLE_HINTS = [
    "developer", "engineer", "consultant", "architect", "specialist",
    "manager", "analyst", "designer", "coordinator", "director",
    "representative", "associate", "lead", "position", "role",
    "opening", "opportunity"
]
```

Removed generic industry words ("marketing", "sales", "product") from the main hints.

### 2. False Positive Patterns
Pre-compiled regex patterns to filter out:
- Questions: "What is...", "How to...", "Why..."
- Social media: "youtube", "spotify", "podcast", "Watch On", "Listen On"
- Generic CTAs: "Apply Now", "Join Us", "View", "Learn More"
- Blog content: "Episode 57", "Chapter"
- Navigation: "About Us", "Contact", "Meet Our Team"

### 3. Word Boundary Matching
```python
# Pre-compiled patterns with word boundaries
ROLE_PATTERNS = [
    re.compile(r'\b' + re.escape(hint) + r'\b', re.IGNORECASE) 
    for hint in TITLE_HINTS
]
```

This ensures "engineer" matches "engineer" but NOT "engineering".

### 4. Minimum Length Validation
```python
MIN_JOB_TITLE_LENGTH = 5
if len(text.strip()) < MIN_JOB_TITLE_LENGTH:
    return False
```

### 5. Enhanced `_is_job_like()` Function
```python
def _is_job_like(self, text: str) -> bool:
    if not text or len(text.strip()) < MIN_JOB_TITLE_LENGTH:
        return False
    
    text_lower = text.lower().strip()
    
    # Filter out false positives
    for pattern in FALSE_POSITIVE_PATTERNS:
        if pattern.search(text_lower):
            return False
    
    # Check for role-specific keywords with word boundaries
    for pattern in ROLE_PATTERNS:
        if pattern.search(text_lower):
            return True
    
    return False
```

## Results

### Test Coverage
- **22 total tests** (all passing)
  - 11 original extractor tests
  - 7 false positive detection tests
  - 4 real-world production example tests

### Before Fix
| Input | Extracted? | Should Extract? | Status |
|-------|-----------|----------------|--------|
| "What Is Inbound Marketing?" | ✅ Yes | ❌ No | ❌ BUG |
| "Watch On Youtube" | ✅ Yes | ❌ No | ❌ BUG |
| "Apply Today" | ✅ Yes | ❌ No | ❌ BUG |
| "Marketing & Creative" | ✅ Yes | ❌ No | ❌ BUG |
| "Engineering & Product" | ✅ Yes | ❌ No | ❌ BUG |
| "Episode 57: ..." | ✅ Yes | ❌ No | ❌ BUG |
| "Senior HubSpot Developer" | ✅ Yes | ✅ Yes | ✅ OK |
| "Solutions Architect" | ✅ Yes | ✅ Yes | ✅ OK |

### After Fix
| Input | Extracted? | Should Extract? | Status |
|-------|-----------|----------------|--------|
| "What Is Inbound Marketing?" | ❌ No | ❌ No | ✅ FIXED |
| "Watch On Youtube" | ❌ No | ❌ No | ✅ FIXED |
| "Apply Today" | ❌ No | ❌ No | ✅ FIXED |
| "Marketing & Creative" | ❌ No | ❌ No | ✅ FIXED |
| "Engineering & Product" | ❌ No | ❌ No | ✅ FIXED |
| "Episode 57: ..." | ❌ No | ❌ No | ✅ FIXED |
| "Senior HubSpot Developer" | ✅ Yes | ✅ Yes | ✅ OK |
| "Solutions Architect" | ✅ Yes | ✅ Yes | ✅ OK |
| "Sales Development Representative" | ✅ Yes | ✅ Yes | ✅ OK |

## Performance Optimizations

All regex patterns are pre-compiled at module level:
- 22 false positive patterns in `FALSE_POSITIVE_PATTERNS`
- 17 role patterns in `ROLE_PATTERNS`

This eliminates regex compilation overhead in the hot path (extraction runs on every page).

## Security

✅ CodeQL security scan passed with 0 alerts

## Files Modified

1. **extractors.py** - Core extraction logic improvements
   - Added MIN_JOB_TITLE_LENGTH constant
   - Pre-compiled FALSE_POSITIVE_PATTERNS
   - Pre-compiled ROLE_PATTERNS
   - Improved _is_job_like() function
   - Added minimum length checks to AnchorExtractor, ButtonExtractor, HeadingExtractor

2. **test_false_positives.py** - New test suite for false positive detection
   - 7 tests covering blog posts, navigation, social media, CTAs, questions, categories

3. **test_real_world_examples.py** - Real production failure scenarios
   - 4 tests using actual examples from production logs

## Impact on Production

Expected behavior changes:
- **Fewer extractions** - Will no longer extract blog posts, social media links, generic CTAs
- **Higher quality** - Extracted jobs will be actual job postings with specific role titles
- **Better precision** - Word boundary matching prevents department names from being extracted

From the logs, domains like `revblack.com` showed "17 total jobs" but 0 actual jobs. This fix should result in:
- More accurate job counts
- Less noise in the database
- Better user experience with relevant job listings
