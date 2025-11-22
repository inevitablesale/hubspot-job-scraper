# Validation Demo - False Positive Filtering

This demonstrates the fix in action using actual examples from production logs.

## Test the Fix Yourself

```python
from extractors import MultiLayerExtractor

# Test with false positives from production logs
html = '''
<html>
<body>
    <!-- False Positives (should NOT be extracted) -->
    <a href="/blog/inbound-marketing">What Is Inbound Marketing?</a>
    <a href="/podcast/episode-57">Episode 57: Marketing Teams</a>
    <a href="https://youtube.com">Watch On Youtube</a>
    <a href="/apply">Apply Today</a>
    <h3>Marketing & Creative</h3>
    
    <!-- Actual Jobs (should be extracted) -->
    <a href="/job/1">Senior HubSpot Developer</a>
    <a href="/job/2">Solutions Architect</a>
    <a href="/job/3">Sales Development Representative</a>
</body>
</html>
'''

extractor = MultiLayerExtractor("https://example.com")
jobs = extractor.extract_all(html)

print(f"✅ Found {len(jobs)} jobs (expected 3):")
for job in jobs:
    print(f"  - {job['title']}")
```

## Expected Output

```
✅ Found 3 jobs (expected 3):
  - Senior HubSpot Developer
  - Solutions Architect
  - Sales Development Representative
```

## Verification

Run the test suite to verify all scenarios:

```bash
python -m unittest test_extractors.py test_false_positives.py test_real_world_examples.py -v
```

All 22 tests should pass:
- ✅ 11 original extractor tests
- ✅ 7 false positive detection tests
- ✅ 4 real-world production example tests
